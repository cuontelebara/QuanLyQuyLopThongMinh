import json
import requests
import time
import random
import csv
from datetime import datetime, timedelta
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Gom tất cả Model vào 1 chỗ cho dễ quản lý
from .models import (
    GiaoDich, LichSuGiaoDichXu, ThanhVien, TaiSan, LoaiQuy, DotThu, 
    MucTieuQuy, SuKienNhacViec, User, QuaTang, 
    NhiemVu, BieuQuyet, HuyHieuThanhVien, QATestingLog, 
    LichSuWebhook, DanhMucThuChi, ThongBaoBuuTa, ChiTietBinhChon, KhoDoThanhVien
)
from .utils import format_money

# ==========================================
# 1. HÀM BỔ TRỢ (HELPERS)
# ==========================================
def is_thu_quy(user):
    return user.is_active and (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'ADMIN')

def get_percent_change(current, previous):
    if not previous or previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)

def check_and_reward_quest(request, tu_khoa_nhiem_vu):
    if not request.user.is_authenticated: return False

    nv = NhiemVu.objects.filter(ten_nhiem_vu__icontains=tu_khoa_nhiem_vu, is_active=True).first()
    if not nv: return False

    tv = ThanhVien.objects.filter(user=request.user).first()
    if not tv:
        tv = ThanhVien.objects.create(
            ho_ten=request.user.full_name or request.user.username,
            mssv=getattr(request.user, 'mssv', f"ADMIN-{request.user.id}"),
            user=request.user,)
@login_required
def store_view(request):
    # Lấy thông tin thành viên khớp với user đang đăng nhập
    my_tv = ThanhVien.objects.filter(user=request.user).first()
    
    # Nếu tìm thấy thành viên, lấy xu từ bảng ThanhVien, nếu không thì lấy mặc định 0
    vi_xu = my_tv.vi_xu if my_tv else 0
    
    items = QuaTang.objects.all()
    context = {
        'items': items,
        'vi_xu': vi_xu,  # Truyền biến vi_xu chuẩn vào đây
        'is_admin': is_thu_quy(request.user),
        'user_role_name': "Thủ quỹ hệ thống" if is_thu_quy(request.user) else "Thành viên lớp" 
    }
    check_and_reward_quest(request, 'Window Shopping')
    return render(request, 'quanlyquy/store.html', context)
        

    today = timezone.now().date()
    da_lam = LichSuGiaoDichXu.objects.filter(
        thanh_vien=tv, 
        nhiem_vu_lien_quan=nv,
        ngay_thuc_hien__date=today
    ).exists()
    
    if da_lam: return False 

    tv.vi_xu += nv.phan_thuong_xu
    tv.save()
    
    LichSuGiaoDichXu.objects.create(
        thanh_vien=tv, loai_giao_dich='CONG_XU', so_xu=nv.phan_thuong_xu,
        ly_do=f"Hoàn thành Quest: {nv.ten_nhiem_vu}", 
        nhiem_vu_lien_quan=nv, 
        created_by=str(request.user.id)
    )

    messages.success(request, f"QUEST_SUCCESS|{nv.ten_nhiem_vu}|{nv.phan_thuong_xu}")
    return True

# ==========================================
# 2. HỆ THỐNG XÁC THỰC (AUTH)
# ==========================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not recaptcha_response:
            messages.error(request, 'Vui lòng xác thực "Tôi không phải là người máy"!')
            return render(request, 'quanlyquy/login.html', {'username': username})

        data = {'secret': settings.RECAPTCHA_PRIVATE_KEY, 'response': recaptcha_response}
        try:
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data, timeout=5)
            if not r.json().get('success'):
                messages.error(request, 'Xác thực Captcha thất bại!')
                return render(request, 'quanlyquy/login.html', {'username': username})
        except:
            messages.error(request, 'Lỗi kết nối xác thực!')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session.set_expiry(1209600 if remember_me else 0)
            messages.success(request, f'Chào mừng {user.full_name or user.username} quay trở lại!')
            return redirect('login_redirect')
        else:
            messages.error(request, 'Tài khoản không tồn tại hoặc sai mật khẩu!')
            
    return render(request, 'quanlyquy/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        full_name = request.POST.get('full_name', '').strip()
        mssv = request.POST.get('mssv', '').strip()

        context = {'username': username, 'email': email, 'full_name': full_name, 'mssv': mssv}

        if password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp!")
            return render(request, 'quanlyquy/register.html', context)
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập này đã tồn tại!")
            return render(request, 'quanlyquy/register.html', context)

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.full_name = full_name
            user.mssv = mssv
            user.role = 'MEMBER'   
            user.is_staff = False  
            user.save()
            
            messages.success(request, "Tạo tài khoản thành công! Vui lòng đăng nhập.")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Lỗi tạo tài khoản: {str(e)}")
            return render(request, 'quanlyquy/register.html', context)
            
    return render(request, 'quanlyquy/register.html')

@login_required
def login_redirect_view(request):
    if is_thu_quy(request.user):
        return redirect('/admin/') 
    else:
        return redirect('dashboard')

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, "Bạn đã đăng xuất khỏi hệ thống.")
        return redirect('login')
    return redirect('/')

