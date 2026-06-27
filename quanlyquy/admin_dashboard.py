import json
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from .models import GiaoDich, TaiSan, ThanhVien 

def dashboard_callback(request, context):
    # --- HELPER: Hàm định dạng tiền tệ có dấu chấm ---
    def f_money(v):
        return "{:,.0f}".format(v or 0).replace(',', '.')

    # 1. TỔNG QUAN HỆ THỐNG
    thu_raw = GiaoDich.objects.filter(loai__in=['THU', 'LAI', 'HU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    chi_raw = GiaoDich.objects.filter(loai__in=['CHI', 'TU']).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
    so_du_raw = float(thu_raw - chi_raw)

    # 2. THÀNH VIÊN ĐANG ĐĂNG NHẬP (Dành cho Member)
    current_member = ThanhVien.objects.filter(email=request.user.email).first()
    personal_history = []
    total_paid_raw = 0
    
    if current_member:
        personal_history = GiaoDich.objects.filter(thanh_vien=current_member).order_by('-ngay_tao')[:10]
        total_paid_raw = GiaoDich.objects.filter(thanh_vien=current_member, loai='THU').aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        for tx in personal_history:
            prefix = "+" if tx.loai in ['THU', 'LAI', 'HU'] else "-"
            tx.money_fmt = f"{prefix}{f_money(tx.so_tien)}"

    # 3. BIỂU ĐỒ DÒNG TIỀN 6 THÁNG
    stats = (
        GiaoDich.objects.annotate(month=TruncMonth('ngay_tao'))
        .values('month')
        .annotate(
            thu_thang=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
            chi_thang=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
        ).order_by('month')[:6]
    )
    months = [s['month'].strftime("T%m") for s in stats if s['month']]
    data_thu = [float(s['thu_thang'] or 0) for s in stats]
    data_chi = [float(s['chi_thang'] or 0) for s in stats]

    # 4. BẢNG VINH DANH TOP 3 ĐÓNG GÓP
    top_contributors = (
        ThanhVien.objects.annotate(total=Sum('giaodich__so_tien', filter=Q(giaodich__loai='THU')))
        .filter(total__gt=0)
        .order_by('-total')[:3]
    )
    for top in top_contributors:
        top.total_fmt = f_money(top.total)

    # 5. LỊCH SỬ CHUNG & TÀI SẢN
    recent_txs = GiaoDich.objects.select_related('thanh_vien').order_by('-ngay_tao')[:5]
    for tx in recent_txs:
        prefix = "+" if tx.loai in ['THU', 'LAI', 'HU'] else "-"
        tx.money_fmt = f"{prefix}{f_money(tx.so_tien)}"

    assets = TaiSan.objects.order_by('-ngay_mua')[:4]
    for ts in assets:
        ts.price_fmt = f_money(ts.gia_mua)
        ts.current_val_fmt = f_money(ts.gia_tri_hien_tai)

    # 6. ĐÓNG GÓI CHUYỂN RA HTML
    context.update({
        "tong_thu_fmt": f_money(thu_raw),
        "tong_chi_fmt": f_money(chi_raw),
        "so_du_fmt": f_money(so_du_raw),
        "total_paid_fmt": f_money(total_paid_raw),
        "tong_thu": float(thu_raw),
        "tong_chi": float(chi_raw),
        "so_du": so_du_raw,
        "is_warning": so_du_raw < 500000,
        "recent_txs": recent_txs,
        "assets": assets,
        "top_contributors": top_contributors,
        "personal_history": personal_history,
        "current_member": current_member,
        "chart_months": json.dumps(months),
        "chart_thu": json.dumps(data_thu),
        "chart_chi": json.dumps(data_chi),
    })
    return context