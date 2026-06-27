from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

# ==========================================
# LÕI HỆ THỐNG: QUẢN LÝ DẤU VẾT & XÓA MỀM
# ==========================================
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Lần sửa cuối")
    created_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="Người tạo (ID)")
    updated_by = models.CharField(max_length=50, null=True, blank=True, verbose_name="Người sửa (ID)")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày xóa mềm")
    

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        

    def save(self, *args, **kwargs):
        if not self.pk:  # Nếu là tạo mới hoàn toàn (chưa có ID)
            self.deleted_at = None # Ép buộc nó phải là NULL để hiện lên web
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

# ==========================================
# PHÂN HỆ 1 & 2: THÔNG TIN NGƯỜI DÙNG & QUỸ LỚP
# ==========================================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'Quản lý Tổng quát'),   # Toàn quyền hệ thống
        ('LEADER', 'Lớp trưởng / Thủ quỹ'),      # Tạo Thu/Chi, quản lý thành viên
        ('MEMBER', 'Thành viên lớp'),           # Chỉ xem và đóng tiền
    )
    ROLE_CHOICES = (('ADMIN', 'Thủ Quỹ (Lớp trưởng)'), ('MEMBER', 'Thành Viên'), ('TESTER', 'QA/Tester'))
    full_name = models.CharField(max_length=255, verbose_name="Họ và tên")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True, verbose_name="Số điện thoại")
    mssv = models.CharField(max_length=20, null=True, blank=True, verbose_name="Mã sinh viên")
    credit_score = models.IntegerField(default=100, verbose_name="Điểm tín nhiệm")
    secure_pin = models.CharField(max_length=128, null=True, blank=True, verbose_name="Mã PIN bảo mật")

    class Meta:
        verbose_name = "Tài Khoản"
        verbose_name_plural = "Tài Khoản Hệ Thống"

    def __str__(self): return self.full_name or self.username

class LopHoc(BaseModel):
    ten_lop = models.CharField(max_length=50, verbose_name="Tên lớp")
    nien_khoa = models.CharField(max_length=50, verbose_name="Niên khóa")
    
    class Meta:
        verbose_name = "Lớp Học"
        verbose_name_plural = "Lớp Học"
        
    def __str__(self): return self.ten_lop

