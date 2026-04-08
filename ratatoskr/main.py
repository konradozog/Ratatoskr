"""
Ratatoskr — lightweight voice-to-clipboard tool.

Sits in the system tray. Press a hotkey to start/stop recording.
The recording is transcribed and copied to the clipboard (or saved to a file).
"""

import os
import sys
import ctypes
import ctypes.wintypes
import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QAbstractNativeEventFilter, QByteArray
from PySide6.QtGui import QIcon, QAction, QColor, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from .core.recorder import Recorder, save_recovery_wav, load_recovery_wav, delete_recovery_wav
from .core.transcriber import TranscriberEngine
from .ui.overlay import OverlayWidget
from .ui.settings_dialog import SettingsDialog, load_settings, save_settings
from .ui.theme import build_stylesheet, ACCENT, BG, TEXT, REC_RED

# Windows hotkey constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
_HOTKEY_ID = 1

_MOD_MAP = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN, "windows": MOD_WIN,
}

_VK_MAP = {
    **{chr(c): c for c in range(0x30, 0x3A)},  # 0-9
    **{chr(c).lower(): c for c in range(0x41, 0x5B)},  # a-z → VK_A..VK_Z
    **{f"f{i}": 0x6F + i for i in range(1, 25)},  # F1-F24
    "space": 0x20, "enter": 0x0D, "return": 0x0D, "tab": 0x09,
    "escape": 0x1B, "esc": 0x1B, "backspace": 0x08,
    "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
}


def _parse_hotkey(hotkey_str: str):
    """Parse 'ctrl+shift+r' into (modifiers, vk_code)."""
    parts = [p.strip().lower() for p in hotkey_str.split("+")]
    modifiers = MOD_NOREPEAT
    vk = 0
    for part in parts:
        if part in _MOD_MAP:
            modifiers |= _MOD_MAP[part]
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
        else:
            print(f"Unknown hotkey part: {part}", flush=True)
    return modifiers, vk


