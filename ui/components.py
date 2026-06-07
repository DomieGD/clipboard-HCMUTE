"""
File này định nghĩa các thành phần UI nhỏ lẻ dùng trong danh sách clipboard,
bao gồm nhãn bấm được (ClickableLabel) và thẻ hiển thị thông tin clipboard (ClipboardCard).
"""
import os
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDialog, QScrollArea, QWidget,
                             QMessageBox)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QIcon, QGuiApplication, QPalette

# Xác định đường dẫn tương đối tới thư mục icon
_dir = os.path.dirname(os.path.abspath(__file__))
iconEye       = os.path.join(_dir, "icons", "icon_eye.svg")
iconPin       = os.path.join(_dir, "icons", "icon_pin.svg")
iconPinAct   = os.path.join(_dir, "icons", "icon_pin_active.svg")
iconTrash     = os.path.join(_dir, "icons", "icon_trash.svg")

# Thiết lập kích thước icon và giới hạn hiển thị ký tự xem trước
iconSize      = QSize(16, 16)
btnSize       = 30
maxPreviewChars = 200


def _IconBtn(iconPath: str, tooltip: str, objectName: str) -> QPushButton:
    # Tạo một QPushButton dạng ô vuông chỉ có icon lấy từ file SVG.
    btn = QPushButton()
    btn.setIcon(QIcon(iconPath))
    btn.setIconSize(iconSize)
    btn.setToolTip(tooltip)
    btn.setObjectName(objectName)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedSize(btnSize, btnSize)
    btn.setText("")
    return btn


class ClickableLabel(QLabel):
    # Nhãn hiển thị hình ảnh có khả năng nhận diện sự kiện click chuột trái để phóng to ảnh.
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def mousePressEvent(self, event):
        # Kiểm tra sự kiện nhấp chuột trái
        if event.button() == Qt.MouseButton.LeftButton:
            self._callback()
        super().mousePressEvent(event)


