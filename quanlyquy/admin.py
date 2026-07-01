from django import forms 
from django.http import HttpResponse
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse, path
from django.db import transaction
from django.shortcuts import render, redirect
from django.db.models import Sum
import pandas as pd
from unfold.decorators import action, display
from .models import BieuQuyet, ThanhVien, ChiTietBinhChon
from .models import ClassFund, CollectionPeriod, Transaction, InvestmentProposal, ProposalVote
from decimal import Decimal
from .models import ThongBaoBuuTa, GiaoDich
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline # Thêm TabularInline của Unfold cho đẹp
from .models import KhoTaiNguyen
# ==========================================
# THÊM PhuongAnBieuQuyet VÀO ĐÂY NÈ SẾP
# ==========================================
from .models import (
    User, LopHoc, ThanhVien, LoaiQuy, DotThu, TaiSan, GiaoDich, 
    TienDoDongQuy, DanhMucThuChi, MucTieuQuy, SuKienNhacViec,
    PhieuDeXuatChi, KhieuNai, QuaTang, NhiemVu, LichSuWebhook, 
    BieuQuyet, PhuongAnBieuQuyet, HuyHieu, HuyHieuThanhVien,
    KhoTaiNguyen
)

admin.site.site_header = "HỆ THỐNG TÀI CHÍNH FUNDSMART PRO"
admin.site.site_title = "FundSmart Advanced"
admin.site.index_title = "Bảng điều khiển Kế toán kép"

def f_money(value):
    return "{:,.0f} đ".format(value or 0).replace(',', '.')

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label="Chọn file sao kê ngân hàng (Excel)")

# ==========================================
# 1. QUẢN LÝ NHÂN SỰ & THÀNH VIÊN
# ==========================================
@admin.register(LopHoc)
class LopHocAdmin(ModelAdmin):
    list_display = ('ten_lop', 'nien_khoa', 'created_at')
    search_fields = ('ten_lop',)

@admin.register(ThanhVien)
class ThanhVienAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ('mssv', 'ho_ten', 'lop_hoc', 'phone', 'is_no_xau', 'display_status') 
    list_filter = ('lop_hoc', 'is_no_xau', 'gender') 
    search_fields = ('mssv', 'ho_ten', 'phone', 'email')
    list_editable = ('phone', 'is_no_xau')
    list_per_page = 20

    @display(description="Trạng thái tài chính")
    def display_status(self, obj):
        if obj.is_no_xau: 
            return format_html('<span style="background-color: rgba(244, 63, 94, 0.1); color: #f43f5e; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>', 'NỢ XẤU')
        return format_html('<span style="background-color: rgba(16, 185, 129, 0.1); color: #10b981; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>', 'AN TOÀN')

@admin.register(User)
class CustomUserAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ('username', 'full_name', 'role', 'phone', 'is_active')
    list_filter = ('role', 'is_active')
    list_editable = ('role', 'is_active')

