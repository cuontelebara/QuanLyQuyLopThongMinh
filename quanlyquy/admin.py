from django import forms 
from django.http import HttpResponse
from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.db.models import Sum
import pandas as pd
from unfold.decorators import action, display

from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline # Thêm TabularInline của Unfold cho đẹp

# ==========================================
# THÊM PhuongAnBieuQuyet VÀO ĐÂY NÈ SẾP
# ==========================================
from .models import (
    User, LopHoc, ThanhVien, LoaiQuy, DotThu, TaiSan, GiaoDich, 
    TienDoDongQuy, DanhMucThuChi, MucTieuQuy, SuKienNhacViec,
    PhieuDeXuatChi, KhieuNai, QuaTang, NhiemVu, LichSuWebhook, 
    BieuQuyet, PhuongAnBieuQuyet, HuyHieu, HuyHieuThanhVien
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
    list_display = ('ten_quy', 'display_balance', 'is_khoa_so', 'dieu_chuyen_nhanh')
    list_editable = ('is_khoa_so',)

    @display(description="Số dư hiện tại")
    def display_balance(self, obj):
        color = "#ef4444" if obj.so_du_hien_tai < 500000 else "#10b981"
        return format_html('<b style="color: {}; font-size: 15px;">{}</b>', color, f_money(obj.so_du_hien_tai))

    @display(description="⚡ Chuyển tiền")
    def dieu_chuyen_nhanh(self, obj):
        url = reverse('admin:quanlyquy_giaodich_add') + f"?loai=NB&loai_quy={obj.id}"
        return format_html('<a href="{}" style="background:#6366f1; color:white; padding:4px 12px; border-radius:6px; font-size:11px; font-weight:700;">{}</a>', url, 'ĐIỀU CHUYỂN')

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
    list_display = ('cau_hoi', 'dang_mo', 'han_chot')
    inlines = [PhuongAnInline] # Gắn cái bảng nhập Phương án vào dưới đít bảng Câu hỏi
    list_editable = ('dang_mo',) # Cho phép bật/tắt bình chọn nhanh ở ngoài danh sách

@admin.register(HuyHieu)
class HuyHieuAdmin(ModelAdmin): 
    list_display = ('ten_huy_hieu', 'diem_yeu_cau', 'link_icon')

@admin.register(HuyHieuThanhVien)
class HuyHieuThanhVienAdmin(ModelAdmin): 
    list_display = ('thanh_vien', 'huy_hieu', 'ngay_dat_duoc')