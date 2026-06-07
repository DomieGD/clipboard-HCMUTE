from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QComboBox, QLabel, QScrollArea,
                             QMessageBox, QApplication, QInputDialog,
                             QStyledItemDelegate, QStyle, QSystemTrayIcon, QMenu,
                             QSizePolicy, QGridLayout)
from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODevice, QTimer
from PyQt6.QtGui import QPixmap, QGuiApplication, QPalette, QColor, QAction, QIcon
from datetime import datetime
import os

from database.handler import DatabaseHandler
from database import manager as dbManager
from ui.components import ClipboardCard

_ADD_DB_LABEL = "＋  Thêm kho mới..."

# Thiết lập đường dẫn các file icon chuyên dụng
_uiDir = os.path.dirname(os.path.abspath(__file__))
_rootDir = os.path.dirname(_uiDir)
appIconPath = os.path.join(_rootDir, "ClipboardHCMUTE.ico")
mainWindowIconPath = os.path.join(_rootDir, "ClipboardHCMUTE.ico")


class _AddItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        combo = self.parent()
        if index.row() == combo.count() - 1:          # Kiểm tra nếu là mục cuối cùng (Thêm kho mới)
            option.palette.setColor(option.palette.ColorRole.Text, QColor("#34A853"))

    def paint(self, painter, option, index):
        combo = self.parent()
        if index.row() == combo.count() - 1:
            painter.save()
            isSelected = option.state & QStyle.StateFlag.State_Selected
            if isSelected:
                # Vẽ nền xanh đậm, chữ trắng khi di chuột qua mục cuối cùng
                painter.fillRect(option.rect, QColor("#34A853"))
                penColor = QColor("#FFFFFF")
            else:
                # Vẽ nền mặc định của ComboBox và tô màu chữ xanh lá cây
                combo.style().drawPrimitive(
                    QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, combo
                )
                penColor = QColor("#34A853")
            
            rect = option.rect.adjusted(8, 0, 0, 0)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(penColor)
            painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter, index.data())
            painter.restore()
        else:
            super().paint(painter, option, index)


