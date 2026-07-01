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
from django.shortcuts import HttpResponseRedirect
from decimal import Decimal

# Gom tất cả Model vào 1 chỗ cho dễ quản lý
from .models import (
    GiaoDich, LichSuGiaoDichXu, ThanhVien, TaiSan, LoaiQuy, DotThu, 
    MucTieuQuy, SuKienNhacViec, User, QuaTang, 
    NhiemVu, BieuQuyet, HuyHieuThanhVien, QATestingLog, 
    LichSuWebhook, DanhMucThuChi, ThongBaoBuuTa, ChiTietBinhChon, KhoDoThanhVien, PhuongAnBieuQuyet
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
            user=request.user,
            ho_ten=request.user.full_name or request.user.username,
            mssv=getattr(request.user, 'mssv') or f"NEW-{request.user.id}",
            email=request.user.email
        )
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
# 3. TRANG CHỦ & DASHBOARD
# ==========================================
@login_required
def dashboard(request):
    check_and_reward_quest(request, 'Chăm chỉ điểm danh')
    try:
        kiem_tra_va_tu_dong_tru_no_quy(request.user)
    except Exception as e:
        print(f"Lỗi quét nợ tự động: {e}")
    now = timezone.now()
    thang_nay = now.month
    nam_nay = now.year
    first_day_this_month = now.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    thang_truoc = last_day_last_month.month
    nam_truoc = last_day_last_month.year

    is_admin = is_thu_quy(request.user)
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"
    
    tv = ThanhVien.objects.filter(user=request.user).first()
    if not tv and getattr(request.user, 'mssv', ''):
        tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
    if not tv and getattr(request.user, 'email', ''):
        tv = ThanhVien.objects.filter(email=request.user.email).first()
    if tv and not tv.user:
        tv.user = request.user
        tv.save()

    giao_dich_cho_duyet = []
    if is_admin:
        base_gd = GiaoDich.objects.all()
        danh_sach_no_xau = ThanhVien.objects.filter(is_no_xau=True)
        giao_dich_moi = GiaoDich.objects.all().select_related('thanh_vien').order_by('-ngay_tao')[:5]
        giao_dich_cho_duyet = GiaoDich.all_objects.filter(phuong_thuc='CASH', da_xac_nhan=False, loai='THU').select_related('thanh_vien').order_by('-created_at')
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
    so_du_thuc_te = thu_tong - chi_tong

    stats = (base_gd.annotate(month=TruncMonth('ngay_tao')).values('month').annotate(
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

    so_du_bank = "0"
    so_du_cash = "0"
    quy_nh = LoaiQuy.objects.filter(ten_quy__icontains="Ngân hàng").first()
    if quy_nh:
        thu_nh = base_gd.filter(loai_quy=quy_nh, loai__in=['THU', 'LAI', 'HU'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        chi_nh = base_gd.filter(loai_quy=quy_nh, loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        so_du_bank = format_money(thu_nh - chi_nh)

    quy_tm = LoaiQuy.objects.filter(ten_quy__icontains="Tiền mặt").first()
    if quy_tm:
        thu_tm = base_gd.filter(loai_quy=quy_tm, loai__in=['THU', 'LAI', 'HU'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        chi_tm = base_gd.filter(loai_quy=quy_tm, loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        so_du_cash = format_money(thu_tm - chi_tm)
    
    muc_tieu_quy = list(MucTieuQuy.objects.filter(hoan_thanh=False)[:5])
    danh_sach_muc_tieu = []
    for mt in muc_tieu_quy:
        tien_ht = getattr(mt, 'tien_hien_tai', getattr(mt, 'so_tien_hien_tai', 0)) or 0
        tien_mt = getattr(mt, 'tien_muc_tieu', getattr(mt, 'so_tien_muc_tieu', 0)) or 0
        phan_tram = int((tien_ht / tien_mt) * 100) if tien_mt > 0 else 0
        danh_sach_muc_tieu.append({
            'id': mt.id, 'ten_muc_tieu': mt.ten_muc_tieu,
            'tien_hien_tai_format': format_money(tien_ht),
            'tien_muc_tieu_format': format_money(tien_mt),
            'phan_tram_thuc': min(phan_tram, 100)
        })

    tv_hien_tai = ThanhVien.objects.filter(user=request.user).first()
    lop_target = tv_hien_tai.lop_hoc if tv_hien_tai else None
    if lop_target:
        danh_sach_quy_lop = LoaiQuy.objects.filter(lop_hoc=lop_target)
    else:
        danh_sach_quy_lop = LoaiQuy.objects.all()
    tong_tien_quy_lop_that = sum([q.so_du_hien_tai for q in danh_sach_quy_lop])

    context = {
        'giao_dich_cho_duyet': giao_dich_cho_duyet,
        'so_du': format_money(so_du_thuc_te),
        'so_du_thuc_te': format_money(so_du_thuc_te),
        'tong_tien_quy_lop_str': format_money(tong_tien_quy_lop_that),
        'so_du_vi_web': tv.so_du_vi_web if tv else 0,
        'so_du_bank': so_du_bank,
        'so_du_cash': so_du_cash,
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
        'is_thanh_hut': so_du_thuc_te < 0,
    }
    return render(request, 'quanlyquy/dashboard.html', context)

# ==========================================
# 4. CÁC TRANG CHỨC NĂNG CHÍNH
# ==========================================
@login_required
def giao_dich_view(request):
    check_and_reward_quest(request, 'Kế toán mẫn cán')
    is_admin = is_thu_quy(request.user)
    tv = ThanhVien.objects.filter(user=request.user).first()
    if not tv and getattr(request.user, 'mssv', ''):
        tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
    if not tv and getattr(request.user, 'email', ''):
        tv = ThanhVien.objects.filter(email=request.user.email).first()
    if tv and not tv.user:
        tv.user = request.user
        tv.save()
    
    if is_admin:
        giao_dich_list_raw = GiaoDich.objects.all().select_related('thanh_vien').order_by('-ngay_tao')
    else:
        giao_dich_list_raw = GiaoDich.objects.filter(thanh_vien=tv).select_related('thanh_vien').order_by('-ngay_tao') if tv else GiaoDich.objects.none()

    q = request.GET.get('search', '').strip()
    tx_type = request.GET.get('type', '')
    if q:
        search_condition = Q(ly_do__icontains=q) | (Q(is_an_danh=False) & (Q(thanh_vien__ho_ten__icontains=q) | Q(thanh_vien__mssv__icontains=q)))
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
    return render(request, 'quanlyquy/page_giao_dich.html', {'giao_dich_list': giao_dich_list, 'search_query': q, 'current_type': tx_type, 'is_admin': is_admin})

@login_required
def thong_ke_view(request):
    check_and_reward_quest(request, 'Chuyên gia phân tích')
    is_admin = is_thu_quy(request.user)
    tv = ThanhVien.objects.filter(user=request.user).first()
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"

    base_gd = GiaoDich.objects.all() if is_admin else (GiaoDich.objects.filter(thanh_vien=tv) if tv else GiaoDich.objects.none())
    stats = base_gd.annotate(m=TruncMonth('ngay_tao')).values('m').annotate(
        thu=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
        chi=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
    ).order_by('m')
    
    last_6_stats = list(stats)[-6:]
    c1_labels = [s['m'].strftime("Th %m/%y") for s in last_6_stats if s['m']]
    c1_thu = [float(s['thu'] or 0) for s in last_6_stats]
    c1_chi = [float(s['chi'] or 0) for s in last_6_stats]

    chi_tieu_db = base_gd.filter(loai__in=['CHI', 'TU']).values('danh_muc__ten_danh_muc').annotate(tong=Sum('so_tien')).order_by('-tong')[:5]
    c2_labels = [item['danh_muc__ten_danh_muc'] or "Khác" for item in chi_tieu_db]
    c2_data = [float(item['tong'] or 0) for item in chi_tieu_db]

    top_members = ThanhVien.objects.annotate(tong=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU', giaodich__is_an_danh=False))).filter(tong__gt=0).order_by('-tong')[:5]
    c3_labels = [m.ho_ten for m in top_members]
    c3_data = [float(m.tong or 0) for m in top_members]

    dot_thu_list = DotThu.objects.all().order_by('-id')[:4]
    tong_tv = ThanhVien.objects.count()
    c4_labels = []; c4_dathu = []; c4_no = []
    for dt in dot_thu_list:
        c4_labels.append(dt.ten_dot)
        da_thu = float(base_gd.filter(dot_thu=dt, loai='THU').aggregate(Sum('so_tien'))['so_tien__sum'] or 0)
        tong_phai_thu = float(dt.so_tien_moi_nguoi * (tong_tv if is_admin else 1))
        c4_dathu.append(da_thu)
        c4_no.append(max(0, tong_phai_thu - da_thu))

    quys = LoaiQuy.objects.all()
    c5_labels = [q.ten_quy for q in quys]
    c5_data = [float(q.so_du_hien_tai or 0) for q in quys]

    context = {
        'chart1_labels': json.dumps(c1_labels), 'chart1_thu': json.dumps(c1_thu), 'chart1_chi': json.dumps(c1_chi),
        'chart2_labels': json.dumps(c2_labels), 'chart2_data': json.dumps(c2_data),
        'chart3_labels': json.dumps(c3_labels), 'chart3_data': json.dumps(c3_data),
        'chart4_labels': json.dumps(c4_labels), 'chart4_dathu': json.dumps(c4_dathu), 'chart4_no': json.dumps(c4_no),
        'chart5_labels': json.dumps(c5_labels), 'chart5_data': json.dumps(c5_data),
        'is_admin': is_admin, 'user_role_name': user_role_name,
    }
    return render(request, 'quanlyquy/thong_ke.html', context)

@login_required
def tien_do_thu_view(request):
    """View hiển thị tiến độ đợt thu - ĐÃ FIX: Chặn hiển thị giao dịch Tiền mặt chưa duyệt"""
    check_and_reward_quest(request, 'Kiểm tra nợ nần')
    is_admin = is_thu_quy(request.user)
    
    tv_me = ThanhVien.objects.filter(user=request.user).first()
    if not tv_me and getattr(request.user, 'mssv', ''):
        tv_me = ThanhVien.objects.filter(mssv=request.user.mssv).first()
        if tv_me:
            tv_me.user = request.user
            tv_me.save()
    if not tv_me and getattr(request.user, 'email', ''):
        tv_me = ThanhVien.objects.filter(email=request.user.email).first()
        
    if not tv_me and not is_admin:
        tv_me = ThanhVien.objects.create(
            user=request.user, ho_ten=request.user.full_name or request.user.username,
            mssv=getattr(request.user, 'mssv', f"NEW-{request.user.id}"), email=request.user.email
        )
    if tv_me and not tv_me.user:
        tv_me.user = request.user
        tv_me.save()

    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"
    danh_sach_dot_thu = DotThu.objects.order_by('-created_at')
    dot_thu_id = request.GET.get('dot_thu_id') 
    dot_thu = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else danh_sach_dot_thu.first() 

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all') 

    tat_ca_tv_chung = ThanhVien.objects.filter(deleted_at__isnull=True)
    dinh_muc = dot_thu.so_tien_moi_nguoi if dot_thu else 0
    total_needed = dinh_muc * tat_ca_tv_chung.count()
    
    # 🌟 ĐÃ SỬA: Lọc chặt chẽ da_xac_nhan=True để không tính nhầm tiền mặt chờ duyệt vào KPI tổng
    total_collected = GiaoDich.objects.filter(dot_thu=dot_thu, loai__in=['THU', 'LAI'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0

    if is_admin:
        tat_ca_tv_bang = tat_ca_tv_chung
    else:
        tat_ca_tv_bang = ThanhVien.objects.filter(id=tv_me.id) if tv_me else ThanhVien.objects.none()

    thanh_vien_stats_raw = []
    danh_sach_no = []
    total_actual_owe_raw = 0  
    my_status = False
    search_query_lower = search_query.lower()

    for tv in tat_ca_tv_bang:
        # 🌟 ĐÃ SỬA: Lọc thêm da_xac_nhan=True khi tính số tiền thực tế từng người đã nộp
        da_nop = GiaoDich.objects.filter(thanh_vien=tv, dot_thu=dot_thu, loai__in=['THU', 'LAI'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        
        is_hoan_thanh = da_nop >= dinh_muc
        is_no_xau = da_nop < dinh_muc
        is_me = (tv.user == request.user) or (tv.mssv == getattr(request.user, 'mssv', None)) or (tv.email == request.user.email)
        
        if is_me and is_hoan_thanh: 
            my_status = True
        if is_no_xau: 
            tien_no = dinh_muc - da_nop
            total_actual_owe_raw += tien_no 
            danh_sach_no.append({'id': tv.id, 'ho_ten': tv.ho_ten, 'mssv': tv.mssv, 'is_no_xau': True})

        if search_query:
            if search_query_lower not in tv.ho_ten.lower() and search_query_lower not in str(tv.mssv).lower():
                continue

        if status_filter == 'completed' and not is_hoan_thanh: continue
        if status_filter == 'debt' and not is_no_xau: continue

        thanh_vien_stats_raw.append({
            'id': tv.id, 'ho_ten': tv.ho_ten, 'mssv': tv.mssv,
            'so_tien_da_dong': format_money(da_nop), 'so_tien_dinh_muc': format_money(dinh_muc), 
            'is_hoan_thanh': is_hoan_thanh, 'is_no_xau': is_no_xau, 'is_me': is_me
        })

    paginator = Paginator(thanh_vien_stats_raw, 10) 
    page_number = request.GET.get('page', 1)
    try:
        thanh_vien_stats = paginator.page(page_number)
    except:
        thanh_vien_stats = paginator.page(1)

    percent = int((total_collected / total_needed * 100)) if total_needed > 0 else 0
    try:
        thong_bao_buu_ta = ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user).order_by('-created_at')[:20]
        unread_notif_count = ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user, is_read=False).count()
    except:
        thong_bao_buu_ta = []; unread_notif_count = 0

    context = {
        'is_admin': is_admin, 'user_role_name': user_role_name, 'dot_thu': dot_thu, 'danh_sach_dot_thu': danh_sach_dot_thu, 
        'total_needed': format_money(total_needed), 'total_collected': format_money(total_collected), 'total_remaining': format_money(total_actual_owe_raw),
        'percent': percent, 'remaining_percent': max(0, 100 - percent), 'thanh_vien_stats': thanh_vien_stats,
        'search_query': search_query, 'current_status': status_filter, 'my_status': my_status,
        'debt_count': len(danh_sach_no), 'danh_sach_no': danh_sach_no, 'unread_notif_count': unread_notif_count, 'thong_bao_buu_ta': thong_bao_buu_ta, 
        'deadline': dot_thu.han_chot.strftime("%d/%m/%Y") if dot_thu and dot_thu.han_chot else "Chưa đặt", 'current_tv_id': tv_me.id if tv_me else '',
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
    if not my_tv and getattr(request.user, 'mssv', ''):
        my_tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
        
    vi_xu = getattr(my_tv, 'vi_xu', 0) if my_tv else getattr(request.user, 'credit_score', 0)
    today = timezone.now().date()
    completed_quest_ids = []
    if my_tv:
        completed_quest_ids = list(LichSuGiaoDichXu.objects.filter(thanh_vien=my_tv, loai_giao_dich='CONG_XU', nhiem_vu_lien_quan__isnull=False, ngay_thuc_hien__date=today).values_list('nhiem_vu_lien_quan_id', flat=True))

    lich_su_xu = LichSuGiaoDichXu.objects.filter(thanh_vien=my_tv).order_by('-ngay_thuc_hien')[:20] if my_tv else []
    voted_poll_ids = []
    for log in lich_su_xu:
        if log.ly_do.startswith("Vote khảo sát ID:"):
            try: voted_poll_ids.append(int(log.ly_do.split(':')[1]))
            except: pass
    
    nhiem_vu_list = NhiemVu.objects.filter(is_active=True).order_by('id')
    cua_hang_items = QuaTang.objects.filter(is_active=True)[:3]
    top_dai_gia_raw = ThanhVien.objects.annotate(tong_tien_that=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU', giaodich__is_an_danh=False))).filter(tong_tien_that__gt=0).order_by('-tong_tien_that')[:5]
    
    top_dai_gia = []
    for tv in top_dai_gia_raw:
        tv.diem_cong_hien = int((tv.tong_tien_that or 0) / 1000)
        huy_hieus = HuyHieuThanhVien.objects.filter(thanh_vien=tv).select_related('huy_hieu')[:3]
        tv.danh_sach_huy_hieu = [hh.huy_hieu for hh in huy_hieus]
        top_dai_gia.append(tv)

    if is_admin:
        bieu_quyet_active = BieuQuyet.objects.filter(dang_mo=True).prefetch_related('cac_phuong_an')
    else:
        bieu_quyet_active = BieuQuyet.objects.filter(dang_mo=True, loai_quy__lop_hoc=my_tv.lop_hoc if my_tv else None).prefetch_related('cac_phuong_an')

    for poll in bieu_quyet_active:
        tong_vote = 0
        for pa in poll.cac_phuong_an.all():
            so_vote_that = ChiTietBinhChon.objects.filter(phuong_an=pa).count()
            pa.luot_chon = so_vote_that 
            tong_vote += so_vote_that
        poll.tong_vote = tong_vote
        for pa in poll.cac_phuong_an.all():
            pa.phan_tram = int((pa.luot_chon / tong_vote) * 100) if tong_vote > 0 else 0
            if is_admin:
                pa.danh_sach_nguoi_vote = ChiTietBinhChon.objects.filter(phuong_an=pa).select_related('thanh_vien')

    context = {
        'nhiem_vu_list': nhiem_vu_list, 'completed_quest_ids': completed_quest_ids, 'bieu_quyet_active': bieu_quyet_active,
        'cua_hang_items': cua_hang_items, 'top_dai_gia': top_dai_gia, 'is_admin': is_admin, 'voted_poll_ids': voted_poll_ids,
        'lich_su_xu': lich_su_xu, 'user_role_name': user_role_name, 'vi_xu': vi_xu, 'has_vong_quay': True, 'days_left': 5
    }
    return render(request, 'quanlyquy/gamification.html', context)

@login_required
def export_misa_view(request):
    is_admin = getattr(request.user, 'role', '') == 'ADMIN' or request.user.is_superuser
    if not is_admin: return HttpResponse("Bạn không có quyền thực hiện thao tác này.", status=403)
    giao_dich_list = GiaoDich.objects.all().order_by('-ngay_tao')
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="SaoKe_QuyLop_MISA_FundFlow.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['Ngày hạch toán', 'Ngày chứng từ', 'Số chứng từ', 'Diễn giải', 'Tài khoản Nợ', 'Tài khoản Có', 'Số tiền', 'Đối tượng', 'Loại giao dịch'])
    for gd in giao_dich_list:
        tk_no = "1111"; tk_co = "1111"
        if gd.loai in ['THU', 'LAI']:
            tk_no = "1111"; tk_co = "511" 
        elif gd.loai in ['CHI', 'TU']:
            tk_no = "811"; tk_co = "1111"
        is_an_danh = getattr(gd, 'is_an_danh', False)
        ten_nguoi_nop = "Nhà hảo tâm ẩn danh" if is_an_danh else (gd.thanh_vien.ho_ten if gd.thanh_vien else "Hệ thống")
        writer.writerow([gd.ngay_tao.strftime("%d/%m/%Y"), gd.ngay_tao.strftime("%d/%m/%Y"), f"FF-{gd.id:05d}", gd.ly_do, tk_no, tk_co, gd.so_tien, ten_nguoi_nop, gd.get_loai_display()])
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
    my_tv = ThanhVien.objects.filter(user=request.user).first()
    vi_xu = my_tv.vi_xu if my_tv else 0
    is_admin = is_thu_quy(request.user)
    items = QuaTang.objects.all()
    context = {'items': items, 'vi_xu': vi_xu, 'is_admin': is_admin, 'user_role_name': "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"}
    check_and_reward_quest(request, 'Window Shopping')
    return render(request, 'quanlyquy/store.html', context)

# ==========================================
# 5. API ENDPOINTS CHỮA CHÁY
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
            QATestingLog.objects.create(nguoi_test=user, loai_test="ROT_MANG_BANK", du_lieu_phat_sinh={"error": "504 Gateway Timeout"}, trang_thai="ROLLBACK_SUCCESS")
            return JsonResponse({"status": "error", "message": "[FATAL] Lỗi 504 Gateway Timeout kết nối Ngân Hàng."})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@csrf_exempt
def sepay_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ma_gd = data.get('id', '') 
            so_tien = data.get('transferAmount', 0)
            noi_dung_ck = data.get('content', '').upper() 
            webhook_log = LichSuWebhook.objects.create(ma_giao_dich_ngan_hang=str(ma_gd), so_tien=so_tien, raw_payload=data, trang_thai_xu_ly=False)
            thanh_vien_nhan_dien = None
            danh_sach_tv = ThanhVien.objects.filter(deleted_at__isnull=True)
            for tv in danh_sach_tv:
                if tv.mssv and tv.mssv.upper() in noi_dung_ck:
                    thanh_vien_nhan_dien = tv
                    break
            quy_mac_dinh = LoaiQuy.objects.filter(deleted_at__isnull=True).first()
            if thanh_vien_nhan_dien and quy_mac_dinh:
                GiaoDich.objects.create(loai='THU', so_tien=so_tien, loai_quy=quy_mac_dinh, thanh_vien=thanh_vien_nhan_dien, ly_do=f"[AUTO] CK: {noi_dung_ck}", da_xac_nhan=True)
                webhook_log.trang_thai_xu_ly = True
                webhook_log.save()
                return JsonResponse({"status": "success", "message": f"Đã gạch nợ tự động cho {thanh_vien_nhan_dien.ho_ten}"})
            return JsonResponse({"status": "skipped", "message": "Không nhận diện được thành viên"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "invalid_method", "message": "POST only"}, status=405)

@login_required
def api_mass_remind_debt(request):
    if not is_thu_quy(request.user): return JsonResponse({'status': 'error', 'message': 'Chỉ admin mới có quyền!'})
    dot_thu_id = request.POST.get('dot_thu_id')
    dot_thu = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else DotThu.objects.order_by('-created_at').first()
    if not dot_thu: return JsonResponse({'status': 'error', 'message': 'Không tìm thấy đợt thu!'})
    dinh_muc = dot_thu.so_tien_moi_nguoi
    tat_ca_tv = ThanhVien.objects.filter(deleted_at__isnull=True)
    count_notified = 0
    with transaction.atomic():
        for tv in tat_ca_tv:
            da_nop = GiaoDich.objects.filter(thanh_vien=tv, dot_thu=dot_thu, loai__in=['THU', 'LAI']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
            if da_nop < dinh_muc:
                tiendo, _ = TienDoDongQuy.objects.get_or_create(dot_thu=dot_thu, thanh_vien=tv, defaults={'so_tien_can_nop': dinh_muc})
                tiendo.ngay_nhac_nho_gan_nhat = timezone.now()
                tiendo.save()
                if tv.user:
                    ThongBaoBuuTa.objects.create(nguoi_nhan=tv.user, tieu_de=f"📣 Nhắc nợ gấp đợt: {dot_thu.ten_dot}", noi_dung="Vui lòng hoàn tất đóng quỹ lớp.", loai=ThongBaoBuuTa.Type.REMIND, link_url='/tien-do/')
                    count_notified += 1
    return JsonResponse({'status': 'success', 'message': f'Đã bắn {count_notified} nhắc nợ!'})

@login_required
def api_clear_notifications(request):
    if request.method == 'POST':
        ThongBaoBuuTa.objects.filter(nguoi_nhan=request.user).delete()
        return JsonResponse({'status': 'success', 'message': 'Đã dọn sạch!'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
@csrf_exempt
def api_doi_qua(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_name = data.get('item_name')
            item_price = int(data.get('item_price'))
            tv = ThanhVien.objects.filter(user=request.user).first()
            if not tv or tv.vi_xu < item_price: return JsonResponse({'status': 'error', 'message': 'Không đủ xu!'})
            tv.vi_xu -= item_price
            tv.save()
            LichSuGiaoDichXu.objects.create(thanh_vien=tv, loai_giao_dich='TRU_XU', so_xu=item_price, ly_do=f"Đổi quà: {item_name}", created_by=str(request.user.id))
            return JsonResponse({'status': 'success', 'message': f'Đã đổi thành công {item_name}!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

@login_required
def tui_do_view(request):
    tv = ThanhVien.objects.filter(user=request.user).first()
    kho_items = KhoDoThanhVien.objects.filter(thanh_vien=tv).select_related('qua_tang').order_by('-ngay_mua')
    context = {'kho_items': kho_items, 'vi_xu': tv.vi_xu if tv else 0, 'user_role_name': "Thủ quỹ" if is_thu_quy(request.user) else "Thành viên"}
    return render(request, 'quanlyquy/tui_do.html', context)

@login_required
def theo_doi_dau_tu_view(request):
    if request.method == "POST":
        proposal_id = request.POST.get('proposal_id')
        choice_text = request.POST.get('choice')
        cuoc_vote = BieuQuyet.objects.filter(id=proposal_id).first()
        tv_hien_tai = ThanhVien.objects.filter(user=request.user).first()
        if cuoc_vote and tv_hien_tai:
            if ChiTietBinhChon.objects.filter(bieu_quyet=cuoc_vote, thanh_vien=tv_hien_tai).exists():
                messages.warning(request, "Bạn đã biểu quyết rồi !")
            else:
                phuong_an_obj = PhuongAnBieuQuyet.objects.filter(bieu_quyet=cuoc_vote, noi_dung__icontains=choice_text).first()
                if phuong_an_obj:
                    ChiTietBinhChon.objects.create(bieu_quyet=cuoc_vote, thanh_vien=tv_hien_tai, phuong_an=phuong_an_obj)
                    messages.success(request, "Biểu quyết thành công!")
                    tong_tv = ThanhVien.objects.filter(deleted_at__isnull=True).count()
                    tong_vote_dong_y = ChiTietBinhChon.objects.filter(bieu_quyet=cuoc_vote, phuong_an__noi_dung__icontains="Đồng ý").count()
                    if tong_tv > 0 and (tong_vote_dong_y / tong_tv) >= 0.75:
                        cuoc_vote.trang_thai_duyet = 'APPROVED'
                    cuoc_vote.save()
        return HttpResponseRedirect('/theo-doi-dau-tu/')

    tv_hien_tai = ThanhVien.objects.filter(user=request.user).first()
    lop_target = tv_hien_tai.lop_hoc if tv_hien_tai else None
    
    danh_sach_thanh_vien_lop = ThanhVien.objects.filter(lop_hoc=lop_target, deleted_at__isnull=True) if lop_target else ThanhVien.objects.none()
    tong_so_tv_lop = danh_sach_thanh_vien_lop.count()

    so_tien_goc = 0; lai_suat_nam = 4.8; ngay_bat_dau = timezone.now()
    ten_goi = "Không có dự án đầu tư nào"; so_tien_goc_uoc_tinh = 0; trang_thai_dau_tu = "CHUA_VOTE"
    ty_le_dong_y = 0; so_luong_dong_y = 0; danh_sach_vote = []; cuoc_vote = None; da_vote_roi = False
    
    ngay_ket_thuc_iso = ""
    ngay_ket_thuc_str = ""
    ngay_giai_ngan_str = ""

    if lop_target:
        cuoc_vote = BieuQuyet.objects.filter(lop_hoc=lop_target).order_by('-id').first()
        if not cuoc_vote:
            cuoc_vote = BieuQuyet.objects.filter(loai_quy__lop_hoc=lop_target).order_by('-id').first()
        
        if cuoc_vote:
            ten_goi = cuoc_vote.cau_hoi
            so_tien_goc_uoc_tinh = float(cuoc_vote.so_tien_dau_tu)
            da_vote_roi = ChiTietBinhChon.objects.filter(bieu_quyet=cuoc_vote, thanh_vien=tv_hien_tai).exists() if tv_hien_tai else False
            danh_sach_vote = ChiTietBinhChon.objects.filter(bieu_quyet=cuoc_vote).select_related('thanh_vien__user', 'phuong_an')
            so_luong_dong_y = ChiTietBinhChon.objects.filter(bieu_quyet=cuoc_vote, phuong_an__noi_dung__icontains="Đồng ý").count()
            
            if tong_so_tv_lop > 0: 
                ty_le_dong_y = round((so_luong_dong_y / tong_so_tv_lop) * 100, 1)
            
            if ty_le_dong_y >= 75.0:
                ngay_bat_dau = cuoc_vote.updated_at or ngay_bat_dau
                trang_thai_dau_tu = "DANG_DAU_TU"
                so_tien_goc = so_tien_goc_uoc_tinh
                
                # Lấy ngày kết thúc thật từ database (nếu chưa nhập thì mặc định tạm 7 ngày sau ngày bắt đầu để tránh crash)
                ngay_ket_thuc = cuoc_vote.ngay_ket_thuc_dau_tu or (ngay_bat_dau + timedelta(days=7))
                ngay_ket_thuc_iso = ngay_ket_thuc.isoformat()
                ngay_ket_thuc_str = ngay_ket_thuc.strftime("%d/%m/%Y %H:%M:%S")
                
                # Hạn kết toán và giải ngân (+2 ngày sau ngày kết thúc)
                ngay_giai_ngan = ngay_ket_thuc + timedelta(days=2)
                ngay_giai_ngan_str = ngay_giai_ngan.strftime("%d/%m/%Y %H:%M:%S")
                
                bay_gio = timezone.now()
                
                # 🔄 PHÂN LOẠI TRẠNG THÁI THEO TIMELINE THỰC TẾ
                if bay_gio < ngay_ket_thuc:
                    # Giai đoạn 1: Đang trong thời gian đầu tư sinh lãi
                    trang_thai_dau_tu = "DANG_DAU_TU"
                    
                elif ngay_ket_thuc <= bay_gio < ngay_giai_ngan:
                    # Giai đoạn 2: Đã kết thúc thời gian đầu tư, đang chờ 2 ngày đối soát giải ngân
                    trang_thai_dau_tu = "CHO_DOI_GIAI_NGAN"
                    
                elif bay_gio >= ngay_giai_ngan:
                    # Giai đoạn 3: Hết hạn 2 ngày -> Tự động xử lý giải ngân tiền về ví Web
                    if cuoc_vote.trang_thai_duyet == 'APPROVED':
                        with transaction.atomic():
                            # Tính tổng số tiền lãi cố định tại thời điểm kết thúc
                            thoi_gian_dau_tu_ms = (ngay_ket_thuc - ngay_bat_dau).total_seconds() * 1000
                            lai_mili_giay = (so_tien_goc_uoc_tinh * (lai_suat_nam / 100)) / (365 * 24 * 60 * 60 * 1000)
                            tong_lai_co_dinh = max(0, thoi_gian_dau_tu_ms * lai_mili_giay)
                            tong_so_tien_giai_ngan = so_tien_goc_uoc_tinh + tong_lai_co_dinh
                            
                            if tong_so_tv_lop > 0:
                                so_tien_chia_deu = Decimal(str(round(tong_so_tien_giai_ngan / tong_so_tv_lop, 2)))
                                
                                # Cộng tiền thực tế vào ví từng member
                                for member in danh_sach_thanh_vien_lop:
                                    member.so_du_vi_web = (member.so_du_vi_web or Decimal('0')) + so_tien_chia_deu
                                    member.save()
                                    
                                    if member.user:
                                        ThongBaoBuuTa.objects.create(
                                            nguoi_nhan=member.user,
                                            tieu_de="💰 Quỹ đầu tư đã giải ngân về ví!",
                                            noi_dung=f"Dự án '{cuoc_vote.cau_hoi}' đã hoàn tất đối soát 2 ngày sau đáo hạn. Bạn đã nhận lại {int(so_tien_chia_deu):,}đ (Gốc + Lãi) vào Ví Web.",
                                            loai='FINANCE'
                                        )
                            
                            # Cập nhật trạng thái để không bị lặp lại logic giải ngân ở lần truy cập sau
                            cuoc_vote.trang_thai_duyet = 'CONCLUDED'
                            cuoc_vote.save()
                            
                    trang_thai_dau_tu = "DA_GIAI_NGAN"
            else:
                trang_thai_dau_tu = "DANG_BIEU_QUYET"

    return render(request, 'quanlyquy/page_dau_tu.html', {
        'ten_goi': ten_goi, 'so_tien_goc': so_tien_goc, 'so_tien_goc_uoc_tinh': so_tien_goc_uoc_tinh, 'lai_suat_nam': lai_suat_nam,
        'ngay_bat_dau_iso': ngay_bat_dau.isoformat(), 'ngay_bat_dau_str': ngay_bat_dau.strftime("%d/%m/%Y %H:%M:%S"), 
        'ngay_ket_thuc_iso': ngay_ket_thuc_iso, 'ngay_ket_thuc_str': ngay_ket_thuc_str, 
        'ngay_giai_ngan_str': ngay_giai_ngan_str, 'trang_thai_dau_tu': trang_thai_dau_tu,
        'ty_le_dong_y': ty_le_dong_y, 'so_luong_dong_y': so_luong_dong_y, 'tong_so_tv_lop': tong_so_tv_lop, 
        'danh_sach_vote': danh_sach_vote, 'da_vote_roi': da_vote_roi, 'cuoc_vote': cuoc_vote,
    })
@login_required
@user_passes_test(is_thu_quy, login_url='/')
def giai_tan_quy_view(request, quy_id):
    """
    HÀM GIẢI TÁN QUỸ: Tính số dư hiện tại, chia đều và giải ngân 
    trực tiếp vào ví Web cho các thành viên trong lớp.
    """
    quy = get_object_or_404(LoaiQuy, id=quy_id)
    
    if quy.trang_thai_vong_doi == 'DISBANDED':
        messages.warning(request, f"Quỹ '{quy.ten_quy}' đã được giải tán từ trước rồi Bạn ơi!")
        return redirect('settings') # Hoặc trang quản lý quỹ của sếp

    lop_target = quy.lop_hoc
    if not lop_target:
        messages.error(request, "Quỹ này chưa được gán vào lớp nào nên hệ thống không biết chia tiền cho ai!")
        return redirect('settings')

    # 1. Lấy danh sách thành viên thực tế của lớp (bỏ qua những người đã xóa mềm)
    danh_sach_tv = ThanhVien.objects.filter(lop_hoc=lop_target, deleted_at__isnull=True)
    tong_so_tv = danh_sach_tv.count()

    if tong_so_tv == 0:
        messages.error(request, "Lớp học này hiện tại không có thành viên nào để nhận tiền tất toán!")
        return redirect('settings')

    # 2. Lấy số dư thực tế hiện tại của Quỹ (Tổng Thu - Tổng Chi)
    so_du_quy = quy.so_du_hien_tai

    if so_du_quy <= 0:
        # Nếu quỹ hết tiền hoặc âm, chỉ cần đóng trạng thái vòng đời
        quy.trang_thai_vong_doi = 'DISBANDED'
        quy.is_khoa_so = True
        quy.save()
        messages.success(request, f"Quỹ '{quy.ten_quy}' đã được giải tán thành công (Số dư quỹ bằng 0đ).")
        return redirect('settings')

    # 3. Tiến hành chia tiền và giải ngân đồng loạt bằng Transaction để chống lỗi mất mát dữ liệu
    try:
        with transaction.atomic():
            # Tính số tiền mỗi người nhận được (lấy chuẩn Decimal cho tài chính)
            so_tien_moi_nguoi = Decimal(str(round(float(so_du_quy) / tong_so_tv, 2)))

            for member in danh_sach_tv:
                # Cộng tiền thẳng vào số dư ví Web của sinh viên
                member.so_du_vi_web = (member.so_du_vi_web or Decimal('0')) + so_tien_moi_nguoi
                member.save()

                # Ghi nhận một giao dịch Hoàn ứng / Tất toán quỹ nội bộ để dễ đối soát
                GiaoDich.objects.create(
                    loai='HU', # Hoàn ứng / Tất toán
                    so_tien=so_tien_moi_nguoi,
                    loai_quy=quy,
                    thanh_vien=member,
                    ly_do=f"[TẤT TOÁN QUỸ] Nhận lại tiền chia đều từ quỹ '{quy.ten_quy}' bị giải tán",
                    phuong_thuc='CASH',
                    da_xac_nhan=True
                )

                # Bắn thư thông báo qua hệ thống bưu tá cho từng thành viên
                if member.user:
                    ThongBaoBuuTa.objects.create(
                        nguoi_nhan=member.user,
                        tieu_de="📢 Tất toán giải tán quỹ lớp!",
                        noi_dung=f"Quỹ '{quy.ten_quy}' đã giải tán. Số dư quỹ được chia đều, sếp nhận được {int(so_tien_moi_nguoi):,}đ vào Ví Web.",
                        loai='FINANCE'
                    )

            # 4. Cập nhật trạng thái đóng băng hoàn toàn quỹ
            quy.trang_thai_vong_doi = 'DISBANDED'
            quy.is_khoa_so = True
            quy.save()

            messages.success(request, f"🎉 Đã giải tán quỹ '{quy.ten_quy}' thành công! Tổng số tiền {int(so_du_quy):,}đ đã được tất toán và chia đều cho {tong_so_tv} thành viên lớp.")
    except Exception as e:
        messages.error(request, f"Có lỗi xảy ra trong quá trình chia tiền tất toán: {str(e)}")

    return redirect('dashboard')
@csrf_exempt
@login_required
def api_nap_vi_web(request):
    if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        so_tien_raw = str(data.get('so_tien', '0')).replace(',', '').strip()
        so_tien = Decimal(so_tien_raw) if so_tien_raw else Decimal('0')
        phuong_thuc = data.get('phuong_thuc')
        tv = ThanhVien.objects.filter(user=request.user).first()
        if not tv: return JsonResponse({'status': 'error', 'message': 'Không thấy hồ sơ!'}, status=444)
        quy_mac_dinh = LoaiQuy.objects.filter(lop_hoc=tv.lop_hoc).first() or LoaiQuy.objects.first()
        with transaction.atomic():
            if phuong_thuc in ['BANK', 'LOCAL_TEST_BANK']:
                tv.so_du_vi_web = (tv.so_du_vi_web or Decimal('0')) + so_tien
                tv.save()
                GiaoDich.objects.create(loai='THU', so_tien=so_tien, thanh_vien=tv, loai_quy=quy_mac_dinh, ly_do="Nạp ví Web - CK", phuong_thuc='BANK', da_xac_nhan=True)
                return JsonResponse({'status': 'success', 'message': 'Đã duyệt tự động!'})
            elif phuong_thuc == 'CASH':
                GiaoDich.objects.create(loai='THU', so_tien=so_tien, thanh_vien=tv, loai_quy=quy_mac_dinh, ly_do="Nạp ví Web - Tiền mặt", phuong_thuc='CASH', da_xac_nhan=False)
                return JsonResponse({'status': 'success', 'message': 'Chờ thủ quỹ duyệt tay!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# =========================================================================
# 🌟 LÕI THAY THẾ CHỮA CHÁY BIẾN CỐ TIỀN MẶT & VÍ WEB (API ĐÓNG QUỸ LỚP)
# =========================================================================
@csrf_exempt
@login_required
@transaction.atomic
def api_trich_vi_nop_quy(request):
    """API trích quỹ ví web hoặc báo nộp tiền mặt. Đảm bảo chuẩn Decimal, Tiền mặt chờ duyệt."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ'}, status=405)
    try:
        data = json.loads(request.body)
        so_tien_raw = str(data.get('so_tien', '0')).replace(',', '').replace('.', '').strip()
        so_tien = Decimal(so_tien_raw) if so_tien_raw.isdigit() else Decimal('0')
        
        if so_tien <= 0:
            return JsonResponse({'status': 'error', 'message': 'Số tiền phải lớn hơn 0đ!'})

        ly_do = data.get('ly_do', '')
        muc_tieu_id = data.get('muc_tieu_id')
        dot_thu_id = data.get('dot_thu_id')
        phuong_thuc = data.get('phuong_thuc', 'CASH') 

        tv = ThanhVien.objects.filter(user=request.user).first()
        if not tv and getattr(request.user, 'mssv', ''):
            tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
        if not tv:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy hồ sơ thành viên!'})

        is_xac_nhan = False
        msg = ""

        if phuong_thuc == 'WEB_WALLET':
            so_du_vi = tv.so_du_vi_web or Decimal('0')
            if so_du_vi < so_tien:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Ví không đủ lúa (Hiện có {format_money(so_du_vi)}đ).',
                    'action': 'redirect_to_deposit'
                })
            # 🔥 Khấu trừ trực tiếp chuẩn số Decimal tài chính
            tv.so_du_vi_web = so_du_vi - so_tien
            tv.save()
            is_xac_nhan = True
            ly_do = f"Trích ví Web: {ly_do or 'Đóng quỹ lớp'}"
            msg = 'Đã hoàn tất trích tiền từ Ví Web để đóng quỹ lớp thành công! 🎉'

        elif phuong_thuc in ['BANK', 'TRANSFER']:
            is_xac_nhan = True
            ly_do = f"[GIẢ LẬP QR] {ly_do or 'Chuyển khoản đóng quỹ'}"
            msg = 'Đã quét QR và đóng quỹ thành công! 🎉'

        elif phuong_thuc == 'CASH':
            # 🛑 TIỀN MẶT: da_xac_nhan=False, không trừ ví, không kích hoạt cập nhật tiến độ
            is_xac_nhan = False
            ly_do = f"[TIỀN MẶT CHỜ DUYỆT] {ly_do or 'Nộp tiền mặt'}"
            msg = 'Đã gửi yêu cầu nộp tiền mặt thành công! Sếp vui lòng đưa tiền cho Thủ quỹ để được duyệt nhé.'

        dot_thu = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else None
        quy_target = dot_thu.loai_quy if dot_thu else LoaiQuy.objects.first()

        GiaoDich.objects.create(
            loai='THU', so_tien=so_tien, loai_quy=quy_target, dot_thu=dot_thu,
            muc_tieu_id=muc_tieu_id, thanh_vien=tv, ly_do=ly_do,
            phuong_thuc='BANK' if phuong_thuc in ['BANK', 'TRANSFER'] else phuong_thuc,
            da_xac_nhan=is_xac_nhan
        )
        
        # Chỉ khi duyệt thành công (Ví Web/QR), mới hạch toán trực tiếp vào Tiến độ lập tức
        if is_xac_nhan and dot_thu:
            tiendo, _ = TienDoDongQuy.objects.get_or_create(
                dot_thu=dot_thu, thanh_vien=tv,
                defaults={'so_tien_can_nop': dot_thu.so_tien_moi_nguoi, 'so_tien_da_nop': Decimal('0')}
            )
            tiendo.so_tien_da_nop = Decimal(str(tiendo.so_tien_da_nop)) + so_tien
            tiendo.trang_thai = 'DU' if tiendo.so_tien_da_nop >= tiendo.so_tien_can_nop else 'THIEU'
            tiendo.save()

            check_and_reward_quest(request, 'Công dân gương mẫu')
            if tv.is_no_xau:
                tv.is_no_xau = False
                tv.save()
            try:
                xu_co_ban = int(so_tien / 10000)
                if xu_co_ban > 0:
                    tv.vi_xu += xu_co_ban
                    tv.save()
                    LichSuGiaoDichXu.objects.create(thanh_vien=tv, loai_giao_dich='CONG_XU', so_xu=xu_co_ban, ly_do="Đóng quỹ thành công")
            except: pass

        return JsonResponse({'status': 'success', 'message': msg})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Lỗi: {str(e)}'}, status=500)

def kiem_tra_va_tu_dong_tru_no_quy(user):
    from .models import TienDoDongQuy, GiaoDich, ThongBaoBuuTa
    bay_gio = timezone.now()
    ds_tre_han = TienDoDongQuy.objects.filter(trang_thai__in=['CHUA_NOP', 'THIEU'], ngay_nhac_nho_gan_nhat__lte=bay_gio - timedelta(days=7), da_tu_dong_khau_tru=False)
    for tiendo in ds_tre_han:
        tv = tiendo.thanh_vien
        so_tien_no = tiendo.so_tien_can_nop - tiendo.so_tien_da_nop
        if float(tv.so_du_vi_web) >= float(so_tien_no):
            with transaction.atomic():
                tv.so_du_vi_web -= so_tien_no
                tv.save()
                GiaoDich.objects.create(loai='THU', so_tien=so_tien_no, loai_quy=tiendo.dot_thu.loai_quy, dot_thu=tiendo.dot_thu, thanh_vien=tv, da_xac_nhan=True, ly_do=f"[HỆ THỐNG] Tự động khấu trừ đợt '{tiendo.dot_thu.ten_dot}'")
                tiendo.so_tien_da_nop = tiendo.so_tien_can_nop
                tiendo.trang_thai = 'DU'; tiendo.da_tu_dong_khau_tru = True; tiendo.save()
                if tv.user:
                    ThongBaoBuuTa.objects.create(nguoi_nhan=tv.user, tieu_de="⚡ Hệ thống tự động khấu trừ quỹ", noi_dung=f"Hệ thống đã tự trích {int(so_tien_no):,}đ từ ví.", loai='SYSTEM')

@login_required
def page_nap_tien_view(request):
    is_admin = is_thu_quy(request.user)
    user_role_name = "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp"
    tv = ThanhVien.objects.filter(user=request.user).first()
    if not tv and getattr(request.user, 'mssv', ''):
        tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
    so_du_vi_web_that = tv.so_du_vi_web if tv else 0
    vi_xu_that = tv.vi_xu if tv else 0
    
    danh_sach_dot_thu = []
    if tv:
        all_dot = DotThu.objects.order_by('-created_at')
        for dt in all_dot:
            da_nop = GiaoDich.objects.filter(thanh_vien=tv, dot_thu=dt, loai__in=['THU', 'LAI'], da_xac_nhan=True).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
            con_lai = dt.so_tien_moi_nguoi - da_nop
            if con_lai > 0:
                danh_sach_dot_thu.append({'id': dt.id, 'ten_dot': dt.ten_dot, 'so_tien_can_nop': float(con_lai)})
    muc_tieu_quy = MucTieuQuy.objects.filter(hoan_thanh=False)
    danh_sach_muc_tieu = [{'id': mt.id, 'ten_muc_tieu': mt.ten_muc_tieu} for mt in muc_tieu_quy]
    return render(request, 'quanlyquy/page_nap_tien.html', {
        'is_admin': is_admin, 'user_role_name': user_role_name, 'vi_xu': vi_xu_that,
        'so_du_vi_web': so_du_vi_web_that, 'danh_sach_dot_thu': danh_sach_dot_thu, 'danh_sach_muc_tieu': danh_sach_muc_tieu,
    })
@login_required
def kho_tai_nguyen_view(request):
    # 🌟 THÊM IMPORT NÀY VÀO ĐẦU HÀM ĐỂ DIỆT TẬN GỐC LỖI NAMEERROR SẾP NHÉ
    from django.db.models import Sum
    from .models import KhoTaiNguyen, ThanhVien, DotThu, GiaoDich

    # 1. Kiểm tra quyền Admin/Thủ quỹ trực tiếp bằng User hệ thống
    is_admin = request.user.is_superuser or request.user.is_staff
    
    tv = ThanhVien.objects.filter(user=request.user).first()
    
    # Nếu là thành viên thông thường thì tìm theo lớp của họ, nếu là admin thì lấy đợt thu mới nhất hệ thống
    if tv and tv.lop_hoc:
        dot_thu_moi_nhat = DotThu.objects.filter(loai_quy__lop_hoc=tv.lop_hoc).order_by('-created_at').first()
    else:
        dot_thu_moi_nhat = DotThu.objects.order_by('-created_at').first()
    
    da_hoan_thanh_quy = False
    
    if is_admin:
        da_hoan_thanh_quy = True # Admin luôn xem được công tâm
    elif tv and dot_thu_moi_nhat:
        # Check số tiền đóng quỹ của thành viên thường
        da_nop = GiaoDich.objects.filter(
            thanh_vien=tv, 
            dot_thu=dot_thu_moi_nhat, 
            loai__in=['THU', 'LAI'], 
            da_xac_nhan=True
        ).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        
        if da_nop >= dot_thu_moi_nhat.so_tien_moi_nguoi:
            da_hoan_thanh_quy = True

    # Lấy toàn bộ tài nguyên đang hoạt động lên giao diện 3D
    danh_sach_tai_nguyen = KhoTaiNguyen.objects.filter(is_active=True).order_by('id')

    context = {
        'danh_sach_tai_nguyen': danh_sach_tai_nguyen,
        'da_hoan_thanh_quy': da_hoan_thanh_quy,
        'dot_thu_moi_nhat': dot_thu_moi_nhat,
        'user_role_name': "Thủ quỹ hệ thống" if is_admin else "Thành viên lớp",
    }
    
    # Sếp lưu ý đoạn này: Ở bước trước sếp đặt tên file là kho_tai_nguyen.html hay page_kho_tai_nguyen.html thì điền cho chuẩn nhé!
    return render(request, 'quanlyquy/page_kho_tai_nguyen.html', context)