# ==========================================
# 2. QUẢN LÝ QUỸ & DANH MỤC
# ==========================================
@admin.register(LoaiQuy)
class LoaiQuyAdmin(ModelAdmin):
    # Hiển thị thêm cột Trạng thái vòng đời để theo dõi quỹ nào Đang hoạt động / Đã giải tán
    list_display = ('ten_quy', 'display_balance', 'is_khoa_so', 'trang_thai_vong_doi', 'dieu_chuyen_nhanh')
    list_editable = ('is_khoa_so',)
    list_filter = ('trang_thai_vong_doi', 'is_khoa_so')

    # 🌟 ĐĂNG KÝ HÀNH ĐỘNG GIẢI TÁN QUỸ VÀO ADMIN ACTION
    actions = ['giai_tan_quy_va_chia_tien_ve_vi']

    @display(description="Số dư hiện tại")
    def display_balance(self, obj):
        color = "#ef4444" if obj.so_du_hien_tai < 500000 else "#10b981"
        return format_html('<b style="color: {}; font-size: 15px;">{}</b>', color, f_money(obj.so_du_hien_tai))

    @display(description="⚡ Chuyển tiền")
    def dieu_chuyen_nhanh(self, obj):
        url = reverse('admin:quanlyquy_giaodich_add') + f"?loai=NB&loai_quy={obj.id}"
        return format_html('<a href="{}" style="background:#6366f1; color:white; padding:4px 12px; border-radius:6px; font-size:11px; font-weight:700;">{}</a>', url, 'ĐIỀU CHUYỂN')

    # 💥 LOGIC TỰ ĐỘNG CHIA TIỀN KHI BẤM GIẢI TÁN
    @admin.action(description='💥 Giải tán quỹ đã chọn & Tất toán tiền chia đều về ví Web cho lớp')
    def giai_tan_quy_va_chia_tien_ve_vi(self, request, queryset):
        # Import an toàn ngay trong hàm để tránh triệt để lỗi vòng lặp import (Circular Import)
        from decimal import Decimal
        from django.db import transaction
        from .models import GiaoDich, ThongBaoBuuTa, ThanhVien

        for quy in queryset:
            # 1. Chặn nếu quỹ này đã bấm giải tán từ trước
            if quy.trang_thai_vong_doi == 'DISBANDED':
                self.message_user(request, f"Quỹ '{quy.ten_quy}' đã được giải tán từ trước rồi sếp ơi!", messages.WARNING)
                continue
                
            lop_target = quy.lop_hoc
            if not lop_target:
                self.message_user(request, f"Quỹ '{quy.ten_quy}' chưa được cấu hình thuộc lớp nào nên hệ thống không biết chia tiền cho ai!", messages.ERROR)
                continue

            # 2. Quét toàn bộ thành viên đang hoạt động thực tế của lớp đó
            danh_sach_tv = ThanhVien.objects.filter(lop_hoc=lop_target, deleted_at__isnull=True)
            tong_so_tv = danh_sach_tv.count()

            if tong_so_tv == 0:
                self.message_user(request, f"Lớp '{lop_target.ten_lop}' hiện đang trống, không có thành viên để nhận tiền tất toán!", messages.WARNING)
                continue

            # 3. Đọc số dư hiện tại của quỹ bằng property thông minh sếp đã viết
            so_du_quy = quy.so_du_hien_tai

            # 4. Tiến hành giải ngân chia đều nếu quỹ vẫn còn lúa
            if so_du_quy > 0:
                # Sử dụng transaction.atomic để bọc khối lệnh, đảm bảo tất cả đều được cộng tiền hoặc không ai bị lỗi mất tiền
                with transaction.atomic():
                    # Chia đều số dư quỹ cho tổng sếp trong lớp (Dùng chuẩn tài chính Decimal)
                    so_tien_moi_nguoi = Decimal(str(round(float(so_du_quy) / tong_so_tv, 2)))

                    for member in danh_sach_tv:
                        # Cộng tiền thẳng vào số dư Ví Web của sinh viên
                        member.so_du_vi_web = (member.so_du_vi_web or Decimal('0')) + so_tien_moi_nguoi
                        member.save()

                        # Tạo giao dịch Hoàn ứng (HU) đã xác nhận để lưu vết đối soát kế toán kép
                        GiaoDich.objects.create(
                            loai='HU',  
                            so_tien=so_tien_moi_nguoi,
                            loai_quy=quy,
                            thanh_vien=member,
                            ly_do=f"[TẤT TOÁN QUỸ LỚP] Nhận lại tiền từ quỹ '{quy.ten_quy}' bị giải tán",
                            phuong_thuc='CASH',
                            da_xac_nhan=True
                        )

                        # Phát thư thông báo tự động thông qua Bưu tá hệ thống
                        if member.user:
                            ThongBaoBuuTa.objects.create(
                                nguoi_nhan=member.user,
                                tieu_de="📢 Tất toán giải tán quỹ lớp!",
                                noi_dung=f"Quỹ '{quy.ten_quy}' đã giải tán. Số dư quỹ được tất toán, sếp nhận được {int(so_tien_moi_nguoi):,}đ vào Ví Web.",
                                loai='FINANCE'
                            )

            # 5. Cập nhật trạng thái đóng băng quỹ vĩnh viễn và Khóa sổ
            quy.trang_thai_vong_doi = 'DISBANDED'
            quy.is_khoa_so = True
            quy.save()
            
            self.message_user(
                request, 
                format_html("🎉 Đã giải tán quỹ '<b>{}</b>'! Tất toán thành công <b>{:,}đ</b> chia đều cho <b>{}</b> sếp thuộc lớp <b>{}</b>.", quy.ten_quy, int(so_du_quy), tong_so_tv, lop_target.ten_lop), 
                messages.SUCCESS
            )
