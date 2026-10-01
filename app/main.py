"""Maria Free Download - free, open download manager. No license, no activation."""
import datetime
import json
import os
import subprocess
import sys

from PySide6.QtCore import QProcess, QSize, Qt, QTime, QTimer, QUrl
from PySide6.QtGui import (QAction, QBrush, QColor, QDesktopServices, QFont, QGuiApplication, QIcon,
                           QKeySequence, QPainter, QPalette, QPen, QPixmap)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox,
    QStyle, QSystemTrayIcon, QTableWidget, QTableWidgetItem, QTimeEdit, QToolBar, QToolButton,
    QVBoxLayout, QWidget)

import bridge
import engine as E
import fieldbench
import player
from i18n import T, is_rtl, set_language

APP_NAME = "Maria Free Download"
VERSION = "1.9.1"
CONTACT_EMAIL = "alsfarly2@gmail.com"
COPYRIGHT_EN = "© 2026 Maria Free Download – All rights reserved – Mosul, Iraq"
COPYRIGHT_AR = "© 2026 جميع الحقوق محفوظة – الموصل، العراق"


def ltr(text):
    """Keep numbers + units (e.g. '64.5 MB', '2.1 MB/s') in the right order inside Arabic UI."""
    return f"\u2066{text}\u2069" if is_rtl() and text else text


def copyright_text():
    return COPYRIGHT_AR if is_rtl() else COPYRIGHT_EN
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------- paths & settings
def data_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    p = os.path.join(base, "JDM")
    os.makedirs(p, exist_ok=True)
    return p


