import environ
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
# Khởi tạo environ
env = environ.Env(
    # Giá trị mặc định nếu không tìm thấy file .env (ví dụ mặc định dùng sqlite)
    DEBUG=(bool, False)
)

# Đọc file .env
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}