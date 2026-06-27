import os
import django
import random
from datetime import timedelta

# 1. Kết nối với môi trường Django của sếp
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quylop.settings")
django.setup()

from django.utils import timezone
from quanlyquy.models import (
    User, LopHoc, ThanhVien, LoaiQuy, DanhMucThuChi, 
    GiaoDich, DotThu, TaiSan, MucTieuQuy
)

def run_seeder():
    print("🚀 Đang khởi tạo dữ liệu mẫu (Mock Data) cho FundSmart...")
    print("🧹 Đang dọn dẹp dữ liệu cũ...")
    GiaoDich.objects.all().delete()
    ThanhVien.objects.all().delete()
    # Chỉ xóa các user clone (để tránh xóa nhầm tài khoản Admin của sếp)
    User.objects.filter(username__startswith='user_sv').delete()

    # 1. Tạo Lớp học
    lop, _ = LopHoc.objects.get_or_create(ten_lop="Công Nghệ Thông Tin K22", nien_khoa="2022-2026")
    
    # 2. Tạo Quỹ
    quy, _ = LoaiQuy.objects.get_or_create(ten_quy="Quỹ Lớp Tiền Mặt (Chính)", defaults={'is_khoa_so': False})

    # 3. Tạo Danh mục Thu/Chi
    dm_thu_quy, _ = DanhMucThuChi.objects.get_or_create(ten_danh_muc="Đóng quỹ định kỳ", loai="THU")
    dm_tai_tro, _ = DanhMucThuChi.objects.get_or_create(ten_danh_muc="Quỹ hỗ trợ đoàn thanh niên", loai="THU")
    dm_an_uong, _ = DanhMucThuChi.objects.get_or_create(ten_danh_muc="Liên hoan / Ăn uống", loai="CHI")
    dm_mua_sam, _ = DanhMucThuChi.objects.get_or_create(ten_danh_muc="Mua sắm vật liệu cá nhân", loai="CHI")
    dm_tham_hoi, _ = DanhMucThuChi.objects.get_or_create(ten_danh_muc="Thăm hỏi, viếng thăm người bệnh", loai="CHI")

    # 4. Tạo Đợt Thu
    dot_thu, _ = DotThu.objects.get_or_create(
        ten_dot="Thu quỹ Học kỳ 2 (2024)",
        loai_quy=quy,
        defaults={'so_tien_moi_nguoi': 200000, 'han_chot': timezone.now() + timedelta(days=30)}
    )

    # 5. Tạo 20 Thành viên & Tài khoản
    ho_list = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng"]
    dem_list = ["Văn", "Thị", "Minh", "Hữu", "Thu", "Hải", "Ngọc", "Tuấn", "Đức", "Hoài"]
    ten_list = ["Quan", "Bình", "Cường", "Dung", "Hùng", "Hương", "Linh", "Nghĩa", "Phương", "Trang", "Tuấn", "Thành", "Thủy", "Nhan", "Vy", "Quang", "Anh", "Dương", "Sơn", "Tùng"]

    thanh_viens = []
    print("⏳ Đang tạo 20 sinh viên...")
    for i in range(1, 21):
        ho_ten = f"{random.choice(ho_list)} {random.choice(dem_list)} {random.choice(ten_list)}"
        mssv = f"228060{i:04d}"
        username = f"user_sv{i}"
        
        user, created = User.objects.get_or_create(username=username, defaults={
            'full_name': ho_ten, 'email': f"{username}@gmail.com", 'role': 'MEMBER', 'mssv': mssv
        })
        if created:
            user.set_password("123456")
            user.save()

        tv, _ = ThanhVien.objects.get_or_create(mssv=mssv, defaults={
            'ho_ten': ho_ten, 'gender': random.choice(['NAM', 'NU']),
            'phone': f"090{random.randint(1000000, 9999999)}", 'lop_hoc': lop,
            'email': user.email, 'user': user, 'is_no_xau': random.choice([True, False, False])
        })
        thanh_viens.append(tv)

    # 6. Tạo 100 Giao dịch rải rác 6 tháng để vẽ Biểu đồ Chart.js
    print("⏳ Đang bơm 100 giao dịch lịch sử vào Database...")
    now = timezone.now()
    for i in range(100):
        # Chọn ngày lùi lại ngẫu nhiên (từ hôm nay lùi về tối đa 180 ngày trước)
        random_days_ago = random.randint(0, 180)
        ngay_gd = now - timedelta(days=random_days_ago)
        
        is_thu = random.choice([True, True, False]) # Tỉ lệ Thu nhiều hơn Chi để quỹ luôn dương
        
        if is_thu:
            loai_gd = 'THU'
            danh_muc = random.choice([dm_thu_quy, dm_thu_quy, dm_thu_quy, dm_tai_tro])
            so_tien = random.choice([10000, 20000, 30000, 40000, 50000, 100000, 200000, 500000])
            ly_do = f"Nộp tiền {danh_muc.ten_danh_muc.lower()}"
            tv_gd = random.choice(thanh_viens)
            is_an_danh = random.choice([True, False, False, False])
        else:
            loai_gd = 'CHI'
            danh_muc = random.choice([dm_an_uong, dm_mua_sam, dm_tham_hoi])
            so_tien = random.choice([150000, 300000, 500000, 1000000])
            ly_do = f"Chi trả cho {danh_muc.ten_danh_muc.lower()}"
            tv_gd = None 
            is_an_danh = False

        # Tạo giao dịch
        gd = GiaoDich.objects.create(
            loai=loai_gd, so_tien=so_tien, loai_quy=quy,
            danh_muc=danh_muc, thanh_vien=tv_gd,
            dot_thu=dot_thu if danh_muc == dm_thu_quy else None,
            ly_do=ly_do, is_an_danh=is_an_danh, created_by="Admin Tool"
        )
        # Ép hệ thống lưu lại ngày giả lập thay vì ngày hôm nay
        GiaoDich.objects.filter(id=gd.id).update(ngay_tao=ngay_gd, created_at=ngay_gd)

    # 7. Thêm Tài sản & Mục tiêu
    TaiSan.objects.get_or_create(ten_tai_san="Loa kéo Bluetooth", gia_mua=2500000, ti_le_khau_hao=20, ngay_mua=now - timedelta(days=200))
    TaiSan.objects.get_or_create(ten_tai_san="Dụng cụ y tế lớp", gia_mua=350000, ti_le_khau_hao=50, ngay_mua=now - timedelta(days=100))
    MucTieuQuy.objects.get_or_create(ten_muc_tieu="Teambuilding Nha Trang", so_tien_muc_tieu=105000000, so_tien_hien_tai=3500000)

    print("🎉 HOÀN TẤT! Dữ liệu đã được bơm đầy đủ. Sếp hãy mở Web lên xem thành quả nhé!")

if __name__ == '__main__':
    run_seeder()