def resource(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_tool(name):
    """ffmpeg / deno: bundled in <app>/tools, else from PATH."""
    import shutil
    exe = name + (".exe" if sys.platform.startswith("win") else "")
    p = os.path.join(app_dir(), "tools", exe)
    return p if os.path.exists(p) else (shutil.which(name) or "")


def extension_dir():
    return os.path.join(app_dir(), "extension")


DEFAULTS = {
    "language": "",
    "theme": "light",
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
    "connections": 8,
    "max_concurrent": 3,
    "speed_limit_kb": 0,
    "ask_on_browser_download": True,
    "notify_on_complete": True,
    "close_to_tray": True,
    "scheduler": {"enabled": False, "start": "02:00", "stop_enabled": False,
                  "stop": "08:00", "days": [0, 1, 2, 3, 4, 5, 6]},
}


def load_settings():
    s = json.loads(json.dumps(DEFAULTS))
    try:
        with open(os.path.join(data_dir(), "settings.json"), encoding="utf-8") as f:
            user = json.load(f)
        sched = {**s["scheduler"], **user.get("scheduler", {})}
        s.update(user)
        s["scheduler"] = sched
    except (OSError, ValueError):
        pass
    return s


def save_settings(s):
    data = {k: v for k, v in s.items() if k not in ("ffmpeg_path", "deno_path")}
    with open(os.path.join(data_dir(), "settings.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def show_in_folder(path):
    if sys.platform.startswith("win") and os.path.exists(path):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    else:
        open_path(os.path.dirname(path))


# ---------------------------------------------------------------- light / dark theme
DARK = {
    "window": "#1b1e23", "base": "#14161a", "alt": "#1f232a", "text": "#e6e8eb",
    "button": "#2a2f37", "mid": "#3a404a", "dim": "#8b939e", "link": "#38bdf8",
    "footer": "#16191d", "footer_border": "#2c3139", "footer_text": "#9aa3ad",
}
LIGHT_FOOTER = {"footer": "#f4f6f8", "footer_border": "#dde3e8", "footer_text": "#5b6470"}


def apply_theme(app, theme):
    """Switch the whole program between the white (light) and black (dark) look."""
    app.setStyle("Fusion")
    if theme == "dark":
        c = {k: QColor(v) for k, v in DARK.items()}
        p = QPalette()
        p.setColor(QPalette.Window, c["window"])
        p.setColor(QPalette.WindowText, c["text"])
        p.setColor(QPalette.Base, c["base"])
        p.setColor(QPalette.AlternateBase, c["alt"])
        p.setColor(QPalette.ToolTipBase, c["button"])
        p.setColor(QPalette.ToolTipText, c["text"])
        p.setColor(QPalette.PlaceholderText, c["dim"])
        p.setColor(QPalette.Text, c["text"])
        p.setColor(QPalette.Button, c["button"])
        p.setColor(QPalette.ButtonText, c["text"])
        p.setColor(QPalette.BrightText, QColor("#ff6b6b"))
        p.setColor(QPalette.Link, c["link"])
        p.setColor(QPalette.Highlight, QColor("#0e7490"))
        p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        p.setColor(QPalette.Light, c["mid"])
        p.setColor(QPalette.Midlight, c["button"])
        p.setColor(QPalette.Mid, c["mid"])
        p.setColor(QPalette.Dark, QColor("#0f1114"))
        p.setColor(QPalette.Shadow, QColor("#000000"))
        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            p.setColor(QPalette.Disabled, role, c["dim"])
        app.setPalette(p)
        app.setStyleSheet("QToolTip { color: #e6e8eb; background: #2a2f37; border: 1px solid #3a404a; }")
    else:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
    try:   # Qt 6.8+: dark / light window title bar on Windows 10/11
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark if theme == "dark" else Qt.ColorScheme.Light)
    except Exception:  # noqa: BLE001
        pass


def footer_css(theme):
    c = DARK if theme == "dark" else LIGHT_FOOTER
    return (f"#footer {{ background: {c['footer']}; border-top: 1px solid {c['footer_border']}; }}"
            f"#footer QLabel {{ color: {c['footer_text']}; }}")


def theme_icon(kind, color):
    """Small moon / sun icon drawn in code."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(color)
    if kind == "moon":
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        p.drawEllipse(10, 8, 46, 46)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.drawEllipse(26, 0, 42, 42)
    else:
        p.setBrush(col)
        p.setPen(Qt.NoPen)
        p.drawEllipse(20, 20, 24, 24)
        pen = QPen(col, 5, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        import math
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(int(32 + 18 * math.cos(a)), int(32 + 18 * math.sin(a)),
                       int(32 + 27 * math.cos(a)), int(32 + 27 * math.sin(a)))
    p.end()
    return QIcon(pm)


def media_icon(kind, color):
    """Play / pause / stop icons drawn in the theme colour (standard ones are black)."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    if kind == "play":
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF([QPointF(18, 10), QPointF(54, 32), QPointF(18, 54)]))
    elif kind == "down":
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        p.drawRect(26, 8, 12, 26)
        p.drawPolygon(QPolygonF([QPointF(12, 32), QPointF(52, 32), QPointF(32, 56)]))
    elif kind == "pause":
        p.drawRoundedRect(16, 12, 11, 40, 3, 3)
        p.drawRoundedRect(37, 12, 11, 40, 3, 3)
    else:
        p.drawRoundedRect(15, 15, 34, 34, 4, 4)
    p.end()
    return QIcon(pm)


def logo_pixmap(size):
    """The round Maria Free Download logo, scaled smoothly."""
    pm = QPixmap(resource(os.path.join("assets", "logo.png")))
    if pm.isNull():
        return QPixmap()
    pm.setDevicePixelRatio(1)
    ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1
    out = pm.scaled(int(size * ratio), int(size * ratio), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out.setDevicePixelRatio(ratio)
    return out


def iraq_flag(width=30, height=20):
    """Small Iraqi flag drawn in code (red / white / black, green 'الله أكبر')."""
    scale = 3                                   # draw big, then scale down smoothly
    w, h = width * scale, height * scale
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    band = h / 3
    p.fillRect(0, 0, w, round(band), QColor("#CE1126"))
    p.fillRect(0, round(band), w, round(band * 2) - round(band), QColor("#FFFFFF"))
    p.fillRect(0, round(band * 2), w, h - round(band * 2), QColor("#000000"))
    f = QFont("Arial")
    f.setBold(True)
    f.setPixelSize(int(band * 0.82))
    p.setFont(f)
    p.setPen(QColor("#007A3D"))
    p.drawText(0, round(band), w, round(band), Qt.AlignCenter, "الله أكبر")
    p.setPen(QColor(0, 0, 0, 60))
    p.drawRect(0, 0, w - 1, h - 1)
    p.end()
    return pm.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


# ---------------------------------------------------------------- speed limit
def limit_raw(kb):
    kb = int(kb or 0)
    if kb >= 1024 and kb % 1024 == 0:
        return f"{kb // 1024} MB/s"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB/s"
    return f"{kb} KB/s"


def fmt_limit(kb):
    return T("Unlimited") if int(kb or 0) <= 0 else ltr(limit_raw(kb))


class SpeedLimitEdit(QWidget):
    """Number + unit (KB/s or MB/s). 0 = unlimited."""

    def __init__(self, kb=0, parent=None):
        super().__init__(parent)
        self.num = QSpinBox()
        self.num.setRange(0, 1_000_000)
        self.num.setSpecialValueText(T("Unlimited"))
        self.unit = QComboBox()
        self.unit.addItem("KB/s", 1)
        self.unit.addItem("MB/s", 1024)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.num, 1)
        lay.addWidget(self.unit)
        self.setLayoutDirection(Qt.LeftToRight)
        self.set_kb(kb)

    def set_kb(self, kb):
        kb = max(0, int(kb or 0))
        if kb and kb % 1024 == 0:
            self.unit.setCurrentIndex(1)
            self.num.setValue(kb // 1024)
        else:
            self.unit.setCurrentIndex(0)
            self.num.setValue(kb)

    def kb(self):
        return self.num.value() * int(self.unit.currentData())


class SpeedLimitDialog(QDialog):
    PRESETS = [0, 128, 256, 512, 1024, 2048, 5120, 10240]

    def __init__(self, parent, title, kb, note=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        if note:
            n = QLabel(note)
            n.setWordWrap(True)
            lay.addWidget(n)
        grid = QGridLayout()
        self.edit = SpeedLimitEdit(kb)
        for i, p in enumerate(self.PRESETS):
            b = QPushButton(fmt_limit(p))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=p: self.edit.set_kb(v))
            grid.addWidget(b, i // 4, i % 4)
        lay.addLayout(grid)
        form = QFormLayout()
        form.addRow(T("Maximum speed:"), self.edit)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(T("OK"))
        bb.button(QDialogButtonBox.Cancel).setText(T("Cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def kb(self):
        return self.edit.kb()


# ---------------------------------------------------------------- dialogs
class AddDialog(QDialog):
    def __init__(self, parent, settings, url="", filename=""):
        super().__init__(parent)
        self.setWindowTitle(T("Add Download"))
        self.setMinimumWidth(560)
        self.url = QLineEdit(url)
        self.url.setPlaceholderText("https://example.com/file.zip")
        self.name = QLineEdit(filename)
        self.name.setPlaceholderText(T("Automatic (from server)"))
        self.folder = QLineEdit(settings["download_dir"])
        browse = QPushButton(T("Browse…"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder)
        row.addWidget(browse)
        self.conn = QSpinBox()
        self.conn.setRange(1, 32)
        self.conn.setValue(int(settings["connections"]))
        self.quality = QComboBox()
        for q in E.QUALITIES:
            self.quality.addItem(T(q), q)
        self.quality_label = QLabel(T("Video quality:"))
        self.video_hint = QLabel(T("Video page detected – Maria will download the video itself."))
        self.video_hint.setStyleSheet("color: #0e7490; font-weight: bold")
        form = QFormLayout()
        form.addRow(T("URL:"), self.url)
        form.addRow(T("File name:"), self.name)
        form.addRow(T("Save to:"), row)
        form.addRow(T("Connections:"), self.conn)
        self.limit = SpeedLimitEdit(0)
        self.limit.setToolTip(T("Only this file. The overall limit in Settings still applies."))
        form.addRow(T("Speed limit for this file:"), self.limit)
        form.addRow(self.quality_label, self.quality)
        form.addRow(self.video_hint)
        self.url.textChanged.connect(self._check_video)
        self._check_video()
        self.choice = None
        now = QPushButton(T("Download Now"))
        now.setDefault(True)
        later = QPushButton(T("Add to Schedule"))
        paused = QPushButton(T("Add Paused"))
        cancel = QPushButton(T("Cancel"))
        now.clicked.connect(lambda: self._done(E.QUEUED))
        later.clicked.connect(lambda: self._done(E.SCHEDULED))
        paused.clicked.connect(lambda: self._done(E.PAUSED))
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch()
        for b in (now, later, paused, cancel):
            btns.addWidget(b)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addLayout(btns)

    def _check_video(self):
        self.is_video = E.is_video_url(self.url.text().strip())
        for w in (self.quality, self.quality_label, self.video_hint):
            w.setVisible(self.is_video)
        self.name.setEnabled(not self.is_video)
        self.name.setPlaceholderText(T("Taken from the video title") if self.is_video
                                     else T("Automatic (from server)"))

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, T("Save to:"), self.folder.text())
        if d:
            self.folder.setText(d)

    def _done(self, status):
        u = self.url.text().strip()
        if not u.lower().startswith(("http://", "https://")):
            QMessageBox.warning(self, APP_NAME, T("Please enter a valid http:// or https:// URL."))
            return
        self.choice = status
        self.accept()


class SettingsDialog(QDialog):
    def __init__(self, parent, s):
        super().__init__(parent)
        self.setWindowTitle(T("Settings"))
        self.setMinimumWidth(480)
        self.s = s
        self.theme = QComboBox()
        self.theme.addItem(T("Light (white)"), "light")
        self.theme.addItem(T("Dark (black)"), "dark")
        self.theme.setCurrentIndex(1 if s.get("theme") == "dark" else 0)
        self.lang = QComboBox()
        self.lang.addItem("English", "en")
        self.lang.addItem("العربية", "ar")
        self.lang.setCurrentIndex(1 if s.get("language") == "ar" else 0)
        self.folder = QLineEdit(s["download_dir"])
        b = QPushButton(T("Browse…"))
        b.clicked.connect(lambda: self.folder.setText(
            QFileDialog.getExistingDirectory(self, T("Download folder"), self.folder.text())
            or self.folder.text()))
        row = QHBoxLayout()
        row.addWidget(self.folder)
        row.addWidget(b)
        self.conn = QSpinBox()
        self.conn.setRange(1, 32)
        self.conn.setValue(int(s["connections"]))
        self.maxc = QSpinBox()
        self.maxc.setRange(1, 10)
        self.maxc.setValue(int(s["max_concurrent"]))
        self.limit = SpeedLimitEdit(int(s["speed_limit_kb"]))
        self.ask = QCheckBox(T("Show 'Add Download' window for browser downloads"))
        self.ask.setChecked(bool(s["ask_on_browser_download"]))
        self.notify = QCheckBox(T("Notify when a download completes"))
        self.notify.setChecked(bool(s["notify_on_complete"]))
        self.tray = QCheckBox(T("Closing the window keeps Maria Free Download running in the tray"))
        self.tray.setChecked(bool(s["close_to_tray"]))
        form = QFormLayout()
        form.addRow(T("Language:"), self.lang)
        form.addRow(T("Theme:"), self.theme)
        form.addRow(T("Default folder:"), row)
        form.addRow(T("Connections per file:"), self.conn)
        form.addRow(T("Simultaneous downloads:"), self.maxc)
        form.addRow(T("Speed limit (all downloads):"), self.limit)
        form.addRow(self.ask)
        form.addRow(self.notify)
        form.addRow(self.tray)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(bb)

    def apply(self):
        self.s["download_dir"] = self.folder.text().strip() or DEFAULTS["download_dir"]
        self.s["connections"] = self.conn.value()
        self.s["max_concurrent"] = self.maxc.value()
        self.s["speed_limit_kb"] = self.limit.kb()
        self.s["ask_on_browser_download"] = self.ask.isChecked()
        self.s["notify_on_complete"] = self.notify.isChecked()
        self.s["close_to_tray"] = self.tray.isChecked()
        self.s["language"] = self.lang.currentData()
        self.s["theme"] = self.theme.currentData()


class SchedulerDialog(QDialog):
    def __init__(self, parent, sched):
        super().__init__(parent)
        self.setWindowTitle(T("Scheduler"))
        self.sched = sched
        self.enabled = QCheckBox(T("Enable scheduler"))
        self.enabled.setChecked(sched["enabled"])
        self.start = QTimeEdit(QTime.fromString(sched["start"], "HH:mm"))
        self.start.setDisplayFormat("HH:mm")
        self.stop_en = QCheckBox(T("Stop (pause) downloads at:"))
        self.stop_en.setChecked(sched["stop_enabled"])
        self.stop = QTimeEdit(QTime.fromString(sched["stop"], "HH:mm"))
        self.stop.setDisplayFormat("HH:mm")
        days = QHBoxLayout()
        self.day_boxes = []
        for i, n in enumerate(DAYS):
            c = QCheckBox(T(n))
            c.setChecked(i in sched["days"])
            self.day_boxes.append(c)
            days.addWidget(c)
        grp = QGroupBox(T("Downloads marked 'Scheduled' start automatically"))
        form = QFormLayout(grp)
        form.addRow(T("Start at:"), self.start)
        form.addRow(self.stop_en, self.stop)
        form.addRow(T("Days:"), days)
        hint = QLabel(T("Tip: right-click a download → 'Move to Schedule'."))
        hint.setStyleSheet("color: gray")
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.enabled)
        lay.addWidget(grp)
        lay.addWidget(hint)
        lay.addWidget(bb)

    def apply(self):
        self.sched["enabled"] = self.enabled.isChecked()
        self.sched["start"] = self.start.time().toString("HH:mm")
        self.sched["stop_enabled"] = self.stop_en.isChecked()
        self.sched["stop"] = self.stop.time().toString("HH:mm")
        self.sched["days"] = [i for i, c in enumerate(self.day_boxes) if c.isChecked()]


# ---------------------------------------------------------------- small dialogs
class MeasureDialog(QDialog):
    """Research: field measurements for the segmentation study (results -> CSV)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(T("Field measurement"))
        self.setMinimumSize(620, 560)
        self.run = None
        self.link = QComboBox()
        self.link.setEditable(True)
        for code in ("F1", "F2", "F3", "M1", "M2", "M3"):
            self.link.addItem(code)
        self.urls = QPlainTextEdit()
        self.urls.setPlaceholderText("https://your-server/test-100MB.bin")
        self.urls.setFixedHeight(70)
        self.reps = QSpinBox()
        self.reps.setRange(1, 10)
        self.reps.setValue(3)
        self.note = QLineEdit()
        self.note.setPlaceholderText(T("e.g. 4G, 3 signal bars, home Wi-Fi"))
        form = QFormLayout()
        form.addRow(T("Connection code:"), self.link)
        form.addRow(T("Test file URL(s), one per line:"), self.urls)
        form.addRow(T("Repetitions:"), self.reps)
        form.addRow(T("Note:"), self.note)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.logbox = QPlainTextEdit()
        self.logbox.setReadOnly(True)
        self.start_btn = QPushButton(T("Start measurement"))
        self.stop_btn = QPushButton(T("Stop"))
        self.stop_btn.setEnabled(False)
        folder = QPushButton(T("Open results folder"))
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        folder.clicked.connect(lambda: open_path(fieldbench.results_dir()))
        row = QHBoxLayout()
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addStretch()
        row.addWidget(folder)
        hint = QLabel(T("Pause other downloads and close streaming apps while measuring."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray")
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        lay.addLayout(row)
        lay.addWidget(self.bar)
        lay.addWidget(self.logbox, 1)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)

    def start(self):
        urls = [u.strip() for u in self.urls.toPlainText().splitlines() if u.strip().lower().startswith("http")]
        if not urls:
            QMessageBox.warning(self, APP_NAME, T("Please enter a valid http:// or https:// URL."))
            return
        self.run = fieldbench.FieldRun(urls, self.link.currentText().strip() or "X", self.reps.value(),
                                       self.note.text().strip())
        self.bar.setRange(0, self.run.total)
        self.bar.setValue(0)
        self.logbox.appendPlainText(f"{T('Connection code:')} {self.run.link} · {fieldbench.time_slot()}")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.run.start()
        self.timer.start(300)

    def stop(self):
        if self.run:
            self.run.stop_flag.set()
            self.stop_btn.setEnabled(False)

    def poll(self):
        while self.run and not self.run.events.empty():
            ev = self.run.events.get_nowait()
            if ev[0] == "log":
                self.logbox.appendPlainText(ev[1])
            elif ev[0] == "progress":
                self.bar.setValue(ev[1])
            elif ev[0] == "end":
                self.timer.stop()
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.logbox.appendPlainText(f"{T('Saved to')}: {ev[1]}")

    def closeEvent(self, e):
        self.stop()
        super().closeEvent(e)


class LanguageDialog(QDialog):
    """First run: choose Arabic or English."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maria Free Download – Language / اللغة")
        self.choice = "en"
        flag = QLabel()
        flag.setPixmap(logo_pixmap(120))
        flag.setAlignment(Qt.AlignCenter)
        q = QLabel("Choose the program language\nاختر لغة البرنامج")
        q.setAlignment(Qt.AlignCenter)
        q.setStyleSheet("font-size: 14px; font-weight: 600;")
        ar = QPushButton("العربية")
        en = QPushButton("English")
        for b in (ar, en):
            b.setMinimumSize(150, 44)
            b.setStyleSheet("QPushButton { font-size: 15px; border-radius: 8px; border: 1px solid #0e7490; "
                            "padding: 6px; } QPushButton:hover { background: #0e7490; color: white; }")
        ar.clicked.connect(lambda: self._pick("ar"))
        en.clicked.connect(lambda: self._pick("en"))
        row = QHBoxLayout()
        row.addWidget(ar)
        row.addWidget(en)
        lay = QVBoxLayout(self)
        lay.addWidget(flag)
        lay.addWidget(q)
        lay.addLayout(row)

    def _pick(self, lang):
        self.choice = lang
        self.accept()


# ---------------------------------------------------------------- main window
COLS = ["File Name", "Size", "Progress", "Speed", "Elapsed", "Time Left", "Status", "Connections",
        "Added", "Action"]
C_NAME, C_SIZE, C_PROG, C_SPEED, C_ELAPSED, C_ETA, C_STATUS, C_CONN, C_ADDED, C_ACTION = range(10)

OPEN_BTN_CSS = ("QPushButton { background: #0e7490; color: white; border: none; border-radius: 5px; "
                "padding: 2px 10px; font-weight: 600; } QPushButton:hover { background: #0c5f75; }")


class MainWindow(QMainWindow):
    def __init__(self, settings, start_hidden=False):
        super().__init__()
        self.settings = settings
        self.engine = E.Engine(data_dir(), settings)
        self.icon = QIcon(resource(os.path.join("assets", "jdm.ico")))
        self.setWindowIcon(self.icon)
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1120, 600)
        self._rows = []                    # download ids in table order
        self._action_state = {}            # row -> (id, status) of the Open button
        self._last_status = {}
        self._fired = {}                   # scheduler: event -> date string
        self._viewers = []
        self._quitting = False

        self._build_toolbar()
        self._build_central()
        self._build_tray()
        self.speed_label = QLabel()
        self.limit_label = QToolButton()
        self.limit_label.setAutoRaise(True)
        self.limit_label.setCursor(Qt.PointingHandCursor)
        self.limit_label.setToolTip(T("Click to change the speed limit"))
        self.limit_label.clicked.connect(self.global_limit_dialog)
        self.statusBar().addPermanentWidget(self.limit_label)
        self.statusBar().addPermanentWidget(self.speed_label)

        self.server = bridge.start_server()
        if self.server is None:
            self._flash(T("Browser bridge port is busy – browser capture disabled."))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(500)
        self._refresh(full=True)
        if not start_hidden:
            self.show()

    # ---- ui construction
    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QSize(28, 28))
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        tb.setMovable(False)
        self.addToolBar(tb)
        st = self.style()

        def act(text, icon, slot, shortcut=None):
            a = QAction(st.standardIcon(icon), T(text), self)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            tb.addAction(a)
            return a

        act("Add URL", QStyle.SP_FileDialogNewFolder, self.add_dialog, "Ctrl+N")
        self.media_actions = {
            "play": act("Resume", QStyle.SP_MediaPlay, self.resume_selected),
            "pause": act("Pause", QStyle.SP_MediaPause, self.pause_selected),
            "stop": act("Pause All", QStyle.SP_MediaStop, lambda: self.engine.stop_all()),
        }
        act("Delete", QStyle.SP_TrashIcon, self.delete_selected, "Del")
        tb.addSeparator()
        act("Scheduler", QStyle.SP_BrowserReload, self.scheduler_dialog)
        self.limit_action = act("Speed Limit", QStyle.SP_MediaSeekForward, self.global_limit_dialog)
        act("Settings", QStyle.SP_FileDialogDetailedView, self.settings_dialog)
        act("Open Folder", QStyle.SP_DirOpenIcon,
            lambda: open_path(self.settings["download_dir"]))
        act("Browser", QStyle.SP_ComputerIcon, self.extension_help)
        act("Measure", QStyle.SP_FileDialogInfoView, lambda: MeasureDialog(self).exec())
        tb.addSeparator()
        self.theme_action = QAction(self)
        self.theme_action.triggered.connect(self.toggle_theme)
        tb.addAction(self.theme_action)
        self._update_theme_action()
        act("About", QStyle.SP_MessageBoxInformation, self.about)

    def _build_central(self):
        t = QTableWidget(0, len(COLS))
        t.setHorizontalHeaderLabels([T(c) for c in COLS])
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(30)
        t.setAlternatingRowColors(True)
        t.setContextMenuPolicy(Qt.CustomContextMenu)
        t.customContextMenuRequested.connect(self._context_menu)
        t.doubleClicked.connect(self._double_click)
        h = t.horizontalHeader()
        h.setSectionResizeMode(C_NAME, QHeaderView.Stretch)
        for i, w in enumerate([0, 85, 140, 165, 95, 90, 100, 80, 125, 90]):
            if w:
                t.setColumnWidth(i, w)
        self.table = t

        # footer: copyright on one side; flag above the e-mail on the other
        footer = QFrame()
        footer.setObjectName("footer")
        footer.setStyleSheet(footer_css(self.settings.get("theme", "light")))
        self.footer = footer
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 4, 12, 4)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(40))
        fl.addWidget(logo, 0, Qt.AlignVCenter)
        fl.addSpacing(6)
        self.copyright_label = QLabel(copyright_text())
        fl.addWidget(self.copyright_label, 1, Qt.AlignVCenter)
        right = QVBoxLayout()
        right.setSpacing(3)
        flag = QLabel()
        flag.setPixmap(iraq_flag(30, 20))
        flag.setToolTip(T("Made in Mosul, Iraq"))
        flag.setAlignment(Qt.AlignCenter)
        right.addWidget(flag, 0, Qt.AlignHCenter)
        row = QHBoxLayout()
        row.setSpacing(10)
        mail = QLabel()
        self.mail_label = mail
        self._set_mail_html()
        mail.setOpenExternalLinks(True)
        mail.setLayoutDirection(Qt.LeftToRight)
        row.addWidget(mail)
        right.addLayout(row)
        fl.addLayout(right)

        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(t, 1)
        v.addWidget(footer)
        self.setCentralWidget(central)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self)
        m = QMenu()
        m.addAction(T("Show Maria Free Download"), self.show_normal)
        m.addAction(T("Add URL…"), self.add_dialog)
        m.addAction(T("Pause All"), lambda: self.engine.stop_all())
        m.addSeparator()
        m.addAction(T("Exit"), self.quit)
        self.tray.setContextMenu(m)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(
            lambda r: self.show_normal() if r in (QSystemTrayIcon.Trigger,
                                                  QSystemTrayIcon.DoubleClick) else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    # ---- helpers
    def _flash(self, text, ms=8000):
        self.statusBar().showMessage(text, ms)

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def selected(self):
        ids = {self._rows[i.row()] for i in self.table.selectionModel().selectedRows()
               if i.row() < len(self._rows)}
        return [d for d in self.engine.downloads if d.id in ids]

    # ---- open / play
    def open_download(self, d, external=False):
        if not d.path or not os.path.exists(d.path):
            QMessageBox.warning(self, APP_NAME, T("File not found. It may have been moved or deleted."))
            return
        if not external and player.media_kind(d.path):
            try:
                v = player.MediaViewer(self, d.path, open_path)
                if is_rtl():
                    v.setLayoutDirection(Qt.LeftToRight)   # player controls read left→right
                v.show()
                self._viewers.append(v)
                v.destroyed.connect(lambda *_: self._viewers.remove(v) if v in self._viewers else None)
                return
            except Exception:  # noqa: BLE001  (no multimedia backend) -> system player
                pass
        open_path(d.path)

    def _make_open_button(self, d):
        kind = player.media_kind(d.path)
        text = {"video": "Play", "audio": "Play", "image": "View"}.get(kind, "Open")
        icon = media_icon("play", "#ffffff") if kind in ("video", "audio") \
            else self.style().standardIcon(QStyle.SP_DialogOpenButton)
        b = QPushButton(icon, T(text))
        b.setStyleSheet(OPEN_BTN_CSS)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda: self.open_download(d))
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(b)
        return w

    # ---- actions
    def add_dialog(self, url="", filename="", headers=None, from_browser=False, quality=""):
        if not url:
            clip = QGuiApplication.clipboard().text().strip()
            if clip.lower().startswith(("http://", "https://")) and " " not in clip:
                url = clip
        if from_browser and not self.settings["ask_on_browser_download"]:
            self.engine.add(url, filename=filename or None, headers=headers,
                            quality=quality if quality in E.QUALITIES else "Best quality")
            self.tray.showMessage(APP_NAME, f"{T('Download added:')}\n{filename or url}",
                                  QSystemTrayIcon.Information, 3000)
            return
        self.show_normal()
        dlg = AddDialog(self, self.settings, url, filename)
        if quality in E.QUALITIES:
            dlg.quality.setCurrentIndex(max(0, dlg.quality.findData(quality)))
        dlg.setWindowFlag(Qt.WindowStaysOnTopHint, from_browser)
        if dlg.exec() == QDialog.Accepted:
            video = dlg.is_video
            self.engine.add(dlg.url.text().strip(), dlg.folder.text().strip(),
                            None if video else (dlg.name.text().strip() or None),
                            dlg.conn.value(), headers, status=dlg.choice,
                            kind="video" if video else "file",
                            quality=dlg.quality.currentData(), limit_kb=dlg.limit.kb())
            self._refresh(full=True)

    def resume_selected(self):
        for d in self.selected():
            self.engine.resume(d)

    def pause_selected(self):
        for d in self.selected():
            self.engine.pause(d)

    def schedule_selected(self):
        for d in self.selected():
            if d.status != E.COMPLETED:
                d.stop(E.SCHEDULED)
                d.status = E.SCHEDULED
        self.engine.request_save()

    def global_limit_dialog(self):
        dlg = SpeedLimitDialog(self, T("Speed Limit"), self.settings["speed_limit_kb"],
                               T("Maximum total speed for all downloads together."))
        if dlg.exec() == QDialog.Accepted:
            self.settings["speed_limit_kb"] = dlg.kb()
            self.engine.set_speed_limit_kb(dlg.kb())
            save_settings(self.settings)
            self._flash(T("Speed limit: {v}", v=fmt_limit(dlg.kb())))
            self._refresh()

    def file_limit_dialog(self):
        items = [d for d in self.selected() if d.status != E.COMPLETED]
        if not items:
            return
        title = items[0].filename if len(items) == 1 else T("{n} files", n=len(items))
        dlg = SpeedLimitDialog(self, T("Speed limit for this file"), items[0].limit_kb,
                               f"{title}\n{T('Only this file. The overall limit in Settings still applies.')}")
        if dlg.exec() == QDialog.Accepted:
            for d in items:
                d.set_limit_kb(dlg.kb())
            self._refresh()

    def delete_selected(self):
        items = self.selected()
        if not items:
            return
        box = QMessageBox(self)
        box.setWindowTitle(T("Delete"))
        box.setText(T("Remove {n} download(s) from the list?", n=len(items)))
        also = QCheckBox(T("Also delete the file(s) from disk"))
        box.setCheckBox(also)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if box.exec() == QMessageBox.Yes:
            for d in items:
                self.engine.remove(d, also.isChecked())
            self._refresh(full=True)

    def settings_dialog(self):
        old_lang = self.settings.get("language") or "en"
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply()
            self.engine.set_speed_limit_kb(self.settings["speed_limit_kb"])
            self.set_theme(self.settings.get("theme", "light"))
            new_lang = self.settings.get("language") or "en"
            if new_lang != old_lang:
                set_language(new_lang)
                if QMessageBox.question(self, APP_NAME, T("Restart Maria Free Download now to apply the new language?")) \
                        == QMessageBox.Yes:
                    self.restart()

    def _update_theme_action(self):
        col = "#e6e8eb" if self.settings.get("theme") == "dark" else "#1f2937"
        for kind, a in self.media_actions.items():
            a.setIcon(media_icon(kind, col))
        if self.settings.get("theme") == "dark":
            self.theme_action.setIcon(theme_icon("sun", "#f5b83d"))
            self.theme_action.setText(T("Light mode"))
        else:
            self.theme_action.setIcon(theme_icon("moon", "#334155"))
            self.theme_action.setText(T("Dark mode"))

    def _set_mail_html(self):
        col = "#38bdf8" if self.settings.get("theme") == "dark" else "#0e7490"
        self.mail_label.setText(f"<a href='mailto:{CONTACT_EMAIL}' style='color:{col};text-decoration:none'>"
                                f"✉ {CONTACT_EMAIL}</a>")

    def set_theme(self, theme):
        self.settings["theme"] = theme
        apply_theme(QApplication.instance(), theme)
        self.footer.setStyleSheet(footer_css(theme))
        self._set_mail_html()
        self._update_theme_action()
        save_settings(self.settings)

    def toggle_theme(self):
        self.set_theme("light" if self.settings.get("theme") == "dark" else "dark")

    def restart(self):
        self._quitting = True
        self._shutdown()
        args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
        QProcess.startDetached(sys.executable, [a for a in args if a != "--minimized"])
        QApplication.quit()

    def scheduler_dialog(self):
        dlg = SchedulerDialog(self, self.settings["scheduler"])
        if dlg.exec() == QDialog.Accepted:
            dlg.apply()
            save_settings(self.settings)

    def extension_help(self):
        path = extension_dir()
        QGuiApplication.clipboard().setText(path)
        box = QMessageBox(self)
        box.setWindowTitle(T("Add Maria Free Download to Chrome / Edge"))
        box.setTextFormat(Qt.RichText)
        box.setText(T("EXT_HELP", path=path))
        chrome = box.addButton(T("Open Chrome"), QMessageBox.AcceptRole)
        edge = box.addButton(T("Open Edge"), QMessageBox.AcceptRole)
        box.addButton(T("Open Folder"), QMessageBox.HelpRole).clicked.connect(lambda: open_path(path))
        box.addButton(T("Close"), QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if sys.platform.startswith("win") and clicked in (chrome, edge):
            target = ("chrome", "chrome://extensions") if clicked is chrome \
                else ("msedge", "edge://extensions")
            subprocess.Popen(["cmd", "/c", "start", "", target[0], target[1]],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def about(self):
        box = QMessageBox(self)
        box.setWindowTitle(T("About"))
        box.setIconPixmap(logo_pixmap(110))
        box.setTextFormat(Qt.RichText)
        ff = T("found") if self.settings.get("ffmpeg_path") else T("not found")
        dd = T("found") if self.settings.get("deno_path") else T("not found")
        box.setText(
            f"<b>{APP_NAME}</b> {VERSION}<br>{copyright_text()}<br><br>"
            f"{T('Email:')} <a href='mailto:{CONTACT_EMAIL}'>{CONTACT_EMAIL}</a><br><br>"
            f"{T('Free download manager – no serial, no activation.')}<br>"
            f"{T('Multi-connection downloads, pause/resume, scheduler, speed limiter, browser capture, video downloads and a built-in media player.')}"
            f"<br><br>FFmpeg: {ff}<br>Deno: {dd}")
        box.addButton(T("Close"), QMessageBox.RejectRole)
        box.exec()

    def _context_menu(self, pos):
        items = self.selected()
        if not items:
            return
        d = items[0]
        m = QMenu(self)
        if d.status == E.COMPLETED:
            if player.media_kind(d.path):
                m.addAction(T("Play in Maria"), lambda: self.open_download(d))
            else:
                m.addAction(T("Open"), lambda: self.open_download(d))
            m.addAction(T("Open with default program"), lambda: self.open_download(d, external=True))
            m.addAction(T("Open Folder"), lambda: show_in_folder(d.path))
            m.addAction(T("Download Again"), lambda: self.engine.redownload(d))
        else:
            m.addAction(T("Resume"), self.resume_selected)
            m.addAction(T("Pause"), self.pause_selected)
            m.addAction(T("Move to Schedule"), self.schedule_selected)
            m.addAction(T("Speed limit for this file…"), self.file_limit_dialog)
            m.addAction(T("Open Folder"), lambda: open_path(d.save_dir))
        m.addAction(T("Copy URL"), lambda: QGuiApplication.clipboard().setText(d.url))
        if d.error:
            m.addAction(T("Show Error"), lambda: QMessageBox.warning(self, T("Error"), d.error))
        m.addSeparator()
        m.addAction(T("Delete"), self.delete_selected)
        m.exec(self.table.viewport().mapToGlobal(pos))

    def _double_click(self, index):
        if index.row() < len(self._rows):
            d = self.engine.get(self._rows[index.row()])
            if d and d.status == E.COMPLETED:
                self.open_download(d)
            elif d and d.status in (E.PAUSED, E.ERROR):
                self.engine.resume(d)

    # ---- periodic work
    def _tick(self):
        while not bridge.events.empty():
            kind, data = bridge.events.get_nowait()
            if kind == "show":
                self.show_normal()
            elif kind == "add":
                headers = {}
                if data.get("referrer"):
                    headers["Referer"] = data["referrer"]
                if data.get("cookies"):
                    headers["Cookie"] = data["cookies"]
                if data.get("userAgent"):
                    headers["User-Agent"] = data["userAgent"]
                self.add_dialog(data["url"], data.get("filename", ""), headers, from_browser=True,
                                quality=data.get("quality", ""))
        self._scheduler()
        self.engine.tick()
        self._refresh()

    def _scheduler(self):
        sc = self.settings["scheduler"]
        if not sc["enabled"]:
            return
        now = datetime.datetime.now()
        if now.weekday() not in sc["days"]:
            return
        hm, today = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
        if hm == sc["start"] and self._fired.get("start") != today:
            self._fired["start"] = today
            self.engine.start_scheduled()
            self._flash(T("Scheduler: scheduled downloads started"))
        if sc["stop_enabled"] and hm == sc["stop"] and self._fired.get("stop") != today:
            self._fired["stop"] = today
            for d in self.engine.downloads:
                if d.status in (E.DOWNLOADING, E.QUEUED):
                    d.stop(E.SCHEDULED)
            self.engine.request_save()
            self._flash(T("Scheduler: downloads stopped"))

    def _refresh(self, full=False):
        items = list(self.engine.downloads)
        ids = [d.id for d in items]
        if full or ids != self._rows:
            sel = {d.id for d in self.selected()} if self._rows else set()
            self.table.setRowCount(len(items))
            self._action_state = {}
            for r, d in enumerate(items):
                for c in range(len(COLS)):
                    if c == C_PROG:
                        bar = QProgressBar()
                        bar.setRange(0, 1000)
                        bar.setTextVisible(True)
                        bar.setAlignment(Qt.AlignCenter)
                        self.table.setCellWidget(r, c, bar)
                    elif c == C_ACTION:
                        self.table.removeCellWidget(r, c)
                    else:
                        it = QTableWidgetItem()
                        if c in (C_SIZE, C_SPEED, C_ELAPSED, C_ETA, C_CONN):
                            it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.table.setItem(r, c, it)
            self._rows = ids
            for r, i in enumerate(ids):
                if i in sel:
                    self.table.selectRow(r)
        st = self.style()
        for r, d in enumerate(items):
            running = d.status == E.DOWNLOADING
            icon = {E.COMPLETED: QStyle.SP_DialogApplyButton, E.ERROR: QStyle.SP_MessageBoxCritical,
                    E.PAUSED: QStyle.SP_MediaPause, E.DOWNLOADING: QStyle.SP_ArrowDown,
                    E.SCHEDULED: QStyle.SP_BrowserReload}.get(d.status, QStyle.SP_FileIcon)
            it = self.table.item(r, C_NAME)
            it.setText(d.filename)
            if d.status in (E.DOWNLOADING, E.PAUSED):
                col = "#22a6c3" if d.status == E.DOWNLOADING else (
                    "#e6e8eb" if self.settings.get("theme") == "dark" else "#1f2937")
                it.setIcon(media_icon("down" if d.status == E.DOWNLOADING else "pause", col))
            else:
                it.setIcon(st.standardIcon(icon))
            it.setToolTip(d.url + (f"\n\n{T('Error')}: {d.error}" if d.error else ""))
            self.table.item(r, C_SIZE).setText(T("Unknown") if d.size is None or d.size < 0
                                               else ltr(E.human_size(d.size)))
            bar = self.table.cellWidget(r, C_PROG)
            p = d.progress()
            bar.setValue(int(p * 10))
            bar.setFormat(ltr(f"{p:.1f}%" if d.size > 0 else E.human_size(d.downloaded)))
            sp = self.table.item(r, C_SPEED)
            txt = E.human_size(d.speed) + "/s" if running else ""
            if d.limit_kb and d.status != E.COMPLETED:
                txt = (txt + " / " if txt else "≤ ") + limit_raw(d.limit_kb)
            sp.setText(ltr(txt) if txt else "")
            sp.setToolTip(T("Speed limit for this file: {v}", v=fmt_limit(d.limit_kb)))
            el = d.elapsed_now()
            self.table.item(r, C_ELAPSED).setText(ltr(E.human_time(el)) if el >= 1 else "")
            self.table.item(r, C_ELAPSED).setToolTip(
                T("Total download time") if d.status == E.COMPLETED else T("Time spent downloading so far"))
            if running:
                eta = E.human_time(d.eta())
                self.table.item(r, C_ETA).setText(ltr(eta) if eta else "…")
            else:
                self.table.item(r, C_ETA).setText("")
            self.table.item(r, C_STATUS).setText(T(d.status))
            self.table.item(r, C_CONN).setText(str(d.live_connections) if running else "")
            self.table.item(r, C_ADDED).setText(
                ltr(datetime.datetime.fromtimestamp(d.added).strftime("%Y-%m-%d %H:%M")))
            # "Open / Play" button for finished files
            state = (d.id, d.status, d.path)
            if self._action_state.get(r) != state:
                self._action_state[r] = state
                if d.status == E.COMPLETED:
                    self.table.setCellWidget(r, C_ACTION, self._make_open_button(d))
                else:
                    self.table.removeCellWidget(r, C_ACTION)
            prev = self._last_status.get(d.id)
            if prev and prev != E.COMPLETED and d.status == E.COMPLETED \
                    and self.settings["notify_on_complete"]:
                self.tray.showMessage(T("Download complete"), d.filename,
                                      QSystemTrayIcon.Information, 4000)
            self._last_status[d.id] = d.status
        total = self.engine.total_speed()
        active = sum(1 for d in items if d.status == E.DOWNLOADING)
        self.speed_label.setText(f"  {T('{n} active', n=active)}  |  {ltr(E.human_size(total) + '/s')}  ")
        lim = self.settings["speed_limit_kb"]
        self.limit_label.setText(T("Speed limit: {v}", v=fmt_limit(lim)) if lim else T("No speed limit"))

    # ---- window lifecycle
    def closeEvent(self, ev):
        if not self._quitting and self.settings["close_to_tray"] and \
                QSystemTrayIcon.isSystemTrayAvailable():
            ev.ignore()
            self.hide()
            if not self.settings.get("_tray_hint_shown"):
                self.settings["_tray_hint_shown"] = True
                save_settings(self.settings)
                self.tray.showMessage(APP_NAME, T("Maria Free Download is still running in the tray."),
                                      QSystemTrayIcon.Information, 3000)
            return
        self._shutdown()
        ev.accept()
        QApplication.quit()

    def quit(self):
        self._quitting = True
        self.close()

    def _shutdown(self):
        if getattr(self, "_down", False):
            return
        self._down = True
        self.timer.stop()
        for v in list(self._viewers):
            v.close()
        self.engine.shutdown()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.tray.hide()


def main():
    args = sys.argv[1:]
    url = next((a for a in args if a.lower().startswith(("http://", "https://"))), None)
    if bridge.signal_running_instance(url=url):
        return 0                                      # already running -> it shows itself
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    settings = load_settings()
    apply_theme(app, settings.get("theme", "light"))
    if not settings.get("language") and "--minimized" not in args:
        dlg = LanguageDialog()
        dlg.setWindowIcon(QIcon(resource(os.path.join("assets", "jdm.ico"))))
        dlg.exec()
        settings["language"] = dlg.choice
        save_settings(settings)
    set_language(settings.get("language") or "en")
    if is_rtl():
        app.setLayoutDirection(Qt.RightToLeft)
    settings["ffmpeg_path"] = find_tool("ffmpeg")
    settings["deno_path"] = find_tool("deno")
    w = MainWindow(settings, start_hidden="--minimized" in args)
    if url:
        QTimer.singleShot(300, lambda: w.add_dialog(url))
    elif not settings.get("_ext_hint_shown") and "--minimized" not in args:
        settings["_ext_hint_shown"] = True
        save_settings(settings)
        QTimer.singleShot(600, w.extension_help)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