class ClipboardManager(QMainWindow):
    # Cửa sổ chính của ứng dụng
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản Lý Sao Chép")
        self.setGeometry(100, 100, 480, 650)
        
        # Thiết lập biểu tượng cho cửa sổ chính
        if os.path.exists(mainWindowIconPath):
            self.setWindowIcon(QIcon(mainWindowIconPath))
        
        # Thiết lập cờ trạng thái theo dõi sao chép và bỏ qua trùng lặp
        self.isMonitoring = True
        self.ignoreNextChange = False
        
        # Tải cài đặt người dùng (Theme, sắp xếp, kho dữ liệu hiện tại)
        self._settings = dbManager.LoadSettings()
        
        # Khởi tạo Database từ cấu hình đã lưu
        dbName = self._settings.get("database")
        if not dbName or dbName not in dbManager.DisplayNames():
            dbName = dbManager.DisplayNames()[0]
        self._currentDbName = dbName
        self.db = DatabaseHandler(dbManager.FilenameFor(self._currentDbName))
        
        self.InitUI()
        
        # Lắng nghe sự kiện sao chép từ hệ thống
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.OnClipboardChange)
        
        # Thiết lập Khay hệ thống (System Tray), áp dụng Theme màu và tải danh sách bản ghi
        self.InitTray()
        self.ApplyTheme()
        self.RefreshList()
        
        # Hiển thị thông báo khi khởi động ứng dụng
        QTimer.singleShot(0, self.ShowStartupPopup)

    def InitUI(self):
        # Widget trung tâm và Layout chính dọc của cửa sổ chính
        mainWidget = QWidget()
        mainWidget.setObjectName("MainWindow")
        self.setCentralWidget(mainWidget)
        mainLayout = QVBoxLayout(mainWidget)
        
        # --- Thanh điều khiển 1: Trạng thái & Bộ lọc ---
        topLayout = QHBoxLayout()
        topLayout.setContentsMargins(0, 0, 0, 0)
        topLayout.setSpacing(10)
        
        # Nút bật/tắt theo dõi clipboard
        self.btnToggle = QPushButton("Đang Bật")
        self.btnToggle.setObjectName("btn_toggle")
        self.btnToggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnToggle.clicked.connect(self.ToggleMonitoring)
        self.btnToggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        topLayout.addWidget(self.btnToggle, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Nút thu nhỏ ứng dụng xuống khay hệ thống
        self.btnMinimize = QPushButton("Thu Nhỏ")
        self.btnMinimize.setObjectName("btn_minimize")
        self.btnMinimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnMinimize.clicked.connect(self.MinimizeToTray)
        self.btnMinimize.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        topLayout.addWidget(self.btnMinimize, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Nút làm mới (Xóa sạch lịch sử kho hiện tại)
        self.btnClear = QPushButton("Làm Mới")
        self.btnClear.setObjectName("btn_clear")
        self.btnClear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnClear.clicked.connect(self.ConfirmClearAll)
        self.btnClear.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        topLayout.addWidget(self.btnClear, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Nhãn và Dropdown sắp xếp/lọc dữ liệu
        lblSort = QLabel("Sắp xếp:")
        topLayout.addWidget(lblSort, 0, Qt.AlignmentFlag.AlignVCenter)
        
        self.comboSort = QComboBox()
        self.comboSort.addItems(["Mới Nhất", "Chỉ Văn Bản", "Chỉ Hình Ảnh"])
        self.comboSort.setCurrentText(self._settings.get("sort", "Mới Nhất"))
        self.comboSort.currentIndexChanged.connect(self.RefreshList)
        topLayout.addWidget(self.comboSort, 0, Qt.AlignmentFlag.AlignVCenter)
        mainLayout.addLayout(topLayout)
        
        # --- Thanh điều khiển 2: Chọn Database & ĐỔI THEME ---
        settingLayout = QHBoxLayout()
        settingLayout.setContentsMargins(0, 0, 0, 0)
        settingLayout.setSpacing(10)
        
        # Chọn Kho dữ liệu (Database)
        lblDb = QLabel("📂 Kho:")
        settingLayout.addWidget(lblDb, 0, Qt.AlignmentFlag.AlignVCenter)

        # Tạo Nhóm Kho, Rename, Remove liền kề nhau không khoảng cách (Input Group)
        dbGroupLayout = QHBoxLayout()
        dbGroupLayout.setSpacing(0)

        self.comboDb = QComboBox()
        self.comboDb.setObjectName("combo_db")
        self.comboDb.setItemDelegate(_AddItemDelegate(self.comboDb))
        self.ReloadComboDb()
        self.comboDb.activated.connect(self.OnComboDbActivated)
        dbGroupLayout.addWidget(self.comboDb)

        # Nút chỉnh sửa tên kho
        self.btnRenameDb = QPushButton()
        self.btnRenameDb.setObjectName("btn_rename_db")
        self.btnRenameDb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnRenameDb.setToolTip("Đổi Tên Kho")
        self.btnRenameDb.setIcon(QIcon("ui/icons/icon_edit.svg"))
        self.btnRenameDb.setFixedSize(30, 30)
        self.btnRenameDb.clicked.connect(self.ConfirmRenameDatabase)
        dbGroupLayout.addWidget(self.btnRenameDb)

        # Nút xóa kho dữ liệu
        self.btnRemoveDb = QPushButton()
        self.btnRemoveDb.setObjectName("btn_remove_db")
        self.btnRemoveDb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnRemoveDb.setToolTip("Xóa Kho Dữ Liệu")
        self.btnRemoveDb.setIcon(QIcon("ui/icons/icon_trash.svg"))
        self.btnRemoveDb.setFixedSize(30, 30)
        self.btnRemoveDb.clicked.connect(self.ConfirmRemoveDatabase)
        dbGroupLayout.addWidget(self.btnRemoveDb)

        dbGroupLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        settingLayout.addLayout(dbGroupLayout)

        settingLayout.addStretch(1)

        # Lựa chọn Giao diện (Theme)
        lblTheme = QLabel("🎨 Giao diện:")
        settingLayout.addWidget(lblTheme, 0, Qt.AlignmentFlag.AlignVCenter)

        self.comboTheme = QComboBox()
        self.comboTheme.addItems(["Theo Hệ Thống", "Chế Độ Sáng", "Chế Độ Tối"])
        self.comboTheme.setCurrentText(self._settings.get("theme", "Theo Hệ Thống"))
        self.comboTheme.currentIndexChanged.connect(self.ApplyTheme)
        settingLayout.addWidget(self.comboTheme, 0, Qt.AlignmentFlag.AlignVCenter)
        
        mainLayout.addLayout(settingLayout)
        
        # --- Khu vực hiển thị danh sách dạng cuộn (Scroll Area) ---
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scrollContent = QWidget()
        self.scrollContent.setObjectName("ScrollContent")
        self.scrollLayout = QVBoxLayout(self.scrollContent)
        self.scrollLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollLayout.setContentsMargins(10, 10, 10, 10)
        self.scrollLayout.setSpacing(12)
        self.scrollArea.setWidget(self.scrollContent)
        
        # Nhãn thông báo khi danh sách trống rỗng
        self.emptyLabel = QLabel("Sao chép để lưu")
        self.emptyLabel.setObjectName("empty_label")
        self.emptyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emptyLabel.setVisible(False)
        
        # Sử dụng QGridLayout xếp đè nhãn rỗng lên trên ScrollArea để tự động căn giữa tuyệt đối
        scrollContainer = QGridLayout()
        scrollContainer.setContentsMargins(0, 0, 0, 0)
        scrollContainer.addWidget(self.scrollArea, 0, 0)
        scrollContainer.addWidget(self.emptyLabel, 0, 0, Qt.AlignmentFlag.AlignCenter)
        
        mainLayout.addLayout(scrollContainer)

    # === TÍNH NĂNG ĐỔI THEME VÀ GRADIENT ===
    def IsSystemDarkMode(self):
        """Hàm kiểm tra xem Hệ điều hành máy tính đang cấu hình Dark Mode hay Light Mode."""
        palette = QGuiApplication.palette()
        bgColor = palette.color(QPalette.ColorRole.Window)
        return bgColor.value() < 128 # Độ sáng màu nền hệ thống < 128 tức là đang tối

    def ApplyTheme(self):
        # Áp dụng giao diện sáng/tối dựa theo cấu hình lựa chọn
        themeChoice = self.comboTheme.currentText().lower()
        
        if themeChoice == "theo hệ thống":
            dark = self.IsSystemDarkMode()
        else:
            dark = (themeChoice == "chế độ tối")
            
        if dark:
            # STYLE SHEET CHẾ ĐỘ TỐI
            styleSheet = """
                QMainWindow { background-color: #121212; }
                #MainWindow { background-color: #121212; }
                #ScrollContent { background-color: #121212; }
                
                QLabel { 
                    color: #E0E0E0; 
                    font-family: 'Segoe UI', 'Roboto', sans-serif; 
                }
                
                #empty_label {
                    color: #555555;
                    font-size: 18px;
                    font-weight: 600;
                }
                
                QComboBox {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    padding: 6px 28px 6px 12px;
                    min-width: 140px;
                    max-width: 140px;
                }
                QComboBox#combo_db {
                    border-top-right-radius: 0px;
                    border-bottom-right-radius: 0px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 25px;
                    border-left: none;
                }
                QComboBox::down-arrow {
                    image: url(ui/icons/down_arrow.svg);
                    width: 10px;
                    height: 6px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    selection-background-color: #0078D4;
                    border: 1px solid #333333;
                }
                
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                
                #ClipboardCard {
                    background-color: #1E1E1E;
                    border: 1px solid #2D2D2D;
                    border-radius: 12px;
                }
                #ClipboardCard:hover {
                    background-color: #252525;
                    border: 1px solid #3D3D3D;
                }
                
                #lbl_content { color: #FFFFFF; font-size: 14px; line-height: 1.4; }
                #lbl_time { color: #777777; font-size: 11px; }
                
                QPushButton#btn_copy { 
                    background-color: #0078D4; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 8px; 
                    font-weight: 600; 
                    border: none;
                }
                QPushButton#btn_copy:hover { background-color: #1084D8; }
                QPushButton#btn_copy:pressed { background-color: #005A9E; }
                
                QPushButton#btn_pin, QPushButton#btn_delete, QPushButton#btn_view { 
                    background-color: #2D2D2D; 
                    border-radius: 6px; 
                    padding: 4px;
                    border: 1px solid #3D3D3D;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
                QPushButton#btn_view:hover { background-color: #1A2A3A; border-color: #0078D4; }
                QPushButton#btn_pin:hover { background-color: #3A3500; border-color: #F1C40F; }
                QPushButton#btn_pin[pinned="true"] {
                    background-color: #4A3B00;
                    border-color: #F1C40F;
                }
                QPushButton#btn_pin[pinned="true"]:hover {
                    background-color: #5A4B00;
                }
                QPushButton#btn_delete:hover { background-color: #4D2D2D; border-color: #EA4335; }
                
                QPushButton#btn_minimize { 
                    background-color: transparent; 
                    color: #60A5FA; 
                    border-radius: 6px; 
                    padding: 6px 10px;
                    border: 2px solid #60A5FA;
                    font-weight: bold;
                }
                QPushButton#btn_minimize:hover { background-color: rgba(96, 165, 250, 0.15); }
                QPushButton#btn_minimize:pressed { background-color: rgba(96, 165, 250, 0.25); }
 
                QPushButton#btn_clear { 
                    background-color: transparent; 
                    color: #F87171; 
                    border-radius: 6px; 
                    padding: 6px 10px;
                    border: 2px solid #F87171;
                    font-weight: bold;
                }
                QPushButton#btn_clear:hover { background-color: rgba(248, 113, 113, 0.15); }
                QPushButton#btn_clear:pressed { background-color: rgba(248, 113, 113, 0.25); }
 
                QPushButton#btn_rename_db {
                    background-color: #2D2D2D;
                    border-radius: 0px;
                    border: 1px solid #3D3D3D;
                    border-left-color: transparent;
                }
                QPushButton#btn_rename_db:hover { background-color: #3A3500; border-color: #F1C40F; }
                
                QPushButton#btn_remove_db {
                    background-color: #2D2D2D;
                    border-radius: 0px;
                    border-top-right-radius: 6px;
                    border-bottom-right-radius: 6px;
                    border: 1px solid #3D3D3D;
                    border-left-color: transparent;
                }
                QPushButton#btn_remove_db:hover { background-color: #4D2D2D; border-color: #EA4335; }

                QDialog, QInputDialog, QMessageBox {
                    background-color: #1E1E1E;
                }
                QDialog QLabel, QInputDialog QLabel, QMessageBox QLabel {
                    color: #E0E0E0;
                }
                QDialog QPushButton, QInputDialog QPushButton, QMessageBox QPushButton {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #3D3D3D;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 600;
                }
                QDialog QPushButton:hover, QInputDialog QPushButton:hover, QMessageBox QPushButton:hover {
                    background-color: #3D3D3D;
                }
                QDialog QLineEdit, QInputDialog QLineEdit {
                    background-color: #121212;
                    color: #FFFFFF;
                    border: 1px solid #333333;
                    border-radius: 6px;
                    padding: 4px;
                }
            """
        else:
            # STYLE SHEET CHẾ ĐỘ SÁNG
            styleSheet = """
                QMainWindow { background-color: #F8F9FA; }
                #MainWindow { background-color: #F8F9FA; }
                #ScrollContent { background-color: #F8F9FA; }
                
                QLabel { 
                    color: #202124; 
                    font-family: 'Segoe UI', 'Roboto', sans-serif; 
                }
                
                #empty_label {
                    color: #BDC1C6;
                    font-size: 18px;
                    font-weight: 600;
                }
                
                QComboBox {
                    background-color: #FFFFFF;
                    color: #3C4043;
                    border: 1px solid #DADCE0;
                    border-radius: 6px;
                    padding: 6px 28px 6px 12px;
                    min-width: 140px;
                    max-width: 140px;
                }
                QComboBox#combo_db {
                    border-top-right-radius: 0px;
                    border-bottom-right-radius: 0px;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 25px;
                    border-left: none;
                }
                QComboBox::down-arrow {
                    image: url(ui/icons/down_arrow.svg);
                    width: 10px;
                    height: 6px;
                }
                QComboBox QAbstractItemView {
                    background-color: #FFFFFF;
                    color: #3C4043;
                    selection-background-color: #E8F0FE;
                    selection-color: #1967D2;
                    border: 1px solid #DADCE0;
                }
                
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                
                #ClipboardCard {
                    background-color: #FFFFFF;
                    border: 1px solid #DADCE0;
                    border-radius: 12px;
                }
                #ClipboardCard:hover {
                    background-color: #F1F3F4;
                    border: 1px solid #BDC1C6;
                }
                
                #lbl_content { color: #202124; font-size: 14px; line-height: 1.4; }
                #lbl_time { color: #70757A; font-size: 11px; }
                
                QPushButton#btn_copy { 
                    background-color: #1A73E8; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 8px; 
                    font-weight: 600; 
                    border: none;
                }
                QPushButton#btn_copy:hover { background-color: #1967D2; }
                QPushButton#btn_copy:pressed { background-color: #174EA6; }
                
                QPushButton#btn_pin, QPushButton#btn_delete, QPushButton#btn_view { 
                    background-color: #EEEFF0; 
                    border-radius: 6px; 
                    padding: 4px;
                    border: 1px solid #DADCE0;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
                QPushButton#btn_view:hover { background-color: #E8F0FE; border-color: #1A73E8; }
                QPushButton#btn_pin:hover { background-color: #FEF7D0; border-color: #FBBC04; }
                QPushButton#btn_pin[pinned="true"] {
                    background-color: #FEF7E0;
                    border-color: #FBBC04;
                }
                QPushButton#btn_pin[pinned="true"]:hover {
                    background-color: #FDF0CD;
                }
                QPushButton#btn_delete:hover { background-color: #FCE8E6; border-color: #EA4335; }
                
                QPushButton#btn_minimize { 
                    background-color: transparent; 
                    color: #1A73E8; 
                    border-radius: 6px; 
                    padding: 6px 10px;
                    border: 2px solid #1A73E8;
                    font-weight: bold;
                }
                QPushButton#btn_minimize:hover { background-color: rgba(26, 115, 232, 0.1); }
                QPushButton#btn_minimize:pressed { background-color: rgba(26, 115, 232, 0.2); }
 
                QPushButton#btn_clear { 
                    background-color: transparent; 
                    color: #D93025; 
                    border-radius: 6px; 
                    padding: 6px 10px;
                    border: 2px solid #D93025;
                    font-weight: bold;
                }
                QPushButton#btn_clear:hover { background-color: rgba(217, 48, 37, 0.1); }
                QPushButton#btn_clear:pressed { background-color: rgba(217, 48, 37, 0.2); }
 
                QPushButton#btn_rename_db {
                    background-color: #FFFFFF;
                    border-radius: 0px;
                    border: 1px solid #DADCE0;
                    border-left-color: transparent;
                }
                QPushButton#btn_rename_db:hover { background-color: #FEF7D0; border-color: #FBBC04; }
 
                QPushButton#btn_remove_db {
                    background-color: #FFFFFF;
                    border-radius: 0px;
                    border-top-right-radius: 6px;
                    border-bottom-right-radius: 6px;
                    border: 1px solid #DADCE0;
                    border-left-color: transparent;
                }
                QPushButton#btn_remove_db:hover { background-color: #FCE8E6; border-color: #EA4335; }

                QDialog, QInputDialog, QMessageBox {
                    background-color: #FFFFFF;
                }
                QDialog QLabel, QInputDialog QLabel, QMessageBox QLabel {
                    color: #202124;
                }
                QDialog QPushButton, QInputDialog QPushButton, QMessageBox QPushButton {
                    background-color: #FFFFFF;
                    color: #3C4043;
                    border: 1px solid #DADCE0;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: 600;
                }
                QDialog QPushButton:hover, QInputDialog QPushButton:hover, QMessageBox QPushButton:hover {
                    background-color: #F1F3F4;
                }
                QDialog QLineEdit, QInputDialog QLineEdit {
                    background-color: #FFFFFF;
                    color: #202124;
                    border: 1px solid #DADCE0;
                    border-radius: 6px;
                    padding: 4px;
                }
            """
            
        self.setStyleSheet(styleSheet)
        
        # Cập nhật style và chữ hiển thị của nút Bật/Tắt giám sát bằng Style riêng
        if self.isMonitoring:
            self.btnToggle.setText("Đang Bật")
            self.btnToggle.setStyleSheet("""
                QPushButton {
                    background-color: #34A853; 
                    color: white; 
                    font-weight: bold; 
                    padding: 8px 16px; 
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover { background-color: #2E9648; }
            """)
        else:
            self.btnToggle.setText("Đang Tắt")
            self.btnToggle.setStyleSheet("""
                QPushButton {
                    background-color: #EA4335; 
                    color: white; 
                    font-weight: bold; 
                    padding: 8px 16px; 
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover { background-color: #D33C2F; }
            """)

    # === CÁC HÀM LOGIC === ──────────────────────────────────
    def ReloadComboDb(self):
        """Tải lại danh sách tên các kho trong ComboBox chọn database."""
        self.comboDb.blockSignals(True)
        self.comboDb.clear()
        for name in dbManager.DisplayNames():
            self.comboDb.addItem(name)
        self.comboDb.addItem(_ADD_DB_LABEL)   # Thêm dòng Thêm kho mới vào cuối
        # Chọn lại kho hiện tại
        idx = self.comboDb.findText(self._currentDbName)
        if idx >= 0:
            self.comboDb.setCurrentIndex(idx)
        self.comboDb.blockSignals(False)

    def OnComboDbActivated(self, index: int):
        # Kiểm tra mục người dùng vừa chọn trong dropdown
        text = self.comboDb.itemText(index)
        if text == _ADD_DB_LABEL:
            # Nếu là thêm kho mới, khôi phục lại lựa chọn trước đó và mở hộp thoại tạo
            revertIdx = self.comboDb.findText(self._currentDbName)
            self.comboDb.blockSignals(True)
            self.comboDb.setCurrentIndex(revertIdx)
            self.comboDb.blockSignals(False)
            self.AddDatabaseDialog()
        else:
            # Nếu là kho có sẵn, tiến hành chuyển đổi
            self.SwitchDatabase(text)

    def SwitchDatabase(self, displayName: str):
        # Chuyển đổi sang làm việc với file database khác
        if displayName == self._currentDbName:
            return
        self._currentDbName = displayName
        self.db.Close()
        self.db = DatabaseHandler(dbManager.FilenameFor(displayName))
        self.RefreshList()

    # ────────────────────────────────────────────────────
    def AddDatabaseDialog(self):
        # Hiển thị popup yêu cầu nhập tên kho mới cần thêm
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Thêm kho mới")
        dialog.setLabelText("Tên kho (ví dụ: Công Việc, Học Tập...):")
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Hủy")
        
        ok = dialog.exec()
        name = dialog.textValue().strip()
        if not ok or not name:
            return
        if name in dbManager.DisplayNames():
            QMessageBox.warning(self, "Trùng Tên", f'Kho "{name}" đã tồn tại.')
            return
        dbManager.AddDatabase(name)
        self._currentDbName = name
        self.db.Close()
        self.db = DatabaseHandler(dbManager.FilenameFor(name))
        self.ReloadComboDb()
        self.RefreshList()

    def ConfirmRemoveDatabase(self):
        # Yêu cầu xác nhận xóa kho dữ liệu hiện tại
        names = dbManager.DisplayNames()
        if len(names) <= 1:
            QMessageBox.information(
                self, "Không Thể Xóa",
                "Bạn phải giữ ít nhất một kho dữ liệu."
            )
            return
        box = QMessageBox(self)
        box.setWindowTitle("Xóa Kho")
        box.setText(
            f'Bạn có chắc muốn xóa kho <b>"{self._currentDbName}"</b>?<br>'
            "Toàn bộ dữ liệu trong kho này sẽ bị xóa vĩnh viễn."
        )
        box.setIcon(QMessageBox.Icon.Warning)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Xóa")
        box.button(QMessageBox.StandardButton.No).setText("Hủy")
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        removed = self._currentDbName
        self.db.Close()
        dbManager.RemoveDatabase(removed)
        # Chuyển về làm việc với kho còn lại đầu tiên
        self._currentDbName = dbManager.FirstName()
        self.db = DatabaseHandler(dbManager.FilenameFor(self._currentDbName))
        self.ReloadComboDb()
        self.RefreshList()

    def ConfirmRenameDatabase(self):
        # Hiển thị popup yêu cầu đổi tên kho hiện tại
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Đổi Tên")
        dialog.setLabelText(f"Nhập tên mới cho kho '{self._currentDbName}':")
        dialog.setTextValue(self._currentDbName)
        dialog.setOkButtonText("OK")
        dialog.setCancelButtonText("Hủy")
        
        ok = dialog.exec()
        newName = dialog.textValue().strip()
        if not ok or not newName or newName == self._currentDbName:
            return
        if newName in dbManager.DisplayNames():
            QMessageBox.warning(self, "Trùng Tên", f'Kho "{newName}" đã tồn tại.')
            return

        self.db.Close()
        dbManager.RenameDatabase(self._currentDbName, newName)
        self._currentDbName = newName
        self.db = DatabaseHandler(dbManager.FilenameFor(newName))
        self.ReloadComboDb()
        self.RefreshList()

    def OnClipboardChange(self):
        # Xử lý sự kiện lưu bản ghi mới khi clipboard của hệ điều hành thay đổi
        if not self.isMonitoring or self.ignoreNextChange:
            self.ignoreNextChange = False
            return
            
        mimeData = self.clipboard.mimeData()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if mimeData.hasImage():
            # Xử lý lưu định dạng hình ảnh sang bytes PNG
            image = self.clipboard.image()
            if not image.isNull():
                byteArray = QByteArray()
                buffer = QBuffer(byteArray)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(buffer, "PNG")
                if self.db.InsertImage(byteArray.data(), timestamp):
                    self.RefreshList()
                    
        elif mimeData.hasText():
            # Xử lý lưu định dạng văn bản UTF-8
            text = mimeData.text().strip()
            if text:
                if self.db.InsertText(text, timestamp):
                    self.RefreshList()

    def ToggleMonitoring(self):
        # Chuyển đổi trạng thái bật/tắt theo dõi clipboard của ứng dụng
        self.isMonitoring = not self.isMonitoring
        self.ApplyTheme() # Vẽ lại màu nút Toggle tương ứng trạng thái mới

    def RefreshList(self):
        # Xóa sạch tất cả các thẻ bản ghi cũ trong scroll layout
        for i in reversed(range(self.scrollLayout.count())): 
            widget = self.scrollLayout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            
        # Tải danh sách bản ghi mới từ DB theo sắp xếp/lọc được chọn
        sortType = self.comboSort.currentText()
        rows = self.db.GetHistory(sortType)
        
        if not rows:
            # Hiển thị nhãn trống nếu không có dữ liệu
            self.emptyLabel.show()
            self.emptyLabel.raise_()
        else:
            # Vẽ các thẻ card hiển thị tương ứng từng bản ghi
            self.emptyLabel.hide()
            for row in rows:
                itemId, itemType, content, timestamp, isPinned = row
                card = ClipboardCard(itemId, itemType, content, timestamp, isPinned, 
                                     self.HandlePin, self.HandleCopy, self.HandleDelete)
                self.scrollLayout.addWidget(card)

    def HandlePin(self, itemId, currentStatus):
        # Hàm callback xử lý sự kiện bấm ghim một thẻ
        self.db.TogglePin(itemId, currentStatus)
        self.RefreshList()

    def HandleDelete(self, itemId):
        # Hàm callback xử lý sự kiện bấm xóa một thẻ
        self.db.DeleteItem(itemId)
        self.RefreshList()

    def HandleCopy(self, itemType, content):
        # Hàm callback xử lý sự kiện nạp lại dữ liệu của thẻ vào clipboard hệ thống
        self.ignoreNextChange = True # Chặn không cho ứng dụng lưu lại dữ liệu do chính nó copy ra
        if itemType == "text":
            self.clipboard.setText(content.decode('utf-8'))
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(content)
            self.clipboard.setImage(pixmap.toImage())

    def ConfirmClearAll(self):
        # Yêu cầu xác nhận làm mới/xóa toàn bộ lịch sử trong kho hiện tại
        box = QMessageBox(self)
        box.setWindowTitle("Làm Mới")
        box.setText("Bạn có chắc chắn muốn xóa toàn bộ lịch sử lưu trữ trong kho này?")
        box.setIcon(QMessageBox.Icon.Question)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Xác nhận")
        box.button(QMessageBox.StandardButton.No).setText("Hủy")
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.db.ClearAll()
            self.RefreshList()
 
    def SaveUserSettings(self):
        # Lưu cài đặt hiện tại của người dùng vào settings.json
        dbManager.SaveSettings(
            self.comboTheme.currentText(),
            self.comboSort.currentText(),
            self._currentDbName
        )

    def ShowStartupPopup(self):
        # Hiển thị thông tin giới thiệu/thông báo khi mở ứng dụng lần đầu
        box = QMessageBox(self)
        box.setWindowTitle("Xin Chào!")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(
            "Đây là sản phẩm mà nhóm chúng mình (nhóm Công Nghệ Thông Tin) chuẩn bị cho bài thi kết thúc học phần "
            "<b>Tư Duy Hệ Thống</b> (SYTH220491)<br><br>"
            "Thành Viên:"
            "<table style='margin-left:8px; margin-top:4px; border-spacing: 0 2px;'>"
            "<tr><td>+&nbsp;Nguyễn Hải Đăng</td><td>&nbsp;→&nbsp;</td><td>Quản lý dự án</td></tr>"
            "<tr><td>+&nbsp;Nguyễn Quốc Anh Khoa</td><td>&nbsp;→&nbsp;</td><td>Thiết kế giao diện</td></tr>"
            "<tr><td>+&nbsp;Huỳnh Trí Đức</td><td>&nbsp;→&nbsp;</td><td>Thiết kế cơ sở dữ liệu</td></tr>"
            "<tr><td>+&nbsp;Đỗ Ngọc Hân</td><td>&nbsp;→&nbsp;</td><td>Kiểm thử</td></tr>"
            "</table><br><br>"
            "Chúng mình là sinh viên năm nhất nên sản phẩm chưa được hoàn hảo như dự kiến, "
            "mong các bạn thông cảm và góp ý nhé <b>:D</b><br><br>"
            "<i>Địa chỉ liên hệ: <a href='https://github.com/DomieGD'>github.com/DomieGD</a></i>"
        )
        box.setIcon(QMessageBox.Icon.Information)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.button(QMessageBox.StandardButton.Ok).setText("OK")
        
        # Áp dụng stylesheet QMessageBox đồng bộ theo Theme màu
        isDark = True
        themeChoice = self.comboTheme.currentText().lower()
        if themeChoice == "theo hệ thống":
            isDark = self.IsSystemDarkMode()
        else:
            isDark = (themeChoice == "chế độ tối")
            
        if isDark:
            box.setStyleSheet("""
                QMessageBox {
                    background-color: #1E1E1E;
                    color: #E0E0E0;
                }
                QLabel {
                    color: #E0E0E0;
                    font-size: 13px;
                    qproperty-alignment: 'AlignJustify';
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
                    qproperty-alignment: 'AlignJustify';
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
            """)
        
        # Căn chỉnh văn bản dạng justify bằng cách tìm trực tiếp QLabel con bên trong hộp thoại
        for lbl in box.findChildren(QLabel):
            lbl.setOpenExternalLinks(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignJustify)
        box.exec()

    def closeEvent(self, event):
        # Sự kiện tắt cửa sổ chính: Lưu cấu hình và giải phóng kết nối cơ sở dữ liệu
        self.SaveUserSettings()
        self.db.Close()
        event.accept()

    def QuitApplication(self):
        # Đóng cửa sổ để kích hoạt closeEvent lưu cấu hình
        self.close()
        # Thoát ứng dụng hoàn toàn
        QApplication.instance().quit()

    def InitTray(self):
        # Khởi tạo biểu tượng ở khay hệ thống (System Tray) và Menu chuột phải
        self.trayIcon = QSystemTrayIcon(self)
        if os.path.exists(appIconPath):
            self.trayIcon.setIcon(QIcon(appIconPath))
        else:
            self.trayIcon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.trayIcon.setToolTip("Quản Lý Sao Chép")
        self.trayIcon.activated.connect(self.OnTrayActivated)

        trayMenu = QMenu()
        showAction = QAction("Mở ứng dụng", self)
        showAction.triggered.connect(self.RestoreFromTray)
        quitAction = QAction("Thoát", self)
        quitAction.triggered.connect(self.QuitApplication)
        
        trayMenu.addAction(showAction)
        trayMenu.addAction(quitAction)
        self.trayIcon.setContextMenu(trayMenu)

    def MinimizeToTray(self):
        # Ẩn cửa sổ ứng dụng
        self.hide()
        self.trayIcon.show()

    def RestoreFromTray(self):
        # Phục hồi hiển thị cửa sổ chính từ khay hệ thống
        self.showNormal()
        self.activateWindow()
        self.trayIcon.hide()

    def OnTrayActivated(self, reason):
        # Xử lý sự kiện click chuột trái vào biểu tượng khay hệ thống để hiện lại app
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.RestoreFromTray()