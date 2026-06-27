"""
URL configuration for quylop project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Import bộ công cụ xử lý mật khẩu có sẵn của Django
from django.contrib.auth import views as auth_views 

# Import rõ ràng 2 file xử lý riêng biệt
from quanlyquy import views       # Xử lý giao diện HTML
from quanlyquy import api_views   # Xử lý dữ liệu ngầm (API)

urlpatterns = [
    # --- 1. HỆ THỐNG QUẢN TRỊ ---
    path('admin/', admin.site.urls),
    
    
    # TRẠM ĐIỀU HƯỚNG: Tự động phân loại người dùng sau login
    path('dieu-huong/', views.login_redirect_view, name='login_redirect'),

    # --- 2. GIAO DIỆN CHÍNH (HTML Pages - TRỎ VỀ views.py) ---
    path('', views.dashboard, name='dashboard'), 
    path('thong-ke/', views.thong_ke_view, name='thong_ke'), 
    path('giao-dich/', views.giao_dich_view, name='page_giao_dich'),
    path('tien-do/', views.tien_do_thu_view, name='page_tien_do'),
    path('gamification/', views.gamification_view, name='gamification'),
    path('cua-hang/', views.store_view, name='store'),
    path('cai-dat/', views.settings_view, name='settings'),
    path('qa-testing/', views.qa_testing_view, name='qa_testing'),
    
    # API chuyên dụng cho QA Chaos Lab
    path('api/chaos/', views.api_chaos_action, name='api_chaos_action'),
    path('api/mass-remind/', views.api_mass_remind_debt, name='api_mass_remind_debt'),
    path('api/clear-notifications/', views.api_clear_notifications, name='api_clear_notifications'),
    
    # API Webhook Nhận tiền tự động (Bank/SePay)
    path('api/webhook/sepay/', views.sepay_webhook, name='sepay_webhook'),
    
    # --- 3. API ENDPOINTS (Dữ liệu JSON cho Modal & Chart - TRỎ VỀ api_views.py) ---
    # path('api/nop-quy/', api_views.api_nop_quy, name='api_nop_quy'),
    path('api/tam-ung/', api_views.api_tam_ung, name='api_tam_ung'),
    path('api/tao-quy/', api_views.api_tao_quy, name='api_tao_quy'),
    path('api/nop-quy-ho/', api_views.api_nop_quy_ho, name='api_nop_quy_ho'),
    path('api/chuyen-noi-bo/', api_views.api_chuyen_noi_bo, name='api_chuyen_noi_bo'),
    path('api/nhac-no/', api_views.api_nhac_no, name='api_nhac_no'),
    path('api/chart-data/', api_views.api_chart_data, name='api_chart_data'),
    path('giao-dich/export-misa/', views.export_misa_view, name='export_misa'),
    path('api/nop-quy/', api_views.api_nop_quy, name='api_nop_quy'),
    path('api/gacha/spin/', api_views.api_spin_gacha, name='api_spin_gacha'),
    path('api/gacha/vote/', api_views.api_submit_vote, name='api_submit_vote'),
    path('api/shop/buy/', api_views.api_buy_item, name='api_buy_item'),
    path('api/submit-vote/', api_views.api_submit_vote, name='api_submit_vote'),
    
    # --- 4. HÀM ĐĂNG NHẬP, ĐĂNG KÝ & ĐĂNG XUẤT ---
    path('accounts/login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),    
    path('logout/', views.logout_view, name='logout'),

    # --- 5. ĐƯỜNG DẪN BẮT BUỘC CHO GOOGLE LOGIN & CAPTCHA ---
    path('accounts/', include('allauth.urls')),
    path('captcha/', include('captcha.urls')),

    # --- 6. QUY TRÌNH QUÊN MẬT KHẨU ---
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='quanlyquy/password_reset.html',
        email_template_name='quanlyquy/password_reset_email.html',
        html_email_template_name='quanlyquy/password_reset_email.html',
        subject_template_name='quanlyquy/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='quanlyquy/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='quanlyquy/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='quanlyquy/password_reset_complete.html'
    ), name='password_reset_complete'),

    # --- 7. Chatbot AI ---
    path('api/chatbot/', api_views.api_chatbot, name='api_chatbot'),
     # --- 8 đổi quà  ---
    path('api/doi-qua/', views.api_doi_qua, name='api_doi_qua'),
    path('tui-do/', views.tui_do_view, name='tui_do'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)