class _HotkeyFilter(QAbstractNativeEventFilter):
    """Catches WM_HOTKEY messages from the Windows message queue."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG" or event_type == QByteArray(b"windows_generic_MSG"):
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                self._callback()
                return True, 0
        return False, 0


class _Signals(QObject):
    """Bridge between background threads and Qt main thread."""
    transcription_done = Signal(str)
    transcription_error = Signal(str)
    model_status = Signal(str)


def _make_icon(color: str = ACCENT) -> QIcon:
    """Generate a simple colored circle icon for the tray."""
    pix = QPixmap(64, 64)
    pix.fill(QColor("transparent"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawEllipse(8, 8, 48, 48)
    # Draw "R" letter
    p.setPen(QColor(BG))
    font = p.font()
    font.setPixelSize(30)
    font.setBold(True)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignCenter, "R")
    p.end()
    return QIcon(pix)


class RatatoskrApp:
    """Main application controller."""

    def __init__(self):
        self._settings = load_settings()
        self._recorder = Recorder()
        self._transcriber = TranscriberEngine()
        self._signals = _Signals()

        # Duration timer (updates overlay while recording)
        self._duration_timer = QTimer()
        self._duration_timer.setInterval(200)
        self._duration_timer.timeout.connect(self._update_duration)

        # Overlay
        self._overlay = OverlayWidget()

        # System tray
        self._icon_default = _make_icon(ACCENT)
        self._icon_recording = _make_icon(REC_RED)

        self._tray = QSystemTrayIcon(self._icon_default)
        self._tray.setToolTip("Ratatoskr — voice to clipboard")
        self._build_tray_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

        # Signals
        self._signals.transcription_done.connect(self._on_transcription_done)
        self._signals.transcription_error.connect(self._on_transcription_error)
        self._signals.model_status.connect(self._on_model_status)

        # Overlay buttons
        self._overlay.pause_clicked.connect(self._toggle_pause)
        self._overlay.stop_clicked.connect(self._stop_recording)

        # Register global hotkey (Windows native)
        self._hotkey_registered = False
        self._register_hotkey()

        # Pre-load model
        self._load_model()

        # If a previous session crashed mid-transcription, recover
        self._try_recover()

    def _build_tray_menu(self):
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background: #1F1F1F;
                color: #E2DDD5;
                border: 1px solid rgba(255,255,255,18);
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: rgba(245,166,35,26);
            }}
        """)

        record_action = QAction("Record  (hotkey)", menu)
        record_action.triggered.connect(self.toggle_recording)
        menu.addAction(record_action)

        menu.addSeparator()

        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_recording()

    def _register_hotkey(self) -> bool:
        """Try to register the global hotkey. Returns True on success."""
        modifiers, vk = _parse_hotkey(self._settings["hotkey"])
        if vk == 0:
            print(f"Invalid hotkey: {self._settings['hotkey']}", flush=True)
            return False
        ok = ctypes.windll.user32.RegisterHotKey(None, _HOTKEY_ID, modifiers, vk)
        if ok:
            self._hotkey_registered = True
            print(f"Hotkey registered: {self._settings['hotkey']}", flush=True)
            return True
        else:
            print(f"Failed to register hotkey: {self._settings['hotkey']} (already in use?)", flush=True)
            return False

    def _unregister_hotkey(self):
        if self._hotkey_registered:
            ctypes.windll.user32.UnregisterHotKey(None, _HOTKEY_ID)
            self._hotkey_registered = False

    def toggle_recording(self):
        if self._recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _toggle_pause(self):
        if not self._recorder.is_recording:
            return
        if self._recorder.is_paused:
            self._recorder.resume()
            self._overlay.show_recording()
            self._duration_timer.start()
        else:
            self._recorder.pause()
            self._duration_timer.stop()
            self._overlay.show_paused()

    def _start_recording(self):
        try:
            self._recorder.start()
        except Exception as e:
            self._overlay.show_error(f"Mic: {e}"[:50])
            return
        self._tray.setIcon(self._icon_recording)
        self._overlay.show_recording()
        self._duration_timer.start()

    def _stop_recording(self):
        self._duration_timer.stop()
        audio = self._recorder.stop()
        self._tray.setIcon(self._icon_default)

        if audio is None:
            self._overlay.hide()
            return

        save_recovery_wav(audio)
        self._overlay.show_transcribing()
        self._transcribe(audio)

    def _update_duration(self):
        if self._recorder.is_recording:
            self._overlay.update_duration(self._recorder.duration)
            self._overlay.update_volume(self._recorder.rms)

    def _try_recover(self):
        audio = load_recovery_wav()
        if audio is None:
            return
        self._overlay.show_recovering()
        self._transcribe(audio)

    def _load_model(self):
        self._transcriber.load_model(
            model_name=self._settings["model"],
            on_status=lambda msg: self._signals.model_status.emit(msg),
        )

    def _on_model_status(self, msg: str):
        self._tray.setToolTip(f"Ratatoskr — {msg}")

    def _transcribe(self, audio):
        if not self._transcriber.is_loaded:
            self._load_model()

        self._transcriber.transcribe(
            audio=audio,
            language=self._settings.get("language"),
            on_done=lambda text: self._signals.transcription_done.emit(text),
            on_error=lambda msg: self._signals.transcription_error.emit(msg),
        )

    def _on_transcription_done(self, text: str):
        delete_recovery_wav()
        if not text:
            self._overlay.show_error("No speech detected")
            return

        actions = []

        if self._settings.get("auto_copy", True):
            QApplication.clipboard().setText(text)
            actions.append("Copied")

        if self._settings.get("save_to_file", False):
            self._save_to_file(text)
            actions.append("Saved")

        msg = " & ".join(actions) if actions else "Done"
        self._overlay.show_done(msg)

    def _on_transcription_error(self, msg: str):
        delete_recovery_wav()
        self._overlay.show_error(f"Error: {msg[:40]}")

    def _save_to_file(self, text: str):
        out_dir = self._settings.get("output_dir") or os.path.join(
            os.path.expanduser("~"), ".ratatoskr", "transcripts"
        )
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"ratatoskr_{ts}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _open_settings(self):
        dlg = SettingsDialog(self._settings)
        dlg.setStyleSheet(build_stylesheet())
        dlg.settings_changed.connect(self._apply_settings)
        dlg.exec()

    def _apply_settings(self, new_settings: dict):
        old_hotkey = self._settings.get("hotkey")
        old_model = self._settings.get("model")
        self._settings = new_settings

        if new_settings.get("hotkey") != old_hotkey:
            self._unregister_hotkey()
            if not self._register_hotkey():
                # Rollback: re-register the old hotkey and persist it
                self._settings["hotkey"] = old_hotkey
                self._register_hotkey()
                save_settings(self._settings)
                self._overlay.show_error("Hotkey unavailable – reverted")

        if new_settings.get("model") != old_model:
            self._load_model()

    def _quit(self):
        self._duration_timer.stop()

        # Stop recording if in progress (cleans up the audio stream)
        if self._recorder.is_recording:
            self._recorder.stop()

        self._unregister_hotkey()
        self._tray.hide()
        QApplication.quit()


def _acquire_single_instance():
    """Prevent multiple instances via a Windows named mutex.

    Returns the mutex handle (must be kept alive) or None if another
    instance is already running.
    """
    ERROR_ALREADY_EXISTS = 183
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\RatatoskrSingleInstance")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return handle


def main():
    if sys.platform != "win32":
        print("Ratatoskr currently supports Windows only.", flush=True)
        sys.exit(1)

    # Windows: set AppUserModelID for taskbar grouping
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ratatoskr.app")
    except Exception:
        pass

    mutex = _acquire_single_instance()
    if mutex is None:
        print("Ratatoskr is already running.", flush=True)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(build_stylesheet())

    ratatoskr = RatatoskrApp()

    # Install native event filter to catch WM_HOTKEY
    hotkey_filter = _HotkeyFilter(ratatoskr.toggle_recording)
    app.installNativeEventFilter(hotkey_filter)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