@admin.register(DanhMucThuChi)
class DanhMucAdmin(ModelAdmin):
    list_display = ('ten_danh_muc', 'loai', 'mo_ta')
    list_filter = ('loai',)

# ==========================================
# 3. LÕI TÀI CHÍNH: GIAO DỊCH & ĐỐI SOÁT
# ==========================================
@admin.register(GiaoDich)
class GiaoDichAdmin(ModelAdmin, ImportExportModelAdmin):
    list_display = ('ngay_tao', 'display_loai', 'display_amount', 'loai_quy', 'dot_thu', 'thanh_vien')
    list_filter = ('loai', 'loai_quy', 'dot_thu', 'danh_muc', 'ngay_tao')
    search_fields = ('ly_do', 'thanh_vien__ho_ten', 'thanh_vien__mssv')
    actions = ['reconcile_with_bank']

    @display(description="Dòng tiền")
    def display_amount(self, obj):
        is_in = obj.loai in ['THU', 'LAI', 'HU']
        color = "#10b981" if is_in else "#f43f5e"
        return format_html('<span style="color: {}; font-weight: 900;">{}</span>', color, f_money(obj.so_tien))

    @display(description="Nghiệp vụ")
    def display_loai(self, obj):
        if obj.loai in ['THU', 'LAI', 'HU']:
            return format_html('<span style="background-color: rgba(16, 185, 129, 0.1); color: #10b981; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>', obj.get_loai_display().upper())
        return format_html('<span style="background-color: rgba(244, 63, 94, 0.1); color: #f43f5e; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 11px;">{}</span>', obj.get_loai_display().upper())

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path('download-template/', self.download_template, name='quanlyquy_giaodich_download_template')]
        return custom_urls + urls

    def download_template(self, request):
        df = pd.DataFrame({'Số tiền': [150000, -20000], 'Nội dung': ['Ví dụ: Nguyễn Văn A nộp', 'Ví dụ: Mua nước']})
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=mau_doi_soat_fundsmart.xlsx'
        df.to_excel(response, index=False)
        return response

    @action(description="🔍 Đối soát ngân hàng từ file Excel")
    def reconcile_with_bank(self, request, queryset):
        if 'apply' in request.POST:
            form = ExcelUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    df = pd.read_excel(request.FILES['excel_file'])
                    bank_amounts = df['Số tiền'].astype(float).tolist()
                    system_amounts = [float(gd.so_tien) for gd in queryset]
                    matches = [f_money(a) for a in bank_amounts if a in system_amounts]
                    missing_sys = [f_money(a) for a in bank_amounts if a not in system_amounts]
                    missing_bank = [f_money(a) for a in system_amounts if a not in bank_amounts]
                    return render(request, "admin/reconciliation_report.html", {
                        'results': {'match': matches, 'missing_sys': missing_sys, 'missing_bank': missing_bank},
                        'title': "Kết quả đối soát tài chính"
                    })
                except Exception as e:
                    self.message_user(request, f"Lỗi xử lý file: {str(e)}", messages.ERROR)
                    return redirect(request.get_full_path())
        return render(request, "admin/excel_upload.html", {'items': queryset, 'form': ExcelUploadForm(), 'title': "Tải lên sao kê để so đối", 'download_url': reverse('admin:quanlyquy_giaodich_download_template')})

