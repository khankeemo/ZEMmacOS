from PySide6 import QtCore, QtGui, QtWidgets
import sys
import threading
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from backend_manager import BackendManager
from api_monitor import APIMonitor
from admin_api_client import (
    AdminAPIClient,
    resolve_admin_key,
    load_api_config,
    set_api_log_callback,
)
from license_generator import LicenseGenerator

QT_STYLE = """
QWidget { background: #161616; color: #F5F5F7; font-family: 'Segoe UI', 'Helvetica Neue', Arial; }
#sidebar { background: #1C1C1E; }
.card { background: rgba(255,255,255,0.04); border-radius: 14px; padding: 12px; }
.title { color: #F5F5F7; font-weight: 600; }
.value { color: #0A84FF; font-size: 22px; font-weight: 700; }
QPushButton { background: transparent; border: none; color: #F5F5F7; }
QPushButton:hover { color: #0A84FF; }
"""


class SplashScreen(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.resize(560, 260)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        card = QtWidgets.QFrame()
        card.setObjectName("card")
        card.setStyleSheet("background: rgba(20,20,20,0.6); border-radius:12px;")
        inner = QtWidgets.QVBoxLayout(card)
        title = QtWidgets.QLabel("ZEMmacOS — Starting License Services...")
        title.setStyleSheet("color: #F5F5F7; font-size:18px; font-weight:700;")
        inner.addWidget(title)
        self.progress = QtWidgets.QLabel("Checking backend...")
        inner.addWidget(self.progress)
        layout.addWidget(card)

    def set_message(self, msg: str):
        self.progress.setText(msg)


class DashboardWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZEMmacOS License Admin — Dashboard")
        self.resize(1200, 800)
        self.setStyleSheet(QT_STYLE)

        cfg = load_api_config()
        self.api_url = cfg.get("license_api_url", "http://localhost:8000")
        self.backend = BackendManager(self.api_url, log_callback=self._log)
        self.api_monitor = APIMonitor(
            self.api_url, interval=8, callback=self._on_api_update
        )

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)

        # Sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sv = QtWidgets.QVBoxLayout(sidebar)
        sv.setContentsMargins(12, 12, 12, 12)
        logo = QtWidgets.QLabel("ZEMmacOS")
        logo.setStyleSheet("font-size:18px; font-weight:700; color:#F5F5F7")
        sv.addWidget(logo)
        sv.addSpacing(8)
        for name in [
            "Dashboard",
            "Generate",
            "Validate",
            "Customers",
            "Hardware",
            "Activations",
            "Logs",
            "Monitoring",
            "Settings",
        ]:
            b = QtWidgets.QPushButton(name)
            b.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            sv.addWidget(b)
        sv.addStretch()

        # Main area
        main_area = QtWidgets.QWidget()
        mv = QtWidgets.QVBoxLayout(main_area)
        top_row = QtWidgets.QHBoxLayout()
        self.cards = {}
        for key, title in [
            ("total", "Total Licenses"),
            ("active", "Active Licenses"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ]:
            f = QtWidgets.QFrame()
            f.setProperty("class", "card")
            f.setMinimumHeight(100)
            lv = QtWidgets.QVBoxLayout(f)
            t = QtWidgets.QLabel(title)
            t.setProperty("class", "title")
            v = QtWidgets.QLabel("—")
            v.setProperty("class", "value")
            lv.addWidget(t)
            lv.addStretch()
            lv.addWidget(v)
            top_row.addWidget(f)
            self.cards[key] = v
        mv.addLayout(top_row)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        mv.addWidget(self.log_view)

        h.addWidget(sidebar)
        h.addWidget(main_area, stretch=1)

        self._startup()

    def _log(self, msg, level="info"):
        ts = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] [{level.upper()}] {msg}")

    def _startup(self):
        splash = SplashScreen()
        splash.show()

        def work():
            splash.set_message("Ensuring backend...")
            ok = self.backend.ensure_backend_running()
            splash.set_message("Connecting to API...")
            key = resolve_admin_key()
            self.api = AdminAPIClient(admin_key=key)
            health = self.api.health_check()
            self._apply_health(health)
            # start live monitoring
            try:
                self.api_monitor.start()
            except Exception:
                pass
            time.sleep(0.5)
            splash.close()

        threading.Thread(target=work, daemon=True).start()

    def _apply_health(self, health: dict):
        stats = {}
        try:
            stats = self.api.get_dashboard_stats()
        except Exception:
            pass
        self.cards.get("total").setText(str(stats.get("total_licenses", "—")))
        self.cards.get("active").setText(str(stats.get("active_licenses", "—")))
        self.cards.get("expired").setText(str(stats.get("expired_licenses", "—")))
        self.cards.get("revoked").setText(str(stats.get("revoked_licenses", "—")))

    def _on_api_update(self, status: dict):
        # called from monitor thread — schedule to GUI thread
        QtCore.QMetaObject.invokeMethod(
            self,
            "_apply_api_status",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(object, status),
        )

    @QtCore.Slot(object)
    def _apply_api_status(self, status: dict):
        if status.get("online"):
            msg = f"API online • {status.get('latency_ms')}ms"
            self._log(msg, "success")
        else:
            self._log(f"API offline ({status.get('error')})", "warning")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = DashboardWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
