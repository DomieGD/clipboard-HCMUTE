import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.window import ClipboardManager

def Main():
    # Đảm bảo thư mục làm việc luôn là thư mục chứa file main.py
    currentDir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(currentDir)
    
    # Khởi tạo ứng dụng Qt
    app = QApplication(sys.argv)
    
    # Thiết lập icon ứng dụng
    appIconPath = os.path.join(currentDir, "ClipboardHCMUTE.ico")
    app.setWindowIcon(QIcon(appIconPath))
    
    # Tạo và hiển thị cửa sổ chính của ứng dụng quản lý sao chép
    window = ClipboardManager()
    window.show()
    
    # Chạy vòng lặp sự kiện chính của ứng dụng
    sys.exit(app.exec())

if __name__ == "__main__":
    Main()