# ==========================================
# 4. GAMIFICATION VÀ KHÁC
# ==========================================
@admin.register(DotThu)
class DotThuAdmin(ModelAdmin):
    list_display = ('ten_dot', 'loai_quy', 'format_dinh_muc', 'display_progress', 'han_chot')
    
    @display(description="Định mức")
    def format_dinh_muc(self, obj): return f_money(obj.so_tien_moi_nguoi)

    @display(description="Đã thu được")
    def display_progress(self, obj):
        tong = GiaoDich.objects.filter(dot_thu=obj, loai='THU').aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        return format_html('<span style="color:#6366f1; font-weight:bold;">{}</span>', f_money(tong))

@admin.register(TaiSan)
class TaiSanAdmin(ModelAdmin): list_display = ('ten_tai_san', 'gia_mua', 'ngay_mua', 'ti_le_khau_hao')

@admin.register(MucTieuQuy)
class MucTieuQuyAdmin(ModelAdmin): list_display = ['ten_muc_tieu', 'so_tien_hien_tai', 'so_tien_muc_tieu', 'hoan_thanh']; list_editable = ['hoan_thanh']

@admin.register(SuKienNhacViec)
class SuKienNhacViecAdmin(ModelAdmin): list_display = ['ten_su_kien', 'ngay_dien_ra']

@admin.register(PhieuDeXuatChi)
class PhieuDeXuatChiAdmin(ModelAdmin): list_display = ('nguoi_de_xuat', 'so_tien', 'trang_thai'); list_editable = ('trang_thai',)

@admin.register(KhieuNai)
class KhieuNaiAdmin(ModelAdmin): list_display = ('tieu_de', 'thanh_vien', 'trang_thai'); list_editable = ('trang_thai',)

@admin.register(NhiemVu)
class NhiemVuAdmin(admin.ModelAdmin):
    list_display = ('ten_nhiem_vu', 'loai_nhiem_vu', 'phan_thuong_xu', 'is_active', 'created_at')
    list_editable = ('is_active',) 
    list_filter = ('loai_nhiem_vu', 'is_active')
    search_fields = ('ten_nhiem_vu',)

@admin.register(QuaTang)
class QuaTangAdmin(ModelAdmin): list_display = ('ten_qua', 'gia_xu', 'so_luong_kho')

@admin.register(LichSuWebhook)
class WebhookAdmin(ModelAdmin): list_display = ('ma_giao_dich_ngan_hang', 'so_tien', 'trang_thai_xu_ly')

# ==========================================
# CẤU HÌNH GIAO DIỆN TẠO KHẢO SÁT CHUYÊN NGHIỆP
# ==========================================
class PhuongAnInline(TabularInline):
    model = PhuongAnBieuQuyet
    extra = 2  # Hiện sẵn 2 dòng trắng để Admin nhập Phương án A, Phương án B
    