class ThanhVien(BaseModel):
    ho_ten = models.CharField(max_length=100, verbose_name="Họ tên")
    mssv = models.CharField(max_length=20, unique=True, verbose_name="MSSV")
    gender = models.CharField(max_length=10, choices=[('NAM', 'Nam'), ('NU', 'Nữ')], null=True, verbose_name="Giới tính")
    phone = models.CharField(max_length=15, null=True, blank=True, verbose_name="Số điện thoại")
    lop_hoc = models.ForeignKey(LopHoc, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lớp học")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    is_no_xau = models.BooleanField(default=False, verbose_name="Nợ xấu/Bảo lưu")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    vi_xu = models.IntegerField(default=0, verbose_name="Số dư Xu (Chi tiêu)")
    tong_xu_tich_luy = models.IntegerField(default=0, verbose_name="Tổng Xu từng kiếm (Đua TOP)")

    class Meta:
        verbose_name = "Thành Viên"
        verbose_name_plural = "Hồ Sơ Sinh Viên"

    def __str__(self): return f"{self.mssv} - {self.ho_ten}"

class LoaiQuy(BaseModel):
    ten_quy = models.CharField(max_length=100, verbose_name="Tên quỹ")
    is_khoa_so = models.BooleanField(default=False, verbose_name="Khóa sổ kế toán")
    
    # 🌟 BẮT BUỘC PHẢI CÓ DÒNG NÀY TRONG MODELS.PY:
    lop_hoc = models.ForeignKey('LopHoc', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Thuộc lớp học")
    
    nam_hoc_bat_dau = models.IntegerField(default=2022, verbose_name="Năm học bắt đầu")
    nam_hoc_ket_thuc = models.IntegerField(default=2026, verbose_name="Năm học kết thúc")
    trang_thai_vong_doi = models.CharField(
        max_length=20, 
        choices=[('ACTIVE', 'Đang hoạt động'), ('DISBANDED', 'Đã giải tán')], 
        default='ACTIVE', 
        verbose_name="Trạng thái vòng đời"
    )
    class Meta:
        verbose_name = "Quỹ Lớp"
        verbose_name_plural = "Quản Lý Quỹ Lớp"

    @property
    def so_du_hien_tai(self):
        thu = GiaoDich.objects.filter(loai_quy=self, loai__in=['THU', 'LAI', 'HU']).aggregate(models.Sum('so_tien'))['so_tien__sum'] or 0
        chi = GiaoDich.objects.filter(loai_quy=self, loai__in=['CHI', 'TU']).aggregate(models.Sum('so_tien'))['so_tien__sum'] or 0
        return thu - chi

    def __str__(self): return self.ten_quy

class DotThu(BaseModel):
    ten_dot = models.CharField(max_length=200, verbose_name="Tên đợt thu")
    loai_quy = models.ForeignKey(LoaiQuy, on_delete=models.CASCADE, verbose_name="Vào quỹ")
    so_tien_moi_nguoi = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Định mức nộp")
    han_chot = models.DateField(verbose_name="Hạn chót")

    class Meta:
        verbose_name = "Đợt Thu"
        verbose_name_plural = "Đợt Thu Tiền"

    def __str__(self): return self.ten_dot

class TienDoDongQuy(BaseModel):
    dot_thu = models.ForeignKey(DotThu, on_delete=models.CASCADE)
    thanh_vien = models.ForeignKey(ThanhVien, on_delete=models.CASCADE)
    so_tien_can_nop = models.DecimalField(max_digits=12, decimal_places=0)
    so_tien_da_nop = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    duoc_mien_giam = models.BooleanField(default=False)
    trang_thai = models.CharField(max_length=20, choices=[('CHUA_NOP', 'Chưa nộp'), ('THIEU', 'Nộp thiếu'), ('DU', 'Đã đủ')], default='CHUA_NOP')

class TaiSan(BaseModel):
    ten_tai_san = models.CharField(max_length=200, verbose_name="Tên tài sản")
    gia_mua = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Giá mua")
    ngay_mua = models.DateField(default=timezone.now, verbose_name="Ngày mua")
    ti_le_khau_hao = models.FloatField(default=10, verbose_name="% Khấu hao/Năm")

    class Meta:
        verbose_name = "Tài Sản"
        verbose_name_plural = "Tài Sản Của Lớp"

    @property
    def gia_tri_hien_tai(self):
        tuoi_doi = (timezone.now().date() - self.ngay_mua).days / 365
        khau_hao = float(self.gia_mua) * (self.ti_le_khau_hao / 100) * tuoi_doi
        gia_tri = float(self.gia_mua) - khau_hao
        return max(gia_tri, 0)

class MucTieuQuy(BaseModel):
    ten_muc_tieu = models.CharField(max_length=255, verbose_name="Tên mục tiêu")
    so_tien_muc_tieu = models.BigIntegerField(verbose_name="Số tiền mục tiêu (VNĐ)")
    so_tien_hien_tai = models.BigIntegerField(default=0, verbose_name="Đã gom được (VNĐ)")
    hoan_thanh = models.BooleanField(default=False, verbose_name="Đã hoàn thành?")
    
    class Meta:
        verbose_name = "Mục Tiêu"
        verbose_name_plural = "Mục Tiêu Tích Lũy"

class SuKienNhacViec(BaseModel):
    ten_su_kien = models.CharField(max_length=255, verbose_name="Tên sự kiện")
    mo_ta = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mô tả ngắn")
    ngay_dien_ra = models.DateField(default=timezone.now, verbose_name="Ngày diễn ra")
    
    class Meta:
        verbose_name = "Sự Kiện"
        verbose_name_plural = "Sự Kiện & Lịch Trình"

# ==========================================
# PHÂN HỆ 3: LÕI TÀI CHÍNH & GIAO DỊCH
# ==========================================
class DanhMucThuChi(BaseModel):
    ten_danh_muc = models.CharField(max_length=100, verbose_name="Tên danh mục")
    loai = models.CharField(max_length=3, choices=[('THU', 'Thu'), ('CHI', 'Chi')], verbose_name="Loại")
    mo_ta = models.TextField(null=True, blank=True, verbose_name="Mô tả danh mục")

    class Meta:
        verbose_name = "Danh Mục"
        verbose_name_plural = "Danh Mục Thu/Chi"

    def __str__(self): return f"[{self.get_loai_display()}] {self.ten_danh_muc}"

class GiaoDich(BaseModel):
    LOAI = [('THU', 'Thu quỹ'), ('CHI', 'Chi quỹ'), ('TU', 'Tạm ứng'), ('HU', 'Hoàn ứng'), ('LAI', 'Lãi NH'), ('NB', 'Điều chuyển nội bộ')]
    PHUONG_THUC = [('CASH', 'Tiền mặt'), ('BANK', 'Chuyển khoản / QR')]
    
    loai = models.CharField(max_length=3, choices=LOAI, verbose_name="Loại giao dịch")
    so_tien = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Số tiền")
    loai_quy = models.ForeignKey(LoaiQuy, on_delete=models.CASCADE, verbose_name="Quỹ")
    phuong_thuc = models.CharField(max_length=10, choices=PHUONG_THUC, default='CASH', verbose_name="Phương thức")
    da_xac_nhan = models.BooleanField(default=False, verbose_name="Thủ quỹ đã nhận tiền")
    def save(self, *args, **kwargs):
        # Nếu nộp qua Ngân hàng thì tự động xác nhận là đã thu tiền
        if self.phuong_thuc == 'BANK':
            self.da_xac_nhan = True
        super().save(*args, **kwargs)
    
    # [QUAN TRỌNG]: Thêm cột dot_thu để tránh lỗi Crash khi xem biểu đồ Thống Kê
    dot_thu = models.ForeignKey('DotThu', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Đợt thu")
    
    # [MỚI THÊM NÈ SẾP]: Kết nối Giao dịch với Mục tiêu để hệ thống biết tiền này nộp cho mục tiêu nào
    muc_tieu = models.ForeignKey('MucTieuQuy', on_delete=models.SET_NULL, null=True, blank=True, related_name='cac_giao_dich', verbose_name="Thuộc mục tiêu")
    
    danh_muc = models.ForeignKey(DanhMucThuChi, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Danh mục")
    thanh_vien = models.ForeignKey(ThanhVien, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Thành viên")
    ly_do = models.CharField(max_length=255, verbose_name="Nội dung/Ghi chú")
    anh_hoa_don = models.ImageField(upload_to='hoadon/', blank=True, null=True, verbose_name="Minh chứng (Hóa đơn)")
    
    is_an_danh = models.BooleanField(default=False, verbose_name="Giao dịch ẩn danh")
    ngay_tao = models.DateTimeField(default=timezone.now, verbose_name="Ngày tạo giao dịch")
    

    class Meta:
        verbose_name = "Giao Dịch"
        verbose_name_plural = "Sổ Giao Dịch"

    def clean(self):
        if self.loai_quy and self.loai_quy.is_khoa_so:
            raise ValidationError(f"Quỹ '{self.loai_quy.ten_quy}' đã bị khóa sổ. Không thể thêm giao dịch.")

    def __str__(self): return f"{self.ngay_tao.strftime('%d/%m/%Y')} - {self.ly_do} ({self.so_tien}đ)"

class LichSuWebhook(BaseModel):
    ma_giao_dich_ngan_hang = models.CharField(max_length=100, unique=True)
    so_tien = models.DecimalField(max_digits=12, decimal_places=0)
    raw_payload = models.JSONField(verbose_name="Dữ liệu JSON gốc từ NH")
    trang_thai_xu_ly = models.BooleanField(default=False, verbose_name="Đã gạch nợ tự động chưa?")
    
    class Meta:
        verbose_name = "Webhook"
        verbose_name_plural = "Lịch Sử Webhook Auto"

# ==========================================
# PHÂN HỆ GAMIFICATION & QUY TRÌNH (Rút gọn)
# ==========================================
class PhieuDeXuatChi(BaseModel):
    nguoi_de_xuat = models.ForeignKey(ThanhVien, on_delete=models.CASCADE, verbose_name="Người xin chi")
    so_tien = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Số tiền cần xin")
    muc_dich = models.TextField(verbose_name="Mục đích chi")
    trang_thai = models.CharField(max_length=20, choices=[('CHO_DUYET', 'Chờ duyệt'), ('DA_DUYET', 'Đã duyệt'), ('TU_CHOI', 'Từ chối')], default='CHO_DUYET')
    class Meta: verbose_name = "Đề Xuất"; verbose_name_plural = "Phiếu Đề Xuất Chi"

class KhieuNai(BaseModel):
    thanh_vien = models.ForeignKey(ThanhVien, on_delete=models.CASCADE, verbose_name="Người khiếu nại")
    tieu_de = models.CharField(max_length=255, verbose_name="Vấn đề")
    noi_dung = models.TextField(verbose_name="Chi tiết")
    trang_thai = models.CharField(max_length=20, choices=[('MO', 'Đang mở'), ('DANG_XU_LY', 'Đang xử lý'), ('DONG', 'Đã giải quyết')], default='MO')
    class Meta: verbose_name = "Khiếu Nại"; verbose_name_plural = "Quản Lý Khiếu Nại"

# 3. BẢNG CỬA HÀNG QUÀ TẶNG
class QuaTang(models.Model):
    LOAI_CHOICES = [
        ('VOUCHER', 'Voucher Giảm Quỹ'),
        ('HIEN_VAT', 'Quà Hiện Vật'),
        ('DAC_QUYEN', 'Thẻ Đặc Quyền'),
    ]
    ten_qua = models.CharField(max_length=255)
    loai_qua = models.CharField(max_length=20, choices=LOAI_CHOICES, default='HIEN_VAT')
    gia_xu = models.IntegerField(default=0)
    so_luong_kho = models.IntegerField(default=0)
    mo_ta = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.get_loai_qua_display()}] {self.ten_qua}"

class KhoDoThanhVien(models.Model):
    TRANG_THAI_CHOICES = [
        ('CHUA_DUNG', 'Chưa dùng'),
        ('DA_DUNG', 'Đã dùng/Đã nhận'),
    ]
    thanh_vien = models.ForeignKey('ThanhVien', on_delete=models.CASCADE)
    qua_tang = models.ForeignKey(QuaTang, on_delete=models.CASCADE)
    ngay_doi = models.DateTimeField(auto_now_add=True)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHUA_DUNG')
    
    # Mã này sẽ được tạo tự động khi đổi quà
    ma_dinh_danh = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.ma_dinh_danh:
            # Tạo mã kiểu: VOUCHER-123-2026
            self.ma_dinh_danh = f"{self.qua_tang.loai_qua}-{self.thanh_vien.id}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

# 4. BẢNG KHO ĐỒ CỦA THÀNH VIÊN (Khi mua quà xong cất vào đây)
class KhoDoThanhVien(BaseModel):
    TRANG_THAI = [('CHUA_DUNG', 'Chưa sử dụng'), ('DA_DUNG', 'Đã sử dụng')]
    
    thanh_vien = models.ForeignKey('ThanhVien', on_delete=models.CASCADE, related_name='kho_do')
    qua_tang = models.ForeignKey(QuaTang, on_delete=models.CASCADE)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI, default='CHUA_DUNG')
    ngay_mua = models.DateTimeField(auto_now_add=True)
    ngay_su_dung = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kho Đồ"
        verbose_name_plural = "4. Kho Đồ Thành Viên"

# 1. BẢNG CẤU HÌNH NHIỆM VỤ
class NhiemVu(BaseModel):
    LOAI_NV = [
        ('AUTO_NOP_QUY', 'Tự động: Đóng quỹ'),
        ('AUTO_TUONG_TAC', 'Tự động: Tương tác web'),
        ('MANUAL_ADMIN', 'Thủ công: Admin duyệt')
    ]
    ten_nhiem_vu = models.CharField(max_length=255, verbose_name="Tên nhiệm vụ")
    mo_ta = models.TextField(verbose_name="Mô tả & Điều kiện")
    loai_nhiem_vu = models.CharField(max_length=20, choices=LOAI_NV, default='AUTO_NOP_QUY')
    phan_thuong_xu = models.IntegerField(default=10, verbose_name="Mức thưởng (Xu)")
    is_active = models.BooleanField(default=True, verbose_name="Đang mở")
    
    class Meta:
        verbose_name = "Nhiệm Vụ"
        verbose_name_plural = "1. Quản Lý Nhiệm Vụ"
    
# 2. BẢNG LỊCH SỬ NHẬN XU (Sổ phụ chống Hack)
# Dùng để track xem tiền từ đâu ra, và chặn user nhận 1 nhiệm vụ 2 lần
class LichSuGiaoDichXu(BaseModel):
    LOAI_GD = [('CONG_XU', 'Cộng Xu (+)'), ('TRU_XU', 'Tiêu Xu (-)')]
    
    thanh_vien = models.ForeignKey('ThanhVien', on_delete=models.CASCADE, related_name='lich_su_xu')
    loai_giao_dich = models.CharField(max_length=10, choices=LOAI_GD)
    so_xu = models.IntegerField(verbose_name="Số lượng Xu (+/-)")
    ly_do = models.CharField(max_length=255, verbose_name="Lý do (Làm NV gì / Mua gì)")
    nhiem_vu_lien_quan = models.ForeignKey(NhiemVu, null=True, blank=True, on_delete=models.SET_NULL)
    ngay_thuc_hien = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Giao Dịch Xu"
        verbose_name_plural = "2. Lịch Sử Biến Động Xu"

class BieuQuyet(BaseModel):
    cau_hoi = models.CharField(max_length=255, verbose_name="Câu hỏi biểu quyết")
    han_chot = models.DateTimeField(verbose_name="Hạn chót vote")
    dang_mo = models.BooleanField(default=True, verbose_name="Đang diễn ra")
    so_tien_dau_tu = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Số tiền đề xuất đầu tư")
    loai_quy = models.ForeignKey('LoaiQuy', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Quỹ sử dụng đầu tư")
    trang_thai_duyet = models.CharField(max_length=20, choices=[('PENDING', 'Chờ gom phiếu'), ('APPROVED', 'Đã thông qua'), ('REJECTED', 'Bị từ chối')], default='PENDING', verbose_name="Trạng thái phê duyệt")
    class Meta: verbose_name = "Khảo Sát"; verbose_name_plural = "Bầu Cử / Khảo Sát"

class PhuongAnBieuQuyet(BaseModel):
    # Liên kết với bảng BieuQuyet ở trên. Dùng related_name='cac_phuong_an' để móc dữ liệu ra HTML cho dễ
    bieu_quyet = models.ForeignKey(BieuQuyet, on_delete=models.CASCADE, related_name='cac_phuong_an')
    noi_dung = models.CharField(max_length=255, verbose_name="Nội dung phương án (VD: Đi Vũng Tàu)")
    luot_chon = models.IntegerField(default=0, verbose_name="Số người đã vote")

    class Meta:
        verbose_name = "Phương Án"
        verbose_name_plural = "Các Phương Án"

    def __str__(self):
        return self.noi_dung
    
class ChiTietBinhChon(BaseModel):
    bieu_quyet = models.ForeignKey(BieuQuyet, on_delete=models.CASCADE)
    phuong_an = models.ForeignKey(PhuongAnBieuQuyet, on_delete=models.CASCADE)
    thanh_vien = models.ForeignKey('ThanhVien', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Chi tiết Vote"
        verbose_name_plural = "Lịch sử Vote chi tiết"
        # Đảm bảo 1 người chỉ có 1 phiếu cho 1 câu hỏi
        unique_together = ('bieu_quyet', 'thanh_vien')

class QATestingLog(models.Model):
    nguoi_test = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    loai_test = models.CharField(max_length=100, verbose_name="Kịch bản giả lập")
    du_lieu_phat_sinh = models.JSONField(verbose_name="Dữ liệu Data-Seed")
    trang_thai = models.CharField(max_length=50, default="SUCCESS")
    thoi_gian_test = models.DateTimeField(auto_now_add=True)
    class Meta: verbose_name = "Log QA"; verbose_name_plural = "Lịch Sử Test QA"
class HuyHieu(BaseModel):
    ten_huy_hieu = models.CharField(max_length=100, verbose_name="Tên Huy hiệu")
    link_icon = models.CharField(max_length=255, blank=True, null=True, verbose_name="Icon/Emoji")
    mo_ta = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    diem_yeu_cau = models.IntegerField(default=0, verbose_name="Điểm yêu cầu")
    
    class Meta: 
        verbose_name = "Huy Hiệu"
        verbose_name_plural = "Danh Sách Huy Hiệu"
        
    def __str__(self): return self.ten_huy_hieu

class HuyHieuThanhVien(BaseModel):
    thanh_vien = models.ForeignKey(ThanhVien, on_delete=models.CASCADE)
    huy_hieu = models.ForeignKey(HuyHieu, on_delete=models.CASCADE)
    ngay_dat_duoc = models.DateTimeField(default=timezone.now)
    
    class Meta: 
        verbose_name = "Cấp Phát Huy Hiệu"
        verbose_name_plural = "Lịch Sử Cấp Huy Hiệu"

class ThongBaoBuuTa(BaseModel):
    class Type(models.TextChoices):
        SYSTEM = 'SYSTEM', '⚡ Hệ thống'
        REMIND = 'REMIND', '📢 Nhắc nợ'
        FINANCE = 'FINANCE', '💰 Tài chính'

    nguoi_nhan = models.ForeignKey(User, on_delete=models.CASCADE, related_name='thong_bao_receivers', verbose_name="Người nhận")
    tieu_de = models.CharField(max_length=255, verbose_name="Tiêu đề")
    noi_dung = models.TextField(verbose_name="Nội dung chi tiết")
    is_read = models.BooleanField(default=False, verbose_name="Đã đọc?")
    link_url = models.CharField(max_length=255, blank=True, null=True, verbose_name="Link liên kết")
    loai = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM, verbose_name="Phân loại")

    def __str__(self):
        return f"[{self.get_loai_display()}] - {self.tieu_de}"

    class Meta:
        verbose_name = "Bưu tá Hệ thống"
        verbose_name_plural = "Bưu tá Hệ thống"
@receiver(post_save, sender=GiaoDich)
def tu_dong_cap_nhat_tien_do(sender, instance, created, **kwargs):
    # Chỉ chạy khi giao dịch nộp tiền (THU) và ĐÃ XÁC NHẬN
    if instance.loai == 'THU' and instance.da_xac_nhan and instance.dot_thu and instance.thanh_vien:
        from .models import TienDoDongQuy
        tiendo, _ = TienDoDongQuy.objects.get_or_create(
            dot_thu=instance.dot_thu,
            thanh_vien=instance.thanh_vien,
            defaults={'so_tien_can_nop': instance.dot_thu.so_tien_moi_nguoi, 'so_tien_da_nop': 0}
        )
        # Tính lại tổng tiền đã nộp thực tế từ các giao dịch đã xác nhận
        tong_da_nop = GiaoDich.objects.filter(
            thanh_vien=instance.thanh_vien, 
            dot_thu=instance.dot_thu, 
            da_xac_nhan=True, 
            loai='THU'
        ).aggregate(models.Sum('so_tien'))['so_tien__sum'] or 0
        
        tiendo.so_tien_da_nop = tong_da_nop
        tiendo.trang_thai = 'DU' if tong_da_nop >= tiendo.so_tien_can_nop else 'THIEU'
        tiendo.save()
@receiver(post_save, sender=GiaoDich)
def tu_dong_cap_nhat_tien_do(sender, instance, created, **kwargs):
    # Chỉ xử lý khi là giao dịch THU, có đợt thu và đã được XÁC NHẬN (da_xac_nhan=True)
    if instance.loai == 'THU' and instance.da_xac_nhan and instance.dot_thu and instance.thanh_vien:
        from .models import TienDoDongQuy
        tiendo, _ = TienDoDongQuy.objects.get_or_create(
            dot_thu=instance.dot_thu,
            thanh_vien=instance.thanh_vien,
            defaults={'so_tien_can_nop': instance.dot_thu.so_tien_moi_nguoi}
        )
        # Tính lại tổng tiền đã nộp dựa trên các giao dịch ĐÃ XÁC NHẬN
        tong_da_nop = GiaoDich.objects.filter(
            thanh_vien=instance.thanh_vien,
            dot_thu=instance.dot_thu,
            da_xac_nhan=True,
            loai='THU'
        ).aggregate(Sum('so_tien'))['so_tien__sum'] or 0
        
        tiendo.so_tien_da_nop = tong_da_nop
        tiendo.trang_thai = 'DU' if tong_da_nop >= tiendo.so_tien_can_nop else 'THIEU'
        tiendo.save()
# 1. Quỹ lớp & Trạng thái vòng đời (Giai đoạn 1 -> Giai đoạn 4)
class ClassFund(models.Model):
    name = models.CharField(max_length=100)
    total_cash = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)   # Tiền mặt khả dụng
    total_invest = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) # Tiền gửi đầu tư sinh lãi
    status = models.CharField(max_length=20, default='ACTIVE')                        # ACTIVE, FREEZING, CLOSED
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

# 2. Đợt thu quỹ (Giai đoạn 1)
class CollectionPeriod(models.Model):
    fund = models.ForeignKey(ClassFund, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    amount_required = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"{self.title} - {self.fund.name}"

# 3. Sổ giao dịch và đối soát (Giai đoạn 1 & 4)
class Transaction(models.Model):
    fund = models.ForeignKey(ClassFund, on_delete=models.CASCADE)
    collection_period = models.ForeignKey(CollectionPeriod, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Mã định danh đối soát")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    type = models.CharField(max_length=10) # THU, CHI, LAI, HOAN_TIEN
    status = models.CharField(max_length=20, default='PENDING') # PENDING, SUCCESS, FAILED
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_id} - {self.type} - {self.amount}"

# 4. Đề xuất đầu tư (Giai đoạn 2)
class InvestmentProposal(models.Model):
    fund = models.ForeignKey(ClassFund, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='PENDING') # PENDING, APPROVED, REJECTED
    expired_at = models.DateTimeField() # Hạn chót 3 ngày để Cron Job quét ngầm

    def __str__(self):
        return self.title

# 5. Chi tiết phiếu bầu của thành viên (Giai đoạn 2)
class ProposalVote(models.Model):
    proposal = models.ForeignKey(InvestmentProposal, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    choice = models.CharField(max_length=10) # VOTE_YES, VOTE_NO, AUTO_YES
    voted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.proposal.title} - {self.choice}"