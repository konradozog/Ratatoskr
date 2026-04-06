"""Ratatoskr – settings dialog."""

import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QGroupBox, QFormLayout, QLineEdit,
    QMessageBox,
)

from . import theme
from ..core.transcriber import WHISPER_MODELS, LANGUAGES

# Known shortcuts that collide with popular apps (browsers, IDEs, etc.)
_CONFLICTING_HOTKEYS = {
    "ctrl+shift+r",   # browser hard-reload
    "ctrl+shift+i",   # browser devtools
    "ctrl+shift+j",   # browser devtools console
    "ctrl+shift+c",   # browser inspect element / clipboard managers
    "ctrl+shift+v",   # paste without formatting
    "ctrl+shift+n",   # browser incognito
    "ctrl+shift+t",   # browser reopen tab
    "ctrl+shift+p",   # VS Code command palette
}

_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ratatoskr")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "model": "small",
    "language": "auto",
    "hotkey": "ctrl+alt+r",
    "auto_copy": True,
    "save_to_file": False,
    "output_dir": "",
}


def _migrate(settings: dict) -> dict:
    """One-time fixups for settings saved by older versions."""
    # v0.1.0 shipped with ctrl+shift+r which steals browser hard-reload
    if settings.get("hotkey") == "ctrl+shift+r":
        settings["hotkey"] = DEFAULT_SETTINGS["hotkey"]
    return settings


def load_settings() -> dict:
    try:
        with open(_CONFIG_FILE, "r") as f:
            saved = json.load(f)
        merged = {**DEFAULT_SETTINGS, **saved}
        migrated = _migrate(merged)
        if migrated != merged:
            save_settings(migrated)
        return migrated
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)


class SettingsDialog(QDialog):
    settings_changed = Signal(dict)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ratatoskr Settings")
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._settings = dict(settings)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ── Model group ──
        model_group = QGroupBox("TRANSCRIPTION")
        form = QFormLayout(model_group)
        form.setSpacing(10)

        self._model_combo = QComboBox()
        self._model_combo.addItems(WHISPER_MODELS)
        self._model_combo.setCurrentText(self._settings["model"])
        form.addRow("Model:", self._model_combo)

        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(f"{name} ({code})", code)
        idx = list(LANGUAGES.keys()).index(self._settings.get("language", "auto"))
        self._lang_combo.setCurrentIndex(idx)
        form.addRow("Language:", self._lang_combo)

        layout.addWidget(model_group)

        # ── Hotkey group ──
        hotkey_group = QGroupBox("HOTKEY")
        hk_layout = QFormLayout(hotkey_group)
        self._hotkey_edit = QLineEdit(self._settings["hotkey"])
        self._hotkey_edit.setPlaceholderText("e.g. ctrl+alt+r")
        hk_layout.addRow("Record toggle:", self._hotkey_edit)
        layout.addWidget(hotkey_group)

        # ── Output group ──
        out_group = QGroupBox("OUTPUT")
        out_layout = QVBoxLayout(out_group)
        out_layout.setSpacing(8)

        self._auto_copy = QCheckBox("Copy transcription to clipboard")
        self._auto_copy.setChecked(self._settings["auto_copy"])
        out_layout.addWidget(self._auto_copy)

        self._save_file = QCheckBox("Also save to .txt file")
        self._save_file.setChecked(self._settings["save_to_file"])
        out_layout.addWidget(self._save_file)

        layout.addWidget(out_group)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("accent", True)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_save(self):
        hotkey = self._hotkey_edit.text().strip() or "ctrl+alt+r"

        # Warn about well-known collisions
        normalized = "+".join(
            p.strip().lower() for p in hotkey.split("+")
        )
        if normalized in _CONFLICTING_HOTKEYS:
            ans = QMessageBox.warning(
                self,
                "Hotkey conflict",
                f'"{hotkey}" is used by browsers / IDEs and will be '
                f"intercepted while Ratatoskr is running.\n\n"
                f"Save anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

        self._settings["model"] = self._model_combo.currentText()
        self._settings["language"] = self._lang_combo.currentData()
        self._settings["hotkey"] = hotkey
        self._settings["auto_copy"] = self._auto_copy.isChecked()
        self._settings["save_to_file"] = self._save_file.isChecked()
        save_settings(self._settings)
        self.settings_changed.emit(self._settings)
        self.accept()