@admin.register(BieuQuyet)
class BieuQuyetAdmin(ModelAdmin): 
    list_display = ('cau_hoi', 'dang_mo', 'trang_thai_duyet', 'han_chot')
    inlines = [PhuongAnInline] 
    list_editable = ('dang_mo',) 

    # Đăng ký nút bấm hành động trong trang danh sách Khảo sát / Vote
    actions = ['tat_toan_va_giai_ngan_dau_tu_ngay']

    # 🚀 LOGIC TỰ ĐỘNG CHIA TIỀN (CẢ GỐC + CẢ LÃI) VỀ VÍ WEB
    @admin.action(description='⚡ Tất toán dự án đầu tư này & Giải ngân (CẢ GỐC + LÃI) về ví Web')
    def tat_toan_va_giai_ngan_dau_tu_ngay(self, request, queryset):
        from decimal import Decimal
        from django.db import transaction
        from django.utils import timezone
        from .models import ThanhVien, ThongBaoBuuTa, GiaoDich

        for cuoc_vote in queryset:
            # 1. Chặn nếu cuộc vote này không ở trạng thái APPROVED (Đang đầu tư chạy lãi)
            if cuoc_vote.trang_thai_duyet != 'APPROVED':
                self.message_user(request, f"Dự án '{cuoc_vote.cau_hoi}' không ở trạng thái đang đầu tư (APPROVED) để tất toán!", messages.WARNING)
                continue
                
            lop_target = cuoc_vote.lop_hoc
            danh_sach_tv = ThanhVien.objects.filter(lop_hoc=lop_target, deleted_at__isnull=True) if lop_target else []
            tong_so_tv = danh_sach_tv.count()
            
            if tong_so_tv == 0:
                self.message_user(request, f"Lớp của dự án này không có thành viên nào để nhận tiền tất toán!", messages.WARNING)
                continue
                
            with transaction.atomic():
                # 2. LẤY SỐ TIỀN VỐN GỐC THỰC TẾ (Ví dụ: 100.000đ từ database)
                so_tien_goc = float(cuoc_vote.so_tien_dau_tu)
                lai_suat_nam = 4.8
                ngay_bat_dau = cuoc_vote.updated_at or timezone.now()
                
                # 3. TÍNH TOÀN BỘ SỐ TIỀN LÃI REAL-TIME ĐẾN THỜI ĐIỂM BẤM NÚT
                thoi_gian_dau_tu_ms = (timezone.now() - ngay_bat_dau).total_seconds() * 1000
                lai_mili_giay = (so_tien_goc * (lai_suat_nam / 100)) / (365 * 24 * 60 * 60 * 1000)
                tong_lai_thuc_te = max(0, thoi_gian_dau_tu_ms * lai_mili_giay)
                
                # 🔥 TỔNG SỐ TIỀN PHẢI CHIA = TIỀN GỐC + TIỀN LÃI
                tong_so_tien_tat_toan = so_tien_goc + tong_lai_thuc_te
                
                # Chia đều tổng (Gốc + Lãi) cho cả lớp
                so_tien_chia_deu = Decimal(str(round(tong_so_tien_tat_toan / tong_so_tv, 2)))
                
                # 4. GIẢI NGÂN ĐỒNG LOẠT VÀO VÍ WEB CHO TỪNG THÀNH VIÊN
                for member in danh_sach_tv:
                    # Cộng đầy đủ cả gốc lẫn lãi vào số dư ví Web
                    member.so_du_vi_web = (member.so_du_vi_web or Decimal('0')) + so_tien_chia_deu
                    member.save()
                    
                    # Ghi nhận sổ giao dịch Hoàn ứng (HU) khớp với số tiền thực tế nhận được
                    if cuoc_vote.loai_quy:
                        GiaoDich.objects.create(
                            loai='HU',
                            so_tien=so_tien_chia_deu,
                            loai_quy=cuoc_vote.loai_quy,
                            thanh_vien=member,
                            ly_do=f"[TẤT TOÁN VOTE] Nhận tiền (Gốc + Lãi) dự án '{cuoc_vote.cau_hoi}' kết thúc sớm",
                            phuong_thuc='CASH',
                            da_xac_nhan=True
                        )
                    
                    # Bắn thư thông báo bưu tá báo tin vui tiền về ví
                    if member.user:
                        ThongBaoBuuTa.objects.create(
                            nguoi_nhan=member.user,
                            tieu_de="💰 Dự án đầu tư biểu quyết đã tất toán hoàn tất!",
                            noi_dung=f"Dự án '{cuoc_vote.cau_hoi}' đã được tất toán sớm. Sếp đã nhận lại {int(so_tien_chia_deu):,}đ (Bao gồm cả Gốc + Lãi thực tế) vào Ví Web.",
                            loai='FINANCE'
                        )
                
                # 5. Đổi trạng thái cuộc vote sang CONCLUDED để khóa dự án và đóng băng số lãi trên giao diện HTML
                cuoc_vote.trang_thai_duyet = 'CONCLUDED'
                cuoc_vote.save()
                
                self.message_user(
                    request, 
                    f"🎉 Tất toán thành công dự án '{cuoc_vote.cau_hoi}'! Tổng số tiền giải ngân thực tế (Gốc: {int(so_tien_goc):,}đ + Lãi: {round(tong_lai_thuc_te, 2)}đ) là {int(tong_so_tien_tat_toan):,}đ đã được chia đều về ví Web cho {tong_so_tv} thành viên lớp.", 
                    messages.SUCCESS
                )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.nguoi_tao = request.user 
            from .models import ThanhVien, ClassFund
            thanh_vien = ThanhVien.objects.filter(user=request.user).first()
            if thanh_vien and thanh_vien.lop_hoc:
                quy_cua_lop = LoaiQuy.objects.filter(lop_hoc=thanh_vien.lop_hoc).first()
                if quy_cua_lop:
                    obj.loai_quy = quy_cua_lop
        super().save_model(request, obj, form, change)  

