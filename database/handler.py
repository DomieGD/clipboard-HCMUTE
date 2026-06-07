"""
File này xử lý các sự kiện copy văn bản/hình ảnh và các nút xem/ghim/xóa dữ liệu trong một kho
"""

import os
import sys
import sqlite3

class DatabaseHandler:
    def __init__(self, dbName="cá_nhân.db"):
        # Xác định thư mục lưu trữ database
        # - Khi chạy dưới dạng file .exe (PyInstaller): lưu cạnh file .exe
        # - Khi chạy dưới dạng script Python thông thường: lưu trong thư mục database/
        if getattr(sys, "frozen", False):
            dbDir = os.path.join(os.path.dirname(sys.executable), "database")
        else:
            dbDir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(dbDir, exist_ok=True)
        self.dbPath = os.path.join(dbDir, dbName)
        
        self.conn = None
        self.cursor = None
        self.Connect()

    def Connect(self):
        # Kết nối tới cơ sở dữ liệu và tạo bảng nếu chưa có
        if self.conn:
            self.conn.close()
            
        self.conn = sqlite3.connect(self.dbPath)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                content BLOB,
                timestamp TEXT,
                is_pinned INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def InsertText(self, text, timestamp):
        # Kiểm tra trùng lặp với dòng text gần nhất
        self.cursor.execute("SELECT content FROM clipboard_history WHERE type='text' ORDER BY id DESC LIMIT 1")
        lastRow = self.cursor.fetchone()
        if lastRow and lastRow[0].decode('utf-8') == text:
            return False # Trùng lặp, không lưu
            
        self.cursor.execute("INSERT INTO clipboard_history (type, content, timestamp) VALUES (?, ?, ?)", 
                            ("text", text.encode('utf-8'), timestamp))
        self.conn.commit()
        return True

    def InsertImage(self, blobData, timestamp):
        # [MỚI] Kiểm tra xem ảnh mới có bị trùng hoàn toàn với ảnh vừa lưu gần nhất không
        self.cursor.execute("SELECT content FROM clipboard_history WHERE type='image' ORDER BY id DESC LIMIT 1")
        lastRow = self.cursor.fetchone()
        if lastRow and lastRow[0] == blobData:
            return False # Nếu trùng (do Windows gọi 2 lần), bỏ qua không lưu nữa
            
        self.cursor.execute("INSERT INTO clipboard_history (type, content, timestamp) VALUES (?, ?, ?)", 
                            ("image", blobData, timestamp))
        self.conn.commit()
        return True

    def GetHistory(self, sortType):
        """Lấy dữ liệu đã lọc và sắp xếp (Luôn ưu tiên Ghim lên đầu)"""
        query = "SELECT id, type, content, timestamp, is_pinned FROM clipboard_history"
        conditions = []
        
        if sortType == "Chỉ Văn Bản":
            conditions.append("type='text'")
        elif sortType == "Chỉ Hình Ảnh":
            conditions.append("type='image'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY is_pinned DESC, id DESC"
        
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def TogglePin(self, itemId, currentStatus):
        newStatus = 0 if currentStatus == 1 else 1
        self.cursor.execute("UPDATE clipboard_history SET is_pinned = ? WHERE id = ?", (newStatus, itemId))
        self.conn.commit()

    def DeleteItem(self, itemId):
        self.cursor.execute("DELETE FROM clipboard_history WHERE id = ?", (itemId,))
        self.conn.commit()

    def ClearAll(self):
        self.cursor.execute("DELETE FROM clipboard_history")
        self.conn.commit()

    def Close(self):
        if self.conn:
            self.conn.close()