class ClipboardCard(QFrame):
    # Thẻ hiển thị thông tin của từng bản ghi clipboard (Văn bản hoặc hình ảnh).
    def __init__(self, itemId, itemType, content, timestamp, isPinned,
                 onPinCallback, onCopyCallback, onDeleteCallback):
        super().__init__()
        self.itemId = itemId
        self.itemType = itemType
        self.content = content
        self.isPinned = isPinned
        self.onPinCallback = onPinCallback
        self.onCopyCallback = onCopyCallback
        self.onDeleteCallback = onDeleteCallback

        self.setObjectName("ClipboardCard")
        self.InitUi(timestamp)

    def InitUi(self, timestamp):
        # Layout chính của thẻ chứa nội dung hiển thị dạng dọc
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)

        # --- Dòng thông tin meta (Thời gian và các nút ghim/xóa/xem đầy đủ) ---
        metaLayout = QHBoxLayout()
        metaLayout.setSpacing(6)

        lblTime = QLabel(f"⏱ {timestamp}")
        lblTime.setObjectName("lbl_time")
        metaLayout.addWidget(lblTime)
        metaLayout.addStretch()

        # Nút xem chi tiết nội dung đầy đủ
        btnView = _IconBtn(iconEye, "Xem đầy đủ", "btn_view")
        btnView.clicked.connect(self.ShowFullPopup)
        metaLayout.addWidget(btnView)

        # Nút ghim/bỏ ghim bản ghi
        pinIcon = iconPinAct if self.isPinned else iconPin
        pinTip  = "Bỏ ghim" if self.isPinned else "Ghim"
        self.btnPin = _IconBtn(pinIcon, pinTip, "btn_pin")
        self.btnPin.setProperty("pinned", "true" if self.isPinned else "false")
        self.btnPin.clicked.connect(lambda: self.onPinCallback(self.itemId, self.isPinned))
        metaLayout.addWidget(self.btnPin)

        # Nút xóa bản ghi khỏi danh sách lưu trữ
        btnDelete = _IconBtn(iconTrash, "Xóa", "btn_delete")
        btnDelete.clicked.connect(self.DeleteClicked)
        metaLayout.addWidget(btnDelete)

        layout.addLayout(metaLayout)

        # --- Hiển thị nội dung bản ghi dựa vào kiểu dữ liệu ---
        if self.itemType == "text":
            # Xử lý hiển thị nội dung văn bản (Giới hạn tối đa số ký tự xem trước)
            textStr = self.content.decode('utf-8')
            preview = textStr[:maxPreviewChars] + ("..." if len(textStr) > maxPreviewChars else "")
            lblContent = QLabel(preview)
            lblContent.setObjectName("lbl_content")
            lblContent.setWordWrap(True)
            lblContent.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(lblContent)
        else:
            # Xử lý hiển thị ảnh thu nhỏ trong thẻ
            pixmap = QPixmap()
            pixmap.loadFromData(self.content)
            lblImage = ClickableLabel(self.ShowFullPopup)
            lblImage.setPixmap(pixmap.scaledToWidth(380, Qt.TransformationMode.SmoothTransformation))
            lblImage.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lblImage.setStyleSheet("border-radius: 8px;")
            lblImage.setCursor(Qt.CursorShape.PointingHandCursor)
            lblImage.setToolTip("Nhấn để xem")
            layout.addWidget(lblImage)

        # --- Nút sao chép lại nội dung vào clipboard ---
        self.btnCopy = QPushButton("Sao chép")
        self.btnCopy.setObjectName("btn_copy")
        self.btnCopy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnCopy.setFixedHeight(36)
        self.btnCopy.clicked.connect(self.CopyClicked)
        layout.addWidget(self.btnCopy)

    # ── copy ──────────────────────────────────────────────
    def CopyClicked(self):
        # Thực hiện gọi callback để copy dữ liệu vào hệ thống và đổi trạng thái nút
        self.onCopyCallback(self.itemType, self.content)
        self.btnCopy.setText("✓  Đã sao chép")
        self.btnCopy.setStyleSheet("""
            background-color: #34A853;
            color: white;
            font-weight: bold;
        """)
        # Đặt lịch chuyển nút về trạng thái ban đầu sau 1.5 giây
        QTimer.singleShot(1500, self.ResetCopyButton)

    def ResetCopyButton(self):
        # Đặt lại text và style cho nút sao chép về mặc định
        self.btnCopy.setText("Sao chép")
        self.btnCopy.setStyleSheet("")

    # ── delete ──────────────────────────────────────────────
    def DeleteClicked(self):
        # Cảnh báo xác nhận nếu người dùng cố gắng xóa một mục đang được ghim
        if self.isPinned:
            # Kiểm tra chế độ tối/sáng của ứng dụng
            isDark = True
            mainWindow = self.window()
            if mainWindow and hasattr(mainWindow, "comboTheme"):
                themeChoice = mainWindow.comboTheme.currentText().lower()
                if themeChoice == "theo hệ thống":
                    isDark = mainWindow.IsSystemDarkMode()
                else:
                    isDark = (themeChoice == "chế độ tối")
            else:
                palette = QGuiApplication.palette()
                bgColor = palette.color(QPalette.ColorRole.Window)
                isDark = bgColor.value() < 128

            box = QMessageBox(self)
            box.setWindowTitle("Xác nhận")
            box.setText("Mục này đang được <b>ghim</b>. Bạn có chắc muốn xóa không?")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            box.setDefaultButton(QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("Xóa")
            box.button(QMessageBox.StandardButton.No).setText("Hủy")
            
            if isDark:
                box.setStyleSheet("""
                    QMessageBox {
                        background-color: #1E1E1E;
                        color: #E0E0E0;
                    }
                    QLabel {
                        color: #E0E0E0;
                        font-size: 13px;
                    }
                    QPushButton {
                        padding: 6px 20px;
                        border-radius: 6px;
                        font-weight: 600;
                        border: 1px solid #3D3D3D;
                        background-color: #2D2D2D;
                        color: #E0E0E0;
                    }
                    QPushButton:hover { background-color: #3D3D3D; }
                    QPushButton[text="Xác nhận"] {
                        background-color: #C0392B;
                        border-color: #C0392B;
                        color: white;
                    }
                    QPushButton[text="Xác nhận"]:hover { background-color: #EA4335; }
                    QPushButton[text="Hủy"] {
                        background-color: #2D2D2D;
                        border: 1px solid #3D3D3D;
                        color: #E0E0E0;
                    }
                    QPushButton[text="Hủy"]:hover { background-color: #3D3D3D; }
                """)
            else:
                box.setStyleSheet("""
                    QMessageBox {
                        background-color: #F8F9FA;
                        color: #202124;
                    }
                    QLabel {
                        color: #202124;
                        font-size: 13px;
                    }
                    QPushButton {
                        padding: 6px 20px;
                        border-radius: 6px;
                        font-weight: 600;
                        border: 1px solid #DADCE0;
                        background-color: #FFFFFF;
                        color: #3C4043;
                    }
                    QPushButton:hover { background-color: #F1F3F4; }
                    QPushButton[text="Xác nhận"] {
                        background-color: #D93025;
                        border-color: #D93025;
                        color: white;
                    }
                    QPushButton[text="Xác nhận"]:hover { background-color: #EA4335; }
                    QPushButton[text="Hủy"] {
                        background-color: #FFFFFF;
                        border: 1px solid #DADCE0;
                        color: #3C4043;
                    }
                    QPushButton[text="Hủy"]:hover { background-color: #F1F3F4; }
                """)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return
        self.onDeleteCallback(self.itemId)

    # ── popup ──────────────────────────────────────────────
    def ShowFullPopup(self):
        # Hiển thị cửa sổ phụ phóng to nội dung văn bản hoặc hình ảnh gốc
        # Kiểm tra chế độ tối/sáng của ứng dụng
        isDark = True
        mainWindow = self.window()
        if mainWindow and hasattr(mainWindow, "comboTheme"):
            themeChoice = mainWindow.comboTheme.currentText().lower()
            if themeChoice == "theo hệ thống":
                isDark = mainWindow.IsSystemDarkMode()
            else:
                isDark = (themeChoice == "chế độ tối")
        else:
            palette = QGuiApplication.palette()
            bgColor = palette.color(QPalette.ColorRole.Window)
            isDark = bgColor.value() < 128

        dialog = QDialog(self)
        dialog.setWindowFlags(
            dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        dialog.setMinimumWidth(500)
        
        if isDark:
            dialog.setStyleSheet("""
                QDialog       { background-color: #1A1A2E; }
                QLabel        { color: #E0E0E0; font-size: 14px; border: none; }
                QScrollArea   { border: none; background: transparent; }
                QWidget#inner { background: transparent; }
            """)
        else:
            dialog.setStyleSheet("""
                QDialog       { background-color: #FFFFFF; }
                QLabel        { color: #202124; font-size: 14px; border: none; }
                QScrollArea   { border: none; background: transparent; }
                QWidget#inner { background: transparent; }
            """)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        if self.itemType == "text":
            # Đọc toàn bộ văn bản và hiển thị trong vùng có thanh cuộn
            dialog.setWindowTitle("Nội Dung Đầy Đủ")
            textStr = self.content.decode('utf-8')

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            inner = QWidget()
            inner.setObjectName("inner")
            innerLay = QVBoxLayout(inner)
            innerLay.setContentsMargins(8, 8, 8, 8)

            lbl = QLabel(textStr)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            innerLay.addWidget(lbl)
            innerLay.addStretch()
            scroll.setWidget(inner)
            outer.addWidget(scroll)
            dialog.resize(540, 420)

        else:
            # Hiển thị hình ảnh gốc lớn với chế độ giữ tỉ lệ khung hình
            dialog.setWindowTitle("Xem hình ảnh")
            pixmap = QPixmap()
            pixmap.loadFromData(self.content)
            scaled = pixmap.scaled(
                1000, 800,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lblImg = QLabel()
            lblImg.setPixmap(scaled)
            lblImg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer.addWidget(lblImg)
            dialog.adjustSize()

        dialog.exec()
