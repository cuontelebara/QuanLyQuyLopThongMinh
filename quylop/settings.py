"""
Django settings for quylop project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-p_==j%3i#j_ref8m77mw=v2dj7rdvycx(z5pd(b#kd-(yfwtm6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# --- CẤU HÌNH TÊN MIỀN & NGROK BẢO MẬT ---
ALLOWED_HOSTS = ['fundsmart.com', '127.0.0.1', 'localhost', '*', '.ngrok-free.app', '.ngrok-free.dev'] 
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
]

# ==========================================
# 1. KHAI BÁO APP (INSTALLED_APPS)
# ==========================================
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",  
    
    "import_export", 

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', 

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.facebook',

    'captcha',  
    'quanlyquy', 
]

# --- CẤU HÌNH BẢO MẬT GOOGLE RECAPTCHA V2 ---
RECAPTCHA_PUBLIC_KEY = '6LdkaoUsAAAAAPFYnV6w0rTnOX7uAbVA97NIBZGJ'
RECAPTCHA_PRIVATE_KEY = '6LdkaoUsAAAAAKXc5-j8CfG9DAHPWZby35flB29F'

# --- CẤU HÌNH GỬI MAIL THẬT QUA GMAIL ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tranquanquan025@gmail.com'
EMAIL_HOST_PASSWORD = 'nmecpnxudgxivmrp' 
DEFAULT_FROM_EMAIL = 'FundFlow PRO <tranquanquan025@gmail.com>'

SITE_ID = 3

# ==========================================
# 2. MIDDLEWARE & BACKENDS
# ==========================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    'allauth.account.middleware.AccountMiddleware',
    'quanlyquy.middleware.TimezoneMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ROOT_URLCONF = 'quylop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'quylop.wsgi.application'

# ==========================================
# 3. DATABASE & CUSTOM USER (KÈM CẤU HÌNH ALLAUTH)
# ==========================================
# settings.py
# quylop/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'quy_thong_minh', 
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '172.24.252.201',
        'PORT': '3306',           # CỔNG CHUẨN
    }
}









AUTH_USER_MODEL = 'quanlyquy.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# --- CẤU HÌNH ĐĂNG NHẬP MẠNG XÃ HỘI (Bypass Lỗi Trắng Màn Hình) ---
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_EMAIL_VERIFICATION = "none" # Tắt bắt buộc xác thực email
ACCOUNT_SIGNUP_FIELDS = ['email', 'username*', 'password1*', 'password2*']     # Không bắt buộc phải có email

SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name', 'picture'],
        'VERIFIED_EMAIL': False,
        'VERSION': 'v19.0',
    }
}

# ==========================================
# 4. NGÔN NGỮ, FORMAT & ĐIỀU HƯỚNG
# ==========================================
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = False

# Format tiền tệ Việt Nam (1.000.000)
USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'login_redirect'
LOGOUT_REDIRECT_URL = 'login'

# ==========================================
# 5. STATIC & MEDIA
# ==========================================
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# 6. GIAO DIỆN ADMIN (UNFOLD) - BẢN CHUẨN ERP
# ==========================================
UNFOLD = {
    "SITE_TITLE": "FundSmart Admin",
    "SITE_HEADER": "Quản Trị FundSmart Pro",
    "DASHBOARD_CALLBACK": "quanlyquy.admin_dashboard.dashboard_callback",
    "SITE_SYMBOL": "account_balance",
    "COLORS": {
        "primary": {
            "50": "236, 253, 245", "100": "209, 250, 229", "200": "167, 243, 208", 
            "300": "110, 231, 183", "400": "52, 211, 153", "500": "16, 185, 129", 
            "600": "5, 150, 105", "700": "4, 120, 87", "800": "6, 95, 70", "900": "6, 78, 59",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False, 
        "navigation": [
            {
                "title": "1. QUẢN LÝ TÀI CHÍNH",
                "icon": "account_balance_wallet",
                "items": [
                    {"title": "Sổ Giao Dịch", "link": "/admin/quanlyquy/giaodich/", "icon": "receipt_long"},
                    {"title": "Quản Lý Quỹ", "link": "/admin/quanlyquy/loaiquy/", "icon": "account_balance"},
                    {"title": "Đợt Thu Tiền", "link": "/admin/quanlyquy/dotthu/", "icon": "calendar_month"},
                    {"title": "Danh Mục Thu/Chi", "link": "/admin/quanlyquy/danhmucthuchi/", "icon": "category"},
                ],
            },
            {
                "title": "2. NHÂN SỰ & THÀNH VIÊN",
                "icon": "group",
                "items": [
                    {"title": "Hồ Sơ Sinh Viên", "link": "/admin/quanlyquy/thanhvien/", "icon": "badge"},
                    {"title": "Lớp Học", "link": "/admin/quanlyquy/lophoc/", "icon": "school"},
                    {"title": "Tài Khoản (User)", "link": "/admin/quanlyquy/user/", "icon": "manage_accounts"},
                ],
            },
            {
                "title": "3. TÀI SẢN & KẾ HOẠCH",
                "icon": "inventory_2",
                "items": [
                    {"title": "Tài Sản Lớp", "link": "/admin/quanlyquy/taisan/", "icon": "weekend"},
                    {"title": "Mục Tiêu Tích Lũy", "link": "/admin/quanlyquy/muctieuquy/", "icon": "track_changes"},
                    {"title": "Sự Kiện", "link": "/admin/quanlyquy/sukiennhacviec/", "icon": "event"},
                ],
            },
            {
                "title": "4. GAMIFICATION & HỆ THỐNG",
                "icon": "sports_esports",
                "items": [
                    {"title": "Nhiệm Vụ Xu", "link": "/admin/quanlyquy/nhiemvu/", "icon": "task_alt"},
                    {"title": "Cửa Hàng Quà", "link": "/admin/quanlyquy/quatang/", "icon": "storefront"},
                    {"title": "Khảo Sát / Vote", "link": "/admin/quanlyquy/bieuquyet/", "icon": "how_to_vote"},
                    {"title": "Lịch Sử Webhook", "link": "/admin/quanlyquy/lichsuwebhook/", "icon": "webhook"},
                ],
            },
            {
                "title": "5. CẤU HÌNH MẠNG XÃ HỘI",
                "icon": "settings_applications",
                "items": [
                    {"title": "Tên miền (Sites)", "link": "/admin/sites/site/", "icon": "language"},
                    {"title": "App Đăng nhập (Social Apps)", "link": "/admin/socialaccount/socialapp/", "icon": "vpn_key"},
                    {"title": "Tài khoản liên kết", "link": "/admin/socialaccount/socialaccount/", "icon": "link"},
                ],
            },
            {
                "title": "QUAY LẠI TRANG CHỦ",
                "icon": "public",
                "items": [
                    {"title": "Về Website", "link": "/", "icon": "home"},
                ]
            }
        ],
    },
}
# Ép Allauth luôn luôn sử dụng HTTPS khi tạo link giao tiếp với Facebook/Google
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"