@admin.register(HuyHieu)
class HuyHieuAdmin(ModelAdmin): 
    list_display = ('ten_huy_hieu', 'diem_yeu_cau', 'link_icon')

@admin.register(HuyHieuThanhVien)
class HuyHieuThanhVienAdmin(ModelAdmin): 
    list_display = ('thanh_vien', 'huy_hieu', 'ngay_dat_duoc')

# ==========================================
# 5. QUẢN LÝ ĐỀ XUẤT ĐẦU TƯ & BIỂU QUYẾT
# ==========================================
@admin.register(ClassFund)
class ClassFundAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_cash', 'total_invest', 'status', 'start_date', 'end_date')
    list_filter = ('status',)
    search_fields = ('name',)

# 2. Đăng ký Đợt Thu Quỹ
@admin.register(CollectionPeriod)
class CollectionPeriodAdmin(admin.ModelAdmin):
    list_display = ('title', 'fund', 'amount_required')
    list_filter = ('fund',)

# 3. Đăng ký Sổ Giao Dịch & Đối Soát Tự Động
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'fund', 'user', 'amount', 'type', 'status', 'created_at')
    list_filter = ('type', 'status', 'fund')
    search_fields = ('order_id', 'user__username')

# 4. Đăng ký Đề xuất Đầu tư
@admin.register(InvestmentProposal)
class InvestmentProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'fund', 'amount', 'status', 'expired_at')
    list_filter = ('status', 'fund')

# 5. Đăng ký Chi tiết Phiếu bầu
@admin.register(ChiTietBinhChon)
class ChiTietBinhChonAdmin(admin.ModelAdmin):
    # 🌟 GỌI CỘT ẢO 'get_phuong_an' ĐỂ NÉ LỖI HỆ THỐNG
    list_display = ('id', 'get_username', 'get_lop', 'bieu_quyet', 'get_phuong_an', 'created_at')
    
    # Tạm thời bỏ lọc theo phương án để không bị bắt lỗi Field
    list_filter = ('bieu_quyet', 'thanh_vien__lop_hoc')
    search_fields = ('thanh_vien__user__username', 'bieu_quyet__cau_hoi')

    # 🌟 HÀM ẢO 1: Lấy nội dung phương án hiển thị lên bảng admin công tâm
    def get_phuong_an(self, obj):
        # Thử lấy theo các tên biến có thể có, nếu không được thì trả về ID trực tiếp
        if hasattr(obj, 'phuong_an_chon') and obj.phuong_an_chon:
            return obj.phuong_an_chon.noi_dung
        elif hasattr(obj, 'phuong_an') and obj.phuong_an:
            return obj.phuong_an.noi_dung
        elif hasattr(obj, 'phuong_an_id'):
            return f"Phương án ID: {obj.phuong_an_id}"
        return "N/A"
    get_phuong_an.short_description = 'Phương án chọn'

    def get_username(self, obj):
        return obj.thanh_vien.user.username if obj.thanh_vien and obj.thanh_vien.user else "N/A"
    get_username.short_description = 'Tài khoản sinh viên'

    def get_lop(self, obj):
        return obj.thanh_vien.lop_hoc.ten_lop if obj.thanh_vien and obj.thanh_vien.lop_hoc else "Không có lớp"
    get_lop.short_description = 'Thuộc Lớp'
@admin.register(KhoTaiNguyen)
class KhoTaiNguyenAdmin(ModelAdmin):
    list_display = ('ten_tai_nguyen', 'loai', 'tai_khoan', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('loai', 'is_active')
    search_fields = ('ten_tai_nguyen', 'tai_khoan')