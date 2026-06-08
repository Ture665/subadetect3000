import socket
import sys
import threading
import pyautogui
import subprocess
import json
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFrame, 
    QLineEdit, QSpinBox, QComboBox, QFileDialog, QStackedWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

CONFIG_FILE = "suba_detector_config.json"

DEFAULT_CONFIG = {
    "host": "192.168.1.100",
    "port": 5000,
    "action": "Alt + Tab",
    "selected_app_path": "",
    "window_geometry": None
}

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
        
        return {**DEFAULT_CONFIG, **config}
    
    except Exception:
        return DEFAULT_CONFIG.copy()
    
def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

class SignalBridge(QObject):
    log_signal    = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    suba_detected = pyqtSignal()
    disconnected_signal = pyqtSignal()


bridge = SignalBridge()


class SocketClient(threading.Thread):
    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host = host
        self.port = port

        self._stop_event = threading.Event()

    def run(self):
        try:
            bridge.status_signal.emit("Connecting to Pi...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                bridge.log_signal.emit(f"> Connected to Pi at {self.host}:{self.port}")
                bridge.status_signal.emit(f"Connected to: {self.host}")
                s.settimeout(1.0)

                while not self._stop_event.is_set():
                    try:
                        data = s.recv(1024)
                        if not data:
                            bridge.log_signal.emit("> Pi disconnected.")
                            break
                        message = data.decode("utf-8").strip()
                        #bridge.log_signal.emit(f"> Received: {message}")

                        if message == "SUBA_DETECTED":
                            bridge.suba_detected.emit()
                        elif message == "UNKNOWN_DETECTED":
                            bridge.log_signal.emit("> Unknown face — no action.")
                        else: 
                            try: 
                                event = json.loads(message)

                                if event.get("type") == "face_detected":
                                    name = event.get("name", "Unknown")
                                    action = event.get("action", "none")

                                    #bridge.log_signal.emit(f"> Face detected: {name}")

                                    if action == "suba_detected":
                                        bridge.suba_detected.emit()

                            except json.JSONDecodeError:
                                bridge.log_signal.emit("> Unknown message format.")

                    except socket.timeout:
                        continue

        except Exception as e:
            bridge.log_signal.emit(f"> Connection error: {e}")
            bridge.status_signal.emit("Failed to connect — check Pi IP")

        finally:
            bridge.disconnected_signal.emit()

    def stop(self):
        self._stop_event.set()


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.client_thread = None
        self.auto_tab = False
        self.drag_position = None
        self.resizing = False
        self.resize_margin = 12
        self.resize_direction = None
        self.config = load_config()
        self.selected_app_path = self.config["selected_app_path"]
        self.logged_in_user = ""
        self.last_action_time = 0
        self.action_cooldown = 3
        self._build_ui()
        self._connect_signals()

    def open_main(self):
        self.stack.setCurrentIndex(0)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")

    def open_settings(self):
        self.stack.setCurrentIndex(1)

    def save_current_settings(self):
        self.config["host"] = self.host_input.text()
        self.config["port"] = self.port_input.value()
        self.config["action"] = self.action_dropdown.currentText()
        self.config["selected_app_path"] = self.selected_app_path
        save_config(self.config)

        self._log("> Settings saved.")
        self.open_main()

    def open_account(self):
        self.stack.setCurrentIndex(2)

    def login_account(self):
        username = self.username_input.text().strip()

        if not username:
            self.account_status_label.setText("Status: Missing username")
            return

        self.logged_in_user = username
        self.account_status_label.setText(f"Status: Logged in as {username}")
        self.login_logout_btn.setText("Logout")
        self._log(f"> Logged in as {username}")
        self.open_main()


    def restore_window_geometry(self):
        geometry = self.config.get("window_geometry")

        if geometry:
            self.setGeometry(
                geometry.get("x", 200),
                geometry.get("y", 200),
                geometry.get("width", 560),
                geometry.get("height", 480)
            )
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            width = 560
            height = 480
            x = screen.x() + (screen.width() - width) // 2
            y = screen.y() + (screen.height() - height) // 2
            self.setGeometry(x, y, width, height)

    def logout_account(self):
        self.logged_in_user = ""
        self.account_status_label.setText("Status: Not logged in")
        self.login_logout_btn.setText("Login")
        self.username_input.clear()
        self.password_input.clear()
        self._log("> Logged out.")
        self.open_main()

    def handle_login_logout(self):
        if self.logged_in_user:
            self.logout_account()
        else:
            self.login_account()
    
    def _on_disconnected(self):
        self.server_btn.setText("▶  Connect to Pi")
        self.server_btn.setChecked(False)
        self.client_thread = None
    
    def _build_ui(self):
        self.setWindowTitle("Subaharan Detector 3000")
        self.setWindowIcon(QIcon(resource_path("icons/suba.ico")))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.restore_window_geometry()
        self.setMinimumSize(520, 380)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QWidget {
                background-color: #0d0d0d;
                color: #e0e0e0;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QPushButton {
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QPushButton#start_btn {
                background-color: #1a3a1a;
                color: #4cff4c;
                border-color: #4cff4c;
            }
            QPushButton#start_btn:checked {
                background-color: #3a1a1a;
                color: #ff5555;
                border-color: #ff5555;
            }
            QPushButton#auto_btn {
                background-color: #1a1a2e;
                color: #888;
                border-color: #333;
            }
            QPushButton#auto_btn:checked {
                background-color: #1a2e1a;
                color: #4cff4c;
                border-color: #4cff4c;
            }
            QLabel#status_label {
                color: #888;
                font-size: 12px;
                padding: 4px 0;
            }
            QLabel#title_label {
                color: #4cff4c;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 2px;
                padding: 8px 0 4px 0;
            }
            QFrame#divider {
                background-color: #222;
            }
            QTextEdit {
                background-color: #060606;
                color: #4cff4c;
                border: 1px solid #1e1e1e;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 6px;
            }

            QPushButton#top_icon_btn {
                background-color: transparent;
                border: none;
                padding: 0px;
            }

            QPushButton#top_icon_btn:hover {
                background-color: #1a1a1a;
                border-radius: 4px;
            }

            QPushButton#top_icon_btn:pressed {
                background-color: #222222;
                border-radius: 4px;
            }

            QFrame#custom_title_bar {
                background-color: #060606;
                border-bottom: 1px solid #222;
            }

            QPushButton#window_btn {
                background-color: transparent;
                border: none;
                color: #4cff4c;
                padding: 0px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton#window_btn:hover {
                background-color: #1a1a1a;
            }

            QPushButton#close_btn {
                background-color: transparent;
                border: none;
                color: #ff5555;
                padding: 0px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton#close_btn:hover {
                background-color: #3a1a1a;
            }

            QLabel#window_title_label {
            background-color: transparent;
            border: none;
            color: #4cff4c;
            font-size: 12px;
            font-weight: normal;
            letter-spacing: 1px;
            padding: 0px;
}
        """)

        main_root = QVBoxLayout(self)
        main_root.setContentsMargins(0, 0, 0, 0)
        main_root.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setObjectName("custom_title_bar")
        self.title_bar.setFixedHeight(36)

        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(12, 0, 6, 0)
        title_bar_layout.setSpacing(4)

        title_bar_label = QLabel("Subaharan Detector 3000")
        title_bar_label.setObjectName("window_title_label")
        title_bar_layout.addWidget(title_bar_label)

        title_bar_layout.addStretch()

        self.minimize_btn = QPushButton("–")
        self.minimize_btn.setObjectName("window_btn")
        self.minimize_btn.setFixedSize(34, 28)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(self.minimize_btn)

        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setObjectName("window_btn")
        self.maximize_btn.setFixedSize(34, 28)
        self.maximize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        title_bar_layout.addWidget(self.maximize_btn)

        self.close_btn = QPushButton("X")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.setFixedSize(34, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(self.close_btn)

        main_root.addWidget(self.title_bar)

        content_widget = QWidget()
        content_widget.setMouseTracking(True)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        main_root.addWidget(content_widget)

        self.setMouseTracking(True)

        self.main_page = QWidget()
        self.settings_page = QWidget()
        self.account_page = QWidget()

        self.main_page.setMouseTracking(True)
        self.settings_page.setMouseTracking(True)
        self.account_page.setMouseTracking(True)

        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.account_page)

        main_root = QVBoxLayout(self.main_page)
        main_root.setSpacing(8)

        settings_root = QVBoxLayout(self.settings_page)
        settings_root.setSpacing(8)

        account_root = QVBoxLayout(self.account_page)
        account_root.setSpacing(8)

        top_row = QHBoxLayout()

        title = QLabel("◈ SUBA DETECTOR 3000")
        title.setObjectName("title_label")
        top_row.addWidget(title)

        top_row.addStretch()

        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("top_icon_btn")
        self.settings_btn.setIcon(QIcon(resource_path("icons/settings.svg")))
        self.settings_btn.setIconSize(QSize(18, 18))
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        top_row.addWidget(self.settings_btn)

        self.account_btn = QPushButton()
        self.account_btn.setObjectName("top_icon_btn")
        self.account_btn.setIcon(QIcon(resource_path("icons/account.svg")))
        self.account_btn.setIconSize(QSize(18, 18))
        self.account_btn.setFixedSize(32, 32)
        self.account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.account_btn.clicked.connect(self.open_account)
        top_row.addWidget(self.account_btn)

        main_root.addLayout(top_row)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        main_root.addWidget(div)

        btn_row = QHBoxLayout()

        self.server_btn = QPushButton("▶  Connect to Pi")
        self.server_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.server_btn.setObjectName("start_btn")
        self.server_btn.setCheckable(True)
        self.server_btn.clicked.connect(self.toggle_server)
        btn_row.addWidget(self.server_btn)

        self.auto_btn = QPushButton("⇥  Auto Action: OFF")
        self.auto_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auto_btn.setObjectName("auto_btn")
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(self.toggle_auto_tab)
        btn_row.addWidget(self.auto_btn)

        main_root.addLayout(btn_row)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("status_label")
        main_root.addWidget(self.status_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_root.addWidget(self.log)

        self._log("> Suba Detector ready. Connect to Pi to begin.")

        settings_title = QLabel("◈ SETTINGS")
        settings_title.setObjectName("title_label")
        settings_root.addWidget(settings_title)

        settings_div = QFrame()
        settings_div.setObjectName("divider")
        settings_div.setFixedHeight(1)
        settings_root.addWidget(settings_div)

        ip_row = QHBoxLayout()

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Rasberry Pi IP")
        self.host_input.setText(self.config["host"])

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(self.config["port"])

        ip_row.addWidget(QLabel("IP:"))
        ip_row.addWidget(self.host_input)

        ip_row.addWidget(QLabel("Port:"))
        ip_row.addWidget(self.port_input)

        settings_root.addLayout(ip_row)

        action_row = QHBoxLayout()

        action_label = QLabel("Action:")

        self.action_dropdown = QComboBox()

        self.action_dropdown.addItems([
            "Alt + Tab",
            "Ctrl + Tab",
            "Win + D",
            "Open selected app",
            "Do nothing"
        ])

        saved_action = self.config["action"]
        index = self.action_dropdown.findText(saved_action)

        if index >= 0:
            self.action_dropdown.setCurrentIndex(index)

        self.choose_app_btn = QPushButton("⋯")
        self.choose_app_btn.setFixedWidth(30)
        self.choose_app_btn.setFixedHeight(22)
        self.choose_app_btn.setStyleSheet("""
            QPushButton {
                padding: 4px;
                font-size: 18px;
            }
        """)
        self.choose_app_btn.clicked.connect(self.choose_app)
        self.choose_app_btn.hide()

        self.action_dropdown.currentTextChanged.connect(self.update_choose_app_visibility)

        action_row.addWidget(action_label)
        action_row.addWidget(self.action_dropdown)
        action_row.addWidget(self.choose_app_btn)

        settings_root.addLayout(action_row)

        settings_btn_row = QHBoxLayout()

        back_btn = QPushButton("← Back")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.open_main)
        settings_btn_row.addWidget(back_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_current_settings)
        settings_btn_row.addWidget(save_btn)

        settings_root.addLayout(settings_btn_row)
        settings_root.addStretch()

        account_title = QLabel("◈ ACCOUNT")
        account_title.setObjectName("title_label")
        account_root.addWidget(account_title)

        account_div = QFrame()
        account_div.setObjectName("divider")
        account_div.setFixedHeight(1)
        account_root.addWidget(account_div)

        self.account_status_label = QLabel("Status: Not logged in")
        self.account_status_label.setObjectName("status_label")
        account_root.addWidget(self.account_status_label)

        username_row = QHBoxLayout()
        username_row.addWidget(QLabel("Username:"))

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        username_row.addWidget(self.username_input)

        account_root.addLayout(username_row)

        password_row = QHBoxLayout()
        password_row.addWidget(QLabel("Password:"))

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_row.addWidget(self.password_input)

        account_root.addLayout(password_row)

        self.remember_login_checkbox = QCheckBox("Remember me")
        self.remember_login_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        account_root.addWidget(self.remember_login_checkbox)

        account_btn_row = QHBoxLayout()

        account_back_btn = QPushButton("← Back")
        account_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        account_back_btn.clicked.connect(self.open_main)
        account_btn_row.addWidget(account_back_btn)

        self.login_logout_btn = QPushButton("Login")
        self.login_logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_logout_btn.clicked.connect(self.handle_login_logout)
        account_btn_row.addWidget(self.login_logout_btn)

        account_root.addLayout(account_btn_row)
        account_root.addStretch()

    def _connect_signals(self):
        bridge.log_signal.connect(self._log)
        bridge.status_signal.connect(lambda s: self.status_label.setText(f"Status: {s}"))
        bridge.disconnected_signal.connect(self._on_disconnected)
        bridge.suba_detected.connect(self._on_suba_detected)

    def toggle_server(self, checked):
        if checked:
            self.server_btn.setText("■  Disconnect")
            self.status_label.setText("Status: Connecting...")

            host = self.host_input.text()
            port = self.port_input.value()

            self.config["host"] = host
            self.config["port"] = port
            self.config["action"] = self.action_dropdown.currentText()
            self.config["selected_app_path"] = self.selected_app_path
            save_config(self.config)

            self.client_thread = SocketClient(host, port)

            self.client_thread.start()
        else:
            self.server_btn.setText("▶  Connect to Pi")
            self.status_label.setText("Status: Idle")
            self._log("> Disconnected.")
            if self.client_thread:
                self.client_thread.stop()
                self.client_thread = None

    def toggle_auto_tab(self, checked):
        self.auto_tab = checked
        if checked:
            self.auto_btn.setText("⇥  Auto Action: ON")
            self._log("> Auto Action ENABLED.")
        else:
            self.auto_btn.setText("⇥  Auto Action: OFF")
            self._log("> Auto Action DISABLED.")

    def choose_app(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose app",
            "",
            "Programs (*.exe);;All files (*.*)"
        )
        if path:
            self.selected_app_path = path
            self.config["selected_app_path"] = path
            save_config(self.config)
            self._log(f"> Selected app {path}")

    def update_choose_app_visibility(self, action):
        if action == "Open selected app":
            self.choose_app_btn.show()
        else:
            self.choose_app_btn.hide()

    def _on_suba_detected(self):
        self._log(">>> SUBA DETECTED! <<<")
        current_time = time.time()

        if current_time - self.last_action_time < self.action_cooldown:
            self._log("> Action ignored because cooldown is active.")
            return
        
        self.last_action_time = current_time

        if self.auto_tab:
            self._log("> Triggering Alt+Tab ...")
            action = self.action_dropdown.currentText()

            if action == "Alt + Tab":
                pyautogui.hotkey("alt", "tab")
            elif action == "Ctrl + Tab":
                pyautogui.hotkey("ctrl", "tab")
            elif action == "Win + D":
                pyautogui.hotkey("win", "d")
            elif action == "Open selected app":
                if self.selected_app_path:
                    self._log(f"> Opening app: {self.selected_app_path}")
                    subprocess.Popen(self.selected_app_path)
                else: 
                    self._log("> No app selected")
            elif action == "Do nothing":
                self._log("> No action selected.")


        else:
            self._log("> Auto Action is OFF — no action.")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")

    def closeEvent(self, event):
        if self.client_thread:
            self.client_thread.stop()
        self.config["host"] = self.host_input.text()
        self.config["port"] = self.port_input.value()
        self.config["action"] = self.action_dropdown.currentText()
        self.config["selected_app_path"] = self.selected_app_path

        geometry = self.geometry()
        self.config["window_geometry"] = {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height()
        }
        save_config(self.config)

        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self.resize_direction = self.get_resize_direction(pos)

            if self.resize_direction:
                self.resizing = True
                self.drag_position = event.globalPosition().toPoint()
                self.start_geometry = self.geometry()
                event.accept()
                return

            if self.title_bar.geometry().contains(pos):
                self.drag_position = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
                event.accept()

    def update_resize_cursor(self, pos):
        direction = self.get_resize_direction(pos)

        if direction in ["left", "right"]:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif direction in ["top", "bottom"]:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif direction in ["top_left", "bottom_right"]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif direction in ["top_right", "bottom_left"]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if not self.resizing:
            self.update_resize_cursor(pos)

        if self.resizing and self.resize_direction:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.drag_position
            geom = self.start_geometry

            x = geom.x()
            y = geom.y()
            w = geom.width()
            h = geom.height()

            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            if "right" in self.resize_direction:
                w = max(min_w, geom.width() + delta.x())

            if "bottom" in self.resize_direction:
                h = max(min_h, geom.height() + delta.y())

            if "left" in self.resize_direction:
                new_w = max(min_w, geom.width() - delta.x())
                x = geom.x() + (geom.width() - new_w)
                w = new_w

            if "top" in self.resize_direction:
                new_h = max(min_h, geom.height() - delta.y())
                y = geom.y() + (geom.height() - new_h)
                h = new_h

            self.setGeometry(x, y, w, h)
            event.accept()
            return

        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.resizing = False
        self.resize_direction = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def get_resize_direction(self, pos):
        if hasattr(self, "title_bar") and self.title_bar.geometry().contains(pos):
            return None

        x = pos.x()
        y = pos.y()
        w = self.width()
        h = self.height()
        m = self.resize_margin

        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m

        if top and left:
            return "top_left"
        if top and right:
            return "top_right"
        if bottom and left:
            return "bottom_left"
        if bottom and right:
            return "bottom_right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"

        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec())