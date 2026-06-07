"""
File này quản lý chung các kho và lưu dữ liệu kho trong databases.json
"""
import json
import os
import re
import sys

# Xác định thư mục lưu trữ database:
# - Khi chạy dưới dạng file .exe (PyInstaller): lưu cạnh file .exe
# - Khi chạy dưới dạng script Python thông thường: lưu trong thư mục database/
if getattr(sys, "frozen", False):
    _dir = os.path.join(os.path.dirname(sys.executable), "database")
else:
    _dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(_dir, exist_ok=True)

# Đường dẫn lưu cấu hình danh sách các database
configFile = os.path.join(_dir, "databases.json")
# Đường dẫn lưu cài đặt cấu hình (theme, sắp xếp, kho hiện tại)
settingsFile = os.path.join(_dir, "settings.json")

# Danh sách database mặc định khi khởi tạo ứng dụng lần đầu
_defaults = {
    "Cá Nhân": "cá_nhân.db",
}


def Load() -> dict:
    # Tải cấu hình danh sách các database từ file json
    if not os.path.exists(configFile):
        Save(dict(_defaults))
        return dict(_defaults)
    with open(configFile, "r", encoding="utf-8") as f:
        return json.load(f)


def Save(data: dict):
    # Lưu cấu hình danh sách các database vào file json
    with open(configFile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ───────────────────────────────────────────────────────────────────────────

def DisplayNames() -> list[str]:
    # Trả về danh sách tên hiển thị của các kho (không phải tên file .db)
    return list(Load().keys())


def FilenameFor(displayName: str) -> str:
    # Trả về tên file .db tương ứng với tên hiển thị của kho
    return Load()[displayName]

 
def AddDatabase(displayName: str) -> str:
    # Thêm một kho dữ liệu mới vào cấu hình
    data = Load()
    if displayName in data:
        return data[displayName]          # Kho đã tồn tại

    # Tạo tên file an toàn (chỉ chứa ký tự chữ và dấu gạch dưới) từ tên hiển thị
    safe = re.sub(r"[^\w]", "_", displayName.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_") or "database"
    candidate = f"{safe}.db"

    # Tránh trùng lặp tên file vật lý bằng cách thêm hậu tố số (_2, _3...) nếu cần
    existing = set(data.values())
    i = 2
    while candidate in existing:
        candidate = f"{safe}_{i}.db"
        i += 1

    data[displayName] = candidate
    Save(data)
    return candidate


def RemoveDatabase(displayName: str):
    # Xóa cấu hình kho dữ liệu và xóa file database vật lý tương ứng
    data = Load()
    fileName = data.pop(displayName, None)
    Save(data)
    if fileName:
        path = os.path.join(_dir, fileName)
        if os.path.exists(path):
            os.remove(path)


def FirstName() -> str:
    # Lấy tên hiển thị của kho dữ liệu đầu tiên trong cấu hình
    names = DisplayNames()
    return names[0] if names else None


def RenameDatabase(oldName: str, newName: str) -> str:
    # Đổi tên hiển thị và tên file .db vật lý tương ứng của kho dữ liệu
    data = Load()
    if oldName not in data:
        return None
    if newName in data:
        return data[newName]

    oldFileName = data[oldName]
    
    # Tạo tên file an toàn cho database mới
    safe = re.sub(r"[^\w]", "_", newName.lower().strip())
    safe = re.sub(r"_+", "_", safe).strip("_") or "database"
    candidate = f"{safe}.db"

    # Đảm bảo đặt tên file không trùng lặp
    existing = set(data.values())
    i = 2
    while candidate in existing:
        candidate = f"{safe}_{i}.db"
        i += 1

    # Tiến hành đổi tên file database vật lý trên đĩa
    oldPath = os.path.join(_dir, oldFileName)
    newPath = os.path.join(_dir, candidate)
    if os.path.exists(oldPath):
        os.rename(oldPath, newPath)

    # Cập nhật thông tin trong file cấu hình json
    data[newName] = candidate
    del data[oldName]
    Save(data)
    
    return candidate


# ───────────────────────────────────────────────────────────────────────────

def LoadSettings() -> dict:
    # Trả về dict cài đặt cấu hình từ settings.json, hoặc mặc định nếu chưa có.
    defaultDb = FirstName() or "Cá Nhân"
    defaultSettings = {
        "theme": "Theo Hệ Thống",
        "sort": "Mới Nhất",
        "database": defaultDb
    }
    if os.path.exists(settingsFile):
        try:
            with open(settingsFile, "r", encoding="utf-8") as f:
                settings = json.load(f)
                # Đảm bảo các key cần thiết đều có mặt
                for k, v in defaultSettings.items():
                    if k not in settings:
                        settings[k] = v
                return settings
        except Exception:
            return defaultSettings
    return defaultSettings


def SaveSettings(theme: str, sort: str, database: str):
    # Lưu cài đặt theme, sort và database hiện tại vào settings.json.
    try:
        with open(settingsFile, "w", encoding="utf-8") as f:
            json.dump({
                "theme": theme,
                "sort": sort,
                "database": database
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

