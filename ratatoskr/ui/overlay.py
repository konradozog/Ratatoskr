"""Ratatoskr – floating overlay widget (recording indicator + status)."""

import math

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QIcon, QPixmap, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QPushButton

from . import theme


class PulsingDot(QWidget):
    """Small pulsing red dot for recording indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._opacity = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._phase = 0.0

    def start(self):
        self._timer.start(50)

    def stop(self):
        self._timer.stop()
        self._opacity = 1.0
        self.update()

    def _pulse(self):
        self._phase += 0.1
        self._opacity = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(self._phase))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(theme.REC_RED)
        color.setAlphaF(self._opacity)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 10, 10)
        p.end()


def _make_pause_icon(color: str = theme.TEXT, size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor("transparent"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    w = round(size * 0.22)
    gap = round(size * 0.14)
    h = round(size * 0.65)
    y = (size - h) // 2
    x1 = (size - 2 * w - gap) // 2
    p.drawRoundedRect(x1, y, w, h, 1, 1)
    p.drawRoundedRect(x1 + w + gap, y, w, h, 1, 1)
    p.end()
    return QIcon(pix)


def _make_resume_icon(color: str = theme.TEXT, size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor("transparent"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    m = round(size * 0.2)
    path = QPainterPath()
    path.moveTo(m + 1, m)
    path.lineTo(size - m, size / 2)
    path.lineTo(m + 1, size - m)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def _make_stop_icon(color: str = theme.TEXT, size: int = 16) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(QColor("transparent"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    m = round(size * 0.25)
    s = size - 2 * m
    p.drawRoundedRect(m, m, s, s, 2, 2)
    p.end()
    return QIcon(pix)


def _label_style(color: str, weight: int = 600) -> str:
    return (
        f"color: {color};"
        f"font-family: {theme.FONT_FAMILY};"
        f"font-size: 10pt;"
        f"font-weight: {weight};"
        f"background: transparent;"
    )


# Pre-built label stylesheets — built once at import, reused on every state change.
_STYLE_READY = _label_style(theme.TEXT, 500)
_STYLE_RECORDING = _label_style(theme.REC_RED)
_STYLE_ACCENT = _label_style(theme.ACCENT)
_STYLE_SUCCESS = _label_style(theme.SUCCESS)
_STYLE_ERROR = _label_style(theme.ERROR)


class OverlayWidget(QWidget):
    """Frameless floating overlay that shows recording/transcription status."""

    pause_clicked = Signal()
    stop_clicked = Signal()

    _BTN_STYLE = f"""
        QPushButton {{
            background: {theme.SURFACE3};
            border: 1px solid {theme.BORDER};
            border-radius: 6px;
            padding: 0px;
            min-width: 28px;
            min-height: 28px;
            max-width: 28px;
            max-height: 28px;
        }}
        QPushButton:hover {{
            background: {theme.ELEVATED};
            border-color: {theme.BORDER_HOVER};
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(48)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        self._dot = PulsingDot()
        layout.addWidget(self._dot)

        self._label = QLabel("Ready")
        self._label.setStyleSheet(_STYLE_READY)
        layout.addWidget(self._label)

        self._duration_label = QLabel("")
        self._duration_label.setStyleSheet(f"""
            color: {theme.TEXT2};
            font-family: {theme.MONO_FAMILY};
            font-size: 9pt;
            background: transparent;
        """)
        layout.addWidget(self._duration_label)

        layout.addStretch()

        # Pause / Stop buttons (visible only while recording)
        self._icon_pause = _make_pause_icon(theme.TEXT)
        self._icon_resume = _make_resume_icon(theme.TEXT)
        self._icon_stop = _make_stop_icon(theme.TEXT)

        self._btn_pause = QPushButton()
        self._btn_pause.setIcon(self._icon_pause)
        self._btn_pause.setStyleSheet(self._BTN_STYLE)
        self._btn_pause.setToolTip("Pause")
        self._btn_pause.clicked.connect(self.pause_clicked)
        layout.addWidget(self._btn_pause)

        self._btn_stop = QPushButton()
        self._btn_stop.setIcon(self._icon_stop)
        self._btn_stop.setStyleSheet(self._BTN_STYLE)
        self._btn_stop.setToolTip("Stop")
        self._btn_stop.clicked.connect(self.stop_clicked)
        layout.addWidget(self._btn_stop)

        self._btn_pause.setVisible(False)
        self._btn_stop.setVisible(False)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self._position_bottom_right()

    def _position_bottom_right(self, width=280):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.setFixedWidth(width)
            x = geo.right() - width - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(theme.SURFACE2))
        p.setPen(QColor(theme.BORDER))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), theme.R_XL, theme.R_XL)
        p.end()

    def _cancel_hide(self):
        """Cancel any pending auto-hide so a new state isn't hidden prematurely."""
        self._hide_timer.stop()

    def _show_buttons(self, visible: bool):
        self._btn_pause.setVisible(visible)
        self._btn_stop.setVisible(visible)
        self._position_bottom_right(360 if visible else 280)

    def show_recording(self):
        self._cancel_hide()
        self._label.setText("Recording...")
        self._label.setStyleSheet(_STYLE_RECORDING)
        self._dot.start()
        self._dot.setVisible(True)
        self._duration_label.setText("0:00")
        self._btn_pause.setIcon(self._icon_pause)
        self._btn_pause.setToolTip("Pause")
        self._show_buttons(True)
        self.show()

    def show_paused(self):
        self._cancel_hide()
        self._label.setText("Paused")
        self._label.setStyleSheet(_STYLE_ACCENT)
        self._dot.stop()
        self._dot.setVisible(True)
        self._btn_pause.setIcon(self._icon_resume)
        self._btn_pause.setToolTip("Resume")
        self._show_buttons(True)
        self.show()

    def show_recovering(self):
        self._cancel_hide()
        self._dot.stop()
        self._dot.setVisible(False)
        self._label.setText("Recovering...")
        self._label.setStyleSheet(_STYLE_ACCENT)
        self._duration_label.setText("")
        self._show_buttons(False)
        self.show()

    def show_transcribing(self):
        self._cancel_hide()
        self._dot.stop()
        self._dot.setVisible(False)
        self._label.setText("Transcribing...")
        self._label.setStyleSheet(_STYLE_ACCENT)
        self._duration_label.setText("")
        self._show_buttons(False)
        self.show()

    def show_done(self, msg: str = "Copied to clipboard"):
        self._cancel_hide()
        self._dot.stop()
        self._dot.setVisible(False)
        self._label.setText(msg)
        self._label.setStyleSheet(_STYLE_SUCCESS)
        self._duration_label.setText("")
        self._show_buttons(False)
        self.show()
        self._hide_timer.start(2500)

    def show_error(self, msg: str):
        self._cancel_hide()
        self._dot.stop()
        self._dot.setVisible(False)
        self._label.setText(msg)
        self._label.setStyleSheet(_STYLE_ERROR)
        self._duration_label.setText("")
        self._show_buttons(False)
        self.show()
        self._hide_timer.start(4000)

    def update_duration(self, seconds: float):
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        self._duration_label.setText(f"{mins}:{secs:02d}")