# ==========================================
# 3. TRANG CHỦ & DASHBOARD (ĐÃ PHÂN QUYỀN TÂN TIẾN)
# ==========================================
@login_required
def dashboard(request):
    check_and_reward_quest(request, 'Chăm chỉ điểm danh')
    now = timezone.now()
    thang_nay = now.month
    nam_nay = now.year
    
    first_day_this_month = now.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    thang_truoc = last_day_last_month.month
    nam_truoc = last_day_last_month.year

    is_admin = is_thu_quy(request.user)
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"
    member_section_title = "Hồ sơ Thành Viên" if is_admin else "Bạn bè cùng lớp"
    
    tv = ThanhVien.objects.filter(user=request.user).first()

    # 🔒 PHÂN QUYỀN TRUY CẬP DỮ LIỆU CỐT LÕI
    giao_dich_cho_duyet = [] # Khởi tạo biến
    if is_admin:
        base_gd = GiaoDich.objects.all()
        danh_sach_no_xau = ThanhVien.objects.filter(is_no_xau=True)
        giao_dich_moi = GiaoDich.objects.all().select_related('thanh_vien').order_by('-ngay_tao')[:5]
        
        # LẤY TIỀN MẶT CHỜ DUYỆT (CHỈ ADMIN)
        giao_dich_cho_duyet = GiaoDich.all_objects.filter(
            phuong_thuc='CASH', 
            da_xac_nhan=False, 
            loai='THU'
        ).select_related('thanh_vien').order_by('-created_at')
    else:
        base_gd = GiaoDich.objects.filter(thanh_vien=tv) if tv else GiaoDich.objects.none()
        danh_sach_no_xau = ThanhVien.objects.filter(id=tv.id, is_no_xau=True) if tv else []
        giao_dich_moi = GiaoDich.objects.filter(thanh_vien=tv).select_related('thanh_vien').order_by('-ngay_tao')[:5] if tv else []

    thu_thang_nay = base_gd.filter(loai__in=['THU', 'LAI', 'HU'], ngay_tao__month=thang_nay, ngay_tao__year=nam_nay).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    chi_thang_nay = base_gd.filter(loai__in=['CHI', 'TU'], ngay_tao__month=thang_nay, ngay_tao__year=nam_nay).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    
    thu_thang_truoc = base_gd.filter(loai__in=['THU', 'LAI', 'HU'], ngay_tao__month=thang_truoc, ngay_tao__year=nam_truoc).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    chi_thang_truoc = base_gd.filter(loai__in=['CHI', 'TU'], ngay_tao__month=thang_truoc, ngay_tao__year=nam_truoc).aggregate(Sum('so_tien'))['so_tien__sum'] or 0

    thu_percent = get_percent_change(thu_thang_nay, thu_thang_truoc)
    chi_percent = get_percent_change(chi_thang_nay, chi_thang_truoc)

    thu_tong = base_gd.filter(loai__in=['THU', 'LAI', 'HU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    chi_tong = base_gd.filter(loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    so_du_raw = thu_tong - chi_tong

    stats = (base_gd.annotate(month=TruncMonth('ngay_tao'))
             .values('month').annotate(
                 thu=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
                 chi=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
             ).order_by('-month')[:6])
    
    stats_list = list(stats)[::-1]
    chart_months = [s['month'].strftime("Th%m/%y") for s in stats_list if s['month']]
    chart_thu = [float(s['thu'] or 0) for s in stats_list]
    chart_chi = [float(s['chi'] or 0) for s in stats_list]

    ai_alerts = []
    if is_admin:
        late_night_txs = GiaoDich.objects.filter(loai='CHI', ngay_tao__hour__gte=23) | GiaoDich.objects.filter(loai='CHI', ngay_tao__hour__lte=5)
        if late_night_txs.exists():
            ai_alerts.append({'type': 'danger', 'title': 'Cảnh báo khung giờ nhạy cảm', 'desc': f'Có {late_night_txs.count()} khoản chi được tạo vào ban đêm.'})
        
        today_chi_count = GiaoDich.objects.filter(loai='CHI', ngay_tao__date=now.date()).count()
        if today_chi_count >= 3:
            ai_alerts.append({'type': 'warning', 'title': 'Phát hiện chia nhỏ chi tiêu', 'desc': f'Đã có {today_chi_count} khoản chi trong hôm nay.'})
        
    top_dai_gia = ThanhVien.objects.annotate(tong_nop=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU', giaodich__da_xac_nhan=True))).order_by('-tong_nop')[:5]

    # ... giữ nguyên đoạn tính quy_nh, quy_tm và muc_tieu_quy của sếp ...
# ==========================================
    # TÍNH TOÁN SỐ DƯ CHI TIẾT (Fix NameError & Logic Xác nhận)
    # ==========================================
    # 1. Khởi tạo giá trị mặc định để tránh lỗi 'not defined'
    so_du_bank = "0"
    so_du_cash = "0"

    # 2. Tính toán cho Quỹ Ngân Hàng
    quy_nh = LoaiQuy.objects.filter(ten_quy__icontains="Ngân hàng").first()
    if quy_nh:
        # Chỉ tính các giao dịch ĐÃ XÁC NHẬN (da_xac_nhan=True)
        thu_nh = base_gd.filter(loai_quy=quy_nh, loai__in=['THU', 'LAI', 'HU'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        chi_nh = base_gd.filter(loai_quy=quy_nh, loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        so_du_bank = format_money(thu_nh - chi_nh)

    # 3. Tính toán cho Quỹ Tiền Mặt
    quy_tm = LoaiQuy.objects.filter(ten_quy__icontains="Tiền mặt").first()
    if quy_tm:
        # Chỉ tính các giao dịch ĐÃ XÁC NHẬN (da_xac_nhan=True)
        thu_tm = base_gd.filter(loai_quy=quy_tm, loai__in=['THU', 'LAI', 'HU'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        chi_tm = base_gd.filter(loai_quy=quy_tm, loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        so_du_cash = format_money(thu_tm - chi_tm)
    
    # 4. Tính toán mục tiêu quỹ (Giữ nguyên logic loop của sếp)
    muc_tieu_quy = list(MucTieuQuy.objects.filter(hoan_thanh=False)[:5])
    danh_sach_muc_tieu = []
    # ... (tiếp tục đoạn loop for mt in muc_tieu_quy của sếp bên dưới)
    context = {
        'giao_dich_cho_duyet': giao_dich_cho_duyet, # TRUYỀN BIẾN MỚI
        'so_du': format_money(so_du_raw),
        'so_du_bank': so_du_bank, 'so_du_cash': so_du_cash,   
        'danh_sach_no_xau': danh_sach_no_xau,
        'thu_nay': format_money(thu_thang_nay), 'chi_nay': format_money(chi_thang_nay),
        'thu_percent': thu_percent, 'chi_percent': chi_percent,
        'tai_san': TaiSan.objects.all().order_by('-ngay_mua')[:3],
        'thanh_viens': ThanhVien.objects.all().order_by('ho_ten'),
        'giao_dich_moi': giao_dich_moi,
        'muc_tieu_quy': danh_sach_muc_tieu, 
        'su_kien_nhac_viec': SuKienNhacViec.objects.filter(ngay_dien_ra__gte=now.date())[:4],
        'chart_months': json.dumps(chart_months), 'chart_thu': json.dumps(chart_thu), 'chart_chi': json.dumps(chart_chi),
        'is_admin': is_admin, 'user_role_name': user_role_name, 'ai_alerts': ai_alerts, 'top_dai_gia': top_dai_gia,
        'is_thanh_hut': so_du_raw < 0,
    }
    return render(request, 'quanlyquy/dashboard.html', context)


# ==========================================
# 4. CÁC TRANG CHỨC NĂNG CHÍNH (ĐÃ PHÂN QUYỀN)
# ==========================================
@login_required
def giao_dich_view(request):
    check_and_reward_quest(request, 'Kế toán mẫn cán')
    is_admin = is_thu_quy(request.user)
    tv = ThanhVien.objects.filter(user=request.user).first()
    
    # 🔒 PHÂN QUYỀN BẢNG GIAO DỊCH
    if is_admin:
        giao_dich_list_raw = GiaoDich.objects.all().select_related('thanh_vien').order_by('-ngay_tao')
    else:
        giao_dich_list_raw = GiaoDich.objects.filter(thanh_vien=tv).select_related('thanh_vien').order_by('-ngay_tao') if tv else GiaoDich.objects.none()

    q = request.GET.get('search', '').strip()
    tx_type = request.GET.get('type', '')

    if q:
        search_condition = Q(ly_do__icontains=q) | (
            Q(is_an_danh=False) & (Q(thanh_vien__ho_ten__icontains=q) | Q(thanh_vien__mssv__icontains=q))
        )
        if "hảo tâm" in q.lower() or "ẩn danh" in q.lower():
            search_condition |= Q(is_an_danh=True)
        giao_dich_list_raw = giao_dich_list_raw.filter(search_condition)

    if tx_type == 'THU':
        giao_dich_list_raw = giao_dich_list_raw.filter(loai__in=['THU', 'LAI', 'HU'])
    elif tx_type == 'CHI':
        giao_dich_list_raw = giao_dich_list_raw.filter(loai__in=['CHI', 'TU'])

    for gd in giao_dich_list_raw:
        gd.so_tien_format = format_money(gd.so_tien)

    paginator = Paginator(giao_dich_list_raw, 10) 
    page_number = request.GET.get('page')
    giao_dich_list = paginator.get_page(page_number)

    return render(request, 'quanlyquy/page_giao_dich.html', {
        'giao_dich_list': giao_dich_list,
        'search_query': q,
        'current_type': tx_type,
        'is_admin': is_admin
    })

@login_required
def thong_ke_view(request):
    check_and_reward_quest(request, 'Chuyên gia phân tích')
    is_admin = is_thu_quy(request.user)
    tv = ThanhVien.objects.filter(user=request.user).first()
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"

    # 🔒 PHÂN QUYỀN BIỂU ĐỒ THỐNG KÊ
    base_gd = GiaoDich.objects.all() if is_admin else (GiaoDich.objects.filter(thanh_vien=tv) if tv else GiaoDich.objects.none())

    stats = base_gd.annotate(m=TruncMonth('ngay_tao')).values('m').annotate(
        thu=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
        chi=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
    ).order_by('m')
    
    last_6_stats = list(stats)[-6:]
    c1_labels = [s['m'].strftime("Th %m/%y") for s in last_6_stats if s['m']]
    c1_thu = [float(s['thu'] or 0) for s in last_6_stats]
    c1_chi = [float(s['chi'] or 0) for s in last_6_stats]

    chi_tieu_db = base_gd.filter(loai__in=['CHI', 'TU']).values('danh_muc__ten_danh_muc').annotate(
        tong=Sum('so_tien')).order_by('-tong')[:5]
    c2_labels = [item['danh_muc__ten_danh_muc'] or "Khác" for item in chi_tieu_db]
    c2_data = [float(item['tong'] or 0) for item in chi_tieu_db]

    top_members = ThanhVien.objects.annotate(
        tong=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU', giaodich__is_an_danh=False))
    ).filter(tong__gt=0).order_by('-tong')[:5]
    c3_labels = [m.ho_ten for m in top_members]
    c3_data = [float(m.tong or 0) for m in top_members]

    dot_thu_list = DotThu.objects.all().order_by('-id')[:4]
    tong_tv = ThanhVien.objects.count()
    c4_labels = []; c4_dathu = []; c4_no = []
    for dt in dot_thu_list:
        c4_labels.append(dt.ten_dot)
        da_thu = float(base_gd.filter(dot_thu=dt, loai='THU').aggregate(Sum('so_tien'))['so_tien__sum'] or 0)
        tong_phai_thu = float(dt.so_tien_moi_nguoi * (tong_tv if is_admin else 1)) # Cân đối cá nhân/tập thể
        c4_dathu.append(da_thu)
        c4_no.append(max(0, tong_phai_thu - da_thu))

    quys = LoaiQuy.objects.all()
    c5_labels = [q.ten_quy for q in quys]
    c5_data = [float(q.so_du_hien_tai or 0) for q in quys]

    context = {
        'chart1_labels': json.dumps(c1_labels),
        'chart1_thu': json.dumps(c1_thu),
        'chart1_chi': json.dumps(c1_chi),
        'chart2_labels': json.dumps(c2_labels),
        'chart2_data': json.dumps(c2_data),
        'chart3_labels': json.dumps(c3_labels),
        'chart3_data': json.dumps(c3_data),
        'chart4_labels': json.dumps(c4_labels),
        'chart4_dathu': json.dumps(c4_dathu),
        'chart4_no': json.dumps(c4_no),
        'chart5_labels': json.dumps(c5_labels),
        'chart5_data': json.dumps(c5_data),
        'is_admin': is_admin,
        'user_role_name': user_role_name,
    }
    return render(request, 'quanlyquy/thong_ke.html', context)

@login_required
def tien_do_thu_view(request):
    check_and_reward_quest(request, 'Kiểm tra nợ nần')
    is_admin = is_thu_quy(request.user)
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"
    tv_me = ThanhVien.objects.filter(user=request.user).first()

    danh_sach_dot_thu = DotThu.objects.order_by('-created_at')
    dot_thu_id = request.GET.get('dot_thu_id') 
    
    if dot_thu_id:
        dot_thu = DotThu.objects.filter(id=dot_thu_id).first()
    else:
        dot_thu = danh_sach_dot_thu.first() 

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all') 

    # 🔥 FIX 1: TÍNH MỤC TIÊU DỰA TRÊN TỔNG THỂ LỚP (Bất kể Admin hay Thành viên)
    tat_ca_tv_chung = ThanhVien.objects.filter(deleted_at__isnull=True)
    dinh_muc = dot_thu.so_tien_moi_nguoi if dot_thu else 0
    total_needed = dinh_muc * tat_ca_tv_chung.count() # Mục tiêu 4tr2 sẽ hiện chuẩn
    total_collected = GiaoDich.objects.filter(dot_thu=dot_thu, loai__in=['THU', 'LAI']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0

    # 🔒 PHÂN QUYỀN BẢNG BÊN DƯỚI (Ai thấy danh sách người đó)
    if is_admin:
        tat_ca_tv_bang = tat_ca_tv_chung
    else:
        tat_ca_tv_bang = ThanhVien.objects.filter(id=tv_me.id) if tv_me else ThanhVien.objects.none()

    thanh_vien_stats_raw = []
    danh_sach_no = []
    total_actual_owe_raw = 0  
    my_status = False
    search_query_lower = search_query.lower()

    # Vòng lặp duyệt qua danh sách đã được phân quyền
    for tv in tat_ca_tv_bang:
        da_nop = GiaoDich.objects.filter(thanh_vien=tv, dot_thu=dot_thu, loai__in=['THU', 'LAI']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        
        is_hoan_thanh = da_nop >= dinh_muc
        is_no_xau = da_nop < dinh_muc
        is_me = (tv.user == request.user) or (tv.mssv == getattr(request.user, 'mssv', None)) or (tv.email == request.user.email)
        
        if is_me and is_hoan_thanh: 
            my_status = True

        if is_no_xau: 
            tien_no = dinh_muc - da_nop
            total_actual_owe_raw += tien_no 
            danh_sach_no.append({
                'id': tv.id, 'ho_ten': tv.ho_ten, 'mssv': tv.mssv, 'is_no_xau': True
            })

        if search_query:
            if search_query_lower not in tv.ho_ten.lower() and search_query_lower not in str(tv.mssv).lower():
                continue

        if status_filter == 'completed' and not is_hoan_thanh: continue
        if status_filter == 'debt' and not is_no_xau: continue

        thanh_vien_stats_raw.append({
            'id': tv.id, 'ho_ten': tv.ho_ten, 'mssv': tv.mssv,
            'so_tien_da_dong': format_money(da_nop),
            'so_tien_dinh_muc': format_money(dinh_muc), 
            'is_hoan_thanh': is_hoan_thanh, 'is_no_xau': is_no_xau, 'is_me': is_me
        })

    paginator = Paginator(thanh_vien_stats_raw, 10) 
    page_number = request.GET.get('page', 1)

    try:
        thanh_vien_stats = paginator.page(page_number)
    except PageNotAnInteger:
        thanh_vien_stats = paginator.page(1)
    except EmptyPage:
        thanh_vien_stats = paginator.page(paginator.num_pages)

    percent = int((total_collected / total_needed * 100)) if total_needed > 0 else 0
    
    try:
        thong_bao_buu_ta = ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user).order_by('-created_at')[:20]
        unread_notif_count = ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user, is_read=False).count()
    except:
        thong_bao_buu_ta = []
        unread_notif_count = 0

    context = {
        'is_admin': is_admin,
        'user_role_name': user_role_name,
        'dot_thu': dot_thu,
        'danh_sach_dot_thu': danh_sach_dot_thu, 
        'total_needed': format_money(total_needed),
        'total_collected': format_money(total_collected),
        'total_remaining': format_money(total_actual_owe_raw),
        'percent': percent,
        'remaining_percent': max(0, 100 - percent),
        'thanh_vien_stats': thanh_vien_stats,
        'search_query': search_query,
        'current_status': status_filter, 
        'my_status': my_status,
        'debt_count': len(danh_sach_no),
        'danh_sach_no': danh_sach_no,
        'unread_notif_count': unread_notif_count,
        'thong_bao_buu_ta': thong_bao_buu_ta, 
        'deadline': dot_thu.han_chot.strftime("%d/%m/%Y") if dot_thu and dot_thu.han_chot else "Chưa đặt",
        'current_tv_id': tv_me.id if tv_me else '',
    }
    return render(request, 'quanlyquy/page_tien_do.html', context)

@login_required
@user_passes_test(is_thu_quy, login_url='/')
def cai_dat_view(request):
    return render(request, 'quanlyquy/page_cai_dat.html', {'is_admin': True})

@login_required
def gamification_view(request):
    check_and_reward_quest(request, 'Khám phá Khu Vui Chơi')
    is_admin = is_thu_quy(request.user)
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"

    my_tv = ThanhVien.objects.filter(user=request.user).first()
    if not my_tv:
        mssv_user = getattr(request.user, 'mssv', '')
        if mssv_user: my_tv = ThanhVien.objects.filter(mssv=mssv_user).first()
    if not my_tv:
        email_user = getattr(request.user, 'email', '')
        if email_user: my_tv = ThanhVien.objects.filter(email=email_user).first()
        
    vi_xu = getattr(my_tv, 'vi_xu', 0) if my_tv else getattr(request.user, 'credit_score', 0)

    today = timezone.now().date()
    completed_quest_ids = []
    if my_tv:
        completed_quest_ids = list(LichSuGiaoDichXu.objects.filter(
            thanh_vien=my_tv, 
            loai_giao_dich='CONG_XU', 
            nhiem_vu_lien_quan__isnull=False,
            ngay_thuc_hien__date=today 
        ).values_list('nhiem_vu_lien_quan_id', flat=True))

    lich_su_xu = LichSuGiaoDichXu.objects.filter(thanh_vien=my_tv).order_by('-ngay_thuc_hien')[:20] if my_tv else []
    voted_poll_ids = []
    if my_tv:
        for log in lich_su_xu:
            if log.ly_do.startswith("Vote khảo sát ID:"):
                try: voted_poll_ids.append(int(log.ly_do.split(':')[1]))
                except: pass
    
    nhiem_vu_list = NhiemVu.objects.filter(is_active=True).order_by('id')
    bieu_quyet_active = BieuQuyet.objects.filter(dang_mo=True)
    cua_hang_items = QuaTang.objects.filter(is_active=True)[:3]
    
    top_dai_gia_raw = ThanhVien.objects.annotate(
        tong_tien_that=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU', giaodich__is_an_danh=False))
    ).filter(tong_tien_that__gt=0).order_by('-tong_tien_that')[:5]
    
    top_dai_gia = []
    for tv in top_dai_gia_raw:
        tv.diem_cong_hien = int((tv.tong_tien_that or 0) / 1000)
        huy_hieus = HuyHieuThanhVien.objects.filter(thanh_vien=tv).select_related('huy_hieu')[:3]
        tv.danh_sach_huy_hieu = [hh.huy_hieu for hh in huy_hieus]
        top_dai_gia.append(tv)

    bieu_quyet_active = BieuQuyet.objects.filter(dang_mo=True).prefetch_related('cac_phuong_an')
    for poll in bieu_quyet_active:
        tong_vote = 0
        # Vòng 1: Đếm lại lượt vote THẬT của từng phương án
        for pa in poll.cac_phuong_an.all():
            so_vote_that = ChiTietBinhChon.objects.filter(phuong_an=pa).count()
            pa.luot_chon = so_vote_that # Ghi đè vào biến tạm để HTML hiển thị số mới nhất
            tong_vote += so_vote_that
            
        poll.tong_vote = tong_vote
        
        # Vòng 2: Tính % chuẩn dựa trên tổng mới
        for pa in poll.cac_phuong_an.all():
            pa.phan_tram = int((pa.luot_chon / tong_vote) * 100) if tong_vote > 0 else 0
            if is_admin:
                pa.danh_sach_nguoi_vote = ChiTietBinhChon.objects.filter(phuong_an=pa).select_related('thanh_vien')

    context = {
        'nhiem_vu_list': nhiem_vu_list,
        'completed_quest_ids': completed_quest_ids, 
        'bieu_quyet_active': bieu_quyet_active,
        'cua_hang_items': cua_hang_items,
        'top_dai_gia': top_dai_gia,
        'is_admin': is_admin,
        'voted_poll_ids': voted_poll_ids,
        'lich_su_xu': lich_su_xu,
        'user_role_name': user_role_name,
        'vi_xu': vi_xu,
        'has_vong_quay': True,
        'days_left': 5
    }
    return render(request, 'quanlyquy/gamification.html', context)

@login_required
def export_misa_view(request):
    is_admin = getattr(request.user, 'role', '') == 'ADMIN' or request.user.is_superuser
    if not is_admin:
        return HttpResponse("Bạn không có quyền thực hiện thao tác này.", status=403)

    giao_dich_list = GiaoDich.objects.all().order_by('-ngay_tao')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="SaoKe_QuyLop_MISA_FundFlow.csv"'
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response)
    writer.writerow(['Ngày hạch toán', 'Ngày chứng từ', 'Số chứng từ', 'Diễn giải', 'Tài khoản Nợ', 'Tài khoản Có', 'Số tiền', 'Đối tượng', 'Loại giao dịch'])

    for gd in giao_dich_list:
        tk_no = "1111"
        tk_co = "1111"
        if gd.loai in ['THU', 'LAI']:
            tk_no = "1111"
            tk_co = "511" 
        elif gd.loai in ['CHI', 'TU']:
            tk_no = "811"
            tk_co = "1111"

        is_an_danh = getattr(gd, 'is_an_danh', False)
        ten_nguoi_nop = "Nhà hảo tâm ẩn danh" if is_an_danh else (gd.thanh_vien.ho_ten if gd.thanh_vien else "Hệ thống")
        
        writer.writerow([
            gd.ngay_tao.strftime("%d/%m/%Y"), gd.ngay_tao.strftime("%d/%m/%Y"), 
            f"FF-{gd.id:05d}", gd.ly_do, tk_no, tk_co, gd.so_tien, ten_nguoi_nop, gd.get_loai_display()
        ])
    return response

@login_required
def settings_view(request):
    is_admin = getattr(request.user, 'role', '') == 'ADMIN' or request.user.is_superuser
    if not is_admin: return redirect('/') 
    return render(request, 'quanlyquy/settings.html', {'is_admin': is_admin, 'user_role_name': "Thủ quỹ hệ thống"})

@login_required
def qa_testing_view(request):
    is_admin = getattr(request.user, 'role', '') == 'ADMIN' or request.user.is_superuser
    if not is_admin: return redirect('/')
    return render(request, 'quanlyquy/qa_testing.html', {'is_admin': is_admin, 'user_role_name': "Thủ quỹ hệ thống"})

@login_required
def store_view(request):
    # Lấy thông tin thành viên khớp với user đang đăng nhập
    my_tv = ThanhVien.objects.filter(user=request.user).first()
    
    # Ưu tiên lấy xu từ bảng ThanhVien (371 xu)
    vi_xu = my_tv.vi_xu if my_tv else 0
    
    is_admin = is_thu_quy(request.user)
    items = QuaTang.objects.all()
    
    context = {
        'items': items,
        'vi_xu': vi_xu,  # Truyền biến vi_xu chuẩn vào context
        'is_admin': is_admin,
        'user_role_name': "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp" 
    }
    check_and_reward_quest(request, 'Window Shopping')
    return render(request, 'quanlyquy/store.html', context)

# ==========================================
# 5. API XỬ LÝ DỮ LIỆU BẰNG AJAX
# ==========================================
@csrf_exempt
def api_chaos_action(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user = request.user if request.user.is_authenticated else None

        if action == 'SEED_QUESTS':
            NhiemVu.objects.all().delete() 
            quests = [
                ("Chăm chỉ điểm danh", "Đăng nhập và xem trang Tổng quan", 5, 'AUTO_TUONG_TAC'),
                ("Khám phá Khu Vui Chơi", "Ghé thăm Trạm Giải Trí FundSmart", 5, 'AUTO_TUONG_TAC'),
                ("Kế toán mẫn cán", "Tra cứu danh sách giao dịch", 10, 'AUTO_TUONG_TAC'),
                ("Chuyên gia phân tích", "Vào xem biểu đồ dòng tiền", 10, 'AUTO_TUONG_TAC'),
                ("Kiểm tra nợ nần", "Vào xem tiến độ đóng quỹ", 10, 'AUTO_TUONG_TAC'),
                ("Window Shopping", "Ghé thăm Cửa hàng đặc quyền", 5, 'AUTO_TUONG_TAC'),
                ("Lời chào tới FundBot", "Nhắn tin tương tác với Trợ lý AI", 15, 'AUTO_TUONG_TAC'),
                ("Tiếng nói cử tri", "Tham gia vote một Khảo sát bất kỳ", 20, 'AUTO_TUONG_TAC'),
                ("Công dân gương mẫu", "Hoàn thành tự nộp quỹ lớp", 30, 'AUTO_NOP_QUY'),
                ("Đại gia bao nuôi", "Nộp quỹ hộ cho một thành viên khác", 50, 'AUTO_NOP_QUY'),
                ("Con nghiện Gacha", "Chơi vòng quay ít nhất 1 lần", 10, 'AUTO_TUONG_TAC'),
            ]
            for q in quests:
                NhiemVu.objects.create(ten_nhiem_vu=q[0], mo_ta=q[1], phan_thuong_xu=q[2], loai_nhiem_vu=q[3], is_active=True)
            return JsonResponse({"status": "success", "message": "Đã reset và tạo 10 Quest chuẩn mực!"})

        if action == 'TIMEOUT_504':
            time.sleep(1.5)
            QATestingLog.objects.create(
                nguoi_test=user,
                loai_test="ROT_MANG_BANK",
                du_lieu_phat_sinh={"error": "504 Gateway Timeout", "rollback_id": f"RB-{random.randint(1000, 9999)}"},
                trang_thai="ROLLBACK_SUCCESS"
            )
            return JsonResponse({"status": "error", "message": "[FATAL] Lỗi 504 Gateway Timeout kết nối Ngân Hàng.<br>[SYS] Rollback transaction initiated...<br>[SUCCESS] DB Rollback thành công, không mất tiền."})

        elif action == 'SEED_DATA':
            try:
                quy = LoaiQuy.objects.first()
                if quy:
                    GiaoDich.objects.bulk_create([
                        GiaoDich(loai='THU', so_tien=random.randint(10, 50)*1000, loai_quy=quy, ly_do=f"Auto Seed Data #{i}", is_an_danh=True)
                        for i in range(50)
                    ])
                    QATestingLog.objects.create(
                        nguoi_test=user, loai_test="STRESS_TEST_DB",
                        du_lieu_phat_sinh={"records_inserted": 50, "table": "GiaoDich"},
                        trang_thai="SUCCESS"
                    )
                    return JsonResponse({"status": "warn", "message": "[WORKING] Seeding data...<br>[SUCCESS] Đã bơm 50 giao dịch ảo vào Database thành công! Hãy check trang Tổng quan."})
                else:
                    return JsonResponse({"status": "error", "message": "[ERROR] Không tìm thấy Quỹ nào để bơm dữ liệu. Vui lòng tạo Quỹ trước."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"[ERROR] Bơm dữ liệu thất bại: {str(e)}"})

        elif action == 'RATE_LIMIT':
            QATestingLog.objects.create(
                nguoi_test=user, loai_test="DDOS_ATTACK",
                du_lieu_phat_sinh={"requests_per_sec": 500, "ip_blocked": "192.168.1.100"},
                trang_thai="BLOCKED"
            )
            return JsonResponse({"status": "info", "message": "[ALERT] Phát hiện lưu lượng bất thường: 500 req/s.<br>[SECURITY] Kích hoạt Firewall. Đã block IP tấn công."})

    return JsonResponse({"status": "error", "message": "Invalid request"})

# ==========================================
# 6. API WEBHOOK NGÂN HÀNG (TỰ ĐỘNG GẠCH NỢ)
# ==========================================
@csrf_exempt
def sepay_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            ma_gd = data.get('id', '') 
            so_tien = data.get('transferAmount', 0)
            noi_dung_ck = data.get('content', '').upper() 

            webhook_log = LichSuWebhook.objects.create(
                ma_giao_dich_ngan_hang=str(ma_gd),
                so_tien=so_tien,
                raw_payload=data,
                trang_thai_xu_ly=False
            )

            thanh_vien_nhan_dien = None
            danh_sach_tv = ThanhVien.objects.filter(deleted_at__isnull=True)
            
            for tv in danh_sach_tv:
                if tv.mssv and tv.mssv.upper() in noi_dung_ck:
                    thanh_vien_nhan_dien = tv
                    break
            
            quy_mac_dinh = LoaiQuy.objects.filter(deleted_at__isnull=True).first()

            if thanh_vien_nhan_dien and quy_mac_dinh:
                GiaoDich.objects.create(
                    loai='THU',
                    so_tien=so_tien,
                    loai_quy=quy_mac_dinh,
                    thanh_vien=thanh_vien_nhan_dien,
                    ly_do=f"[AUTO] CK qua Bank: {noi_dung_ck}",
                    is_an_danh=False
                )
                webhook_log.trang_thai_xu_ly = True
                webhook_log.save()
                
                return JsonResponse({"status": "success", "message": f"Đã gạch nợ tự động cho {thanh_vien_nhan_dien.ho_ten}"})
            
            return JsonResponse({"status": "skipped", "message": "Giao dịch lưu thành công nhưng không tìm thấy MSSV hợp lệ"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Lỗi hệ thống: {str(e)}"}, status=500)
            
    return JsonResponse({"status": "invalid_method", "message": "Chỉ nhận phương thức POST"}, status=405)

@login_required
def api_mass_remind_debt(request):
    if not is_thu_quy(request.user):
        return JsonResponse({'status': 'error', 'message': 'Lệnh này chỉ thủ quỹ mới được dùng!'})
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ nhận lệnh POST!'})

    dot_thu_id = request.POST.get('dot_thu_id')
    dot_thu = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else DotThu.objects.order_by('-created_at').first()
    
    if not dot_thu:
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy đợt thu này!'})

    dinh_muc = dot_thu.so_tien_moi_nguoi
    tat_ca_tv = ThanhVien.objects.filter(deleted_at__isnull=True).select_related('user')
    
    count_notified = 0
    
    with transaction.atomic():
        for tv in tat_ca_tv:
            da_nop = GiaoDich.objects.filter(thanh_vien=tv, dot_thu=dot_thu, loai__in=['THU', 'LAI']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
            
            if da_nop < dinh_muc: 
                if tv.user: 
                    xung_ho = "sếp" if is_thu_quy(tv.user) else "bạn"
                    tieu_de = f"📣 Nhắc nợ gấp đợt: {dot_thu.ten_dot}"
                    noi_dung = f"{xung_ho.capitalize()} ơi! Gấp gấp! Số xu đóng quỹ {format_money(dinh_muc - da_nop)}đ cho đợt '{dot_thu.ten_dot}' chưa đóng. Đóng quỹ liền tay nhé sếp!"
                    
                    ThongBaoBuuTa.objects.create(
                        nguoi_nhan=tv.user, tieu_de=tieu_de, noi_dung=noi_dung, 
                        loai=ThongBaoBuuTa.Type.REMIND, link_url='/tien-do/'
                    )
                    count_notified += 1

    return JsonResponse({'status': 'success', 'message': f'Đã băm lệnh, bắn {count_notified} bản tin nhắc nợ đến hòm thư, nổ chuông toàn bộ người nợ thành công! 🚀'})

@login_required
def api_clear_notifications(request):
    if request.method == 'POST':
        from .models import ThongBaoBuuTa
        ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user).delete()
        return JsonResponse({'status': 'success', 'message': 'Đã dọn sạch hộp thư!'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})
# ==========================================
# . API DOI Quà
# ==========================================
@login_required
@csrf_exempt
def api_doi_qua(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_name = data.get('item_name')
            item_price = int(data.get('item_price'))
            
            tv = ThanhVien.objects.filter(user=request.user).first()
            if not tv or tv.vi_xu < item_price:
                return JsonResponse({'status': 'error', 'message': 'Không đủ xu hoặc lỗi hồ sơ!'})
            
            # Thực hiện trừ xu
            tv.vi_xu -= item_price
            tv.save()
            
            # Lưu lịch sử giao dịch xu
            LichSuGiaoDichXu.objects.create(
                thanh_vien=tv,
                loai_giao_dich='TRU_XU',
                so_xu=item_price,
                ly_do=f"Đổi quà: {item_name}",
                created_by=str(request.user.id)
            )
            
            return JsonResponse({'status': 'success', 'message': f'Đã đổi thành công {item_name}!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})
# ==========================================
# 6.kho  Quà
# ==========================================
@login_required
def kho_do_view(request):
    # Lấy thông tin thành viên
    tv = ThanhVien.objects.filter(user=request.user).first()
    
    # Lấy danh sách quà trong kho, phân loại theo trạng thái hoặc loại quà
    kho_do = KhoDoThanhVien.objects.filter(thanh_vien=tv).select_related('qua_tang').order_by('-ngay_doi')
    
    context = {
        'kho_do': kho_do,
        'is_admin': is_thu_quy(request.user),
    }
    return render(request, 'quanlyquy/kho_do.html', context)
@login_required
def tui_do_view(request):
    tv = ThanhVien.objects.filter(user=request.user).first()
    # Lấy danh sách quà sếp đã đổi
    kho_items = KhoDoThanhVien.objects.filter(thanh_vien=tv).select_related('qua_tang').order_by('-ngay_mua')
    
    context = {
        'kho_items': kho_items,
        'vi_xu': tv.vi_xu if tv else 0,
        'user_role_name': "Thủ quỹ" if is_thu_quy(request.user) else "Thành viên"
    }
    return render(request, 'quanlyquy/tui_do.html', context)
# ==========================================
# 7. API WEBHOOK NGÂN HÀNG (ĐỐI SOÁT TỰ ĐỘNG THEO ORDER_ID)
# ==========================================
@csrf_exempt  # Chặn lỗi bảo mật CSRF từ ứng dụng bên thứ 3 gọi vào
def banking_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Đọc cấu trúc gói tin nhận từ webhook ngân hàng (Casso hoặc PayOS)
            data_item = data.get('data', [{}])[0] if 'data' in data else data
            
            description = data_item.get('description', '')  # Nội dung chuyển khoản: "FUNDSMART12345"
            amount_paid = float(data_item.get('amount', 0)) # Số tiền thực tế nhận được
            
            if "FUNDSMART" in description:
                # Trích xuất mã giao dịch (Order ID) từ nội dung chuyển khoản
                order_id = description.split("FUNDSMART")[-1].strip()
                
                # Bọc trong transaction.atomic để bảo vệ an toàn dữ liệu, tránh ghi đè đồng thời
                with transaction.atomic():
                    # Tìm đúng giao dịch đang treo (da_xac_nhan=False) trong Sổ Giao Dịch của sếp
                    txn = GiaoDich.objects.select_for_update().get(order_id=order_id, da_xac_nhan=False)
                    
                    # Đối soát số tiền thực tế nhận được với hóa đơn hệ thống
                    if float(txn.so_tien) == amount_paid:
                        txn.da_xac_nhan = True
                        txn.phuong_thuc = 'BANK'  # Đổi sang thanh toán ngân hàng
                        txn.save()  # Khi save(), hàm tự động cập nhật tiến độ (Signal) của sếp sẽ tự chạy!
                        
                        return JsonResponse({'status': 'success', 'message': 'Đối soát tự động thành công, tiến độ đã cập nhật!'}, status=200)
                    else:
                        return JsonResponse({'status': 'error', 'message': 'Sai số tiền giao dịch!'}, status=400)
                        
        except GiaoDich.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy giao dịch hợp lệ hoặc giao dịch đã được xác nhận trước đó!'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)