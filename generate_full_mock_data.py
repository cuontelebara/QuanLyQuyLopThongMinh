import os
import django
import random
from datetime import datetime, timedelta
import pandas as pd

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quylop.settings')
django.setup()

from quanlyquy.models import GiaoDich, ThanhVien, LoaiQuy

# Xóa dữ liệu cũ
print("🧹 Đang xóa dữ liệu Giao dịch cũ...")
GiaoDich.objects.all().delete()

# Lấy dữ liệu cần thiết
members = list(ThanhVien.objects.all())
funds = list(LoaiQuy.objects.all())

if not members or not funds:
    print("❌ Lỗi: Bạn cần tạo ít nhất 1 Thành Viên và 1 Loại Quỹ trước khi chạy script này!")
    exit()

# Dữ liệu mẫu cho lý do
ly_do_thu = [
    " nộp quỹ tháng ",
    " đóng tiền liên hoan nhóm",
    " đóng quỹ đợt thu tháng ",
    " đóng tiền áo lớp",
    " hoàn ứng mua đồ"
]

ly_do_chi = [
    "Chi mua nước uống",
    "Tạm ứng mua văn phòng phẩm",
    "Chi tiền in test case",
    "Chi liên hoan nhóm",
    "Chi hỗ trợ Nguyễn Văn A",
    "Mua đồ trang trí lớp"
]

# Tạo dữ liệu cho 6 tháng gần nhất
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

giao_dich_list = []
tong_thu = 0
tong_chi = 0

print("🚀 Đang tạo 100 giao dịch mẫu...")

for i in range(100):
    # Tạo ngày ngẫu nhiên trong 6 tháng
    random_days = random.randint(0, 180)
    ngay_tao = start_date + timedelta(days=random_days)
    
    # Quyết định Thu hay Chi (70% là Thu)
    loai_nghiep_vu = random.choices(['THU', 'CHI'], weights=[70, 30])[0]
    
    # Tạo số tiền và lý do
    if loai_nghiep_vu == 'THU':
        so_tien = random.choices([20000, 50000, 100000, 200000], weights=[20, 40, 30, 10])[0]
        thanh_vien = random.choice(members)
        reason = f"{thanh_vien.ho_ten} {random.choice(ly_do_thu)}{ngay_tao.strftime('%m/%Y')}"
        
        # Thỉnh thoảng thêm lãi
        if random.random() < 0.1:
            so_tien = 5000
            loai_nghiep_vu = 'LAI'
            reason = "Lãi tiết kiệm ngân hàng tháng " + ngay_tao.strftime('%m/%Y')
            thanh_vien = None
            
        # Thỉnh thoảng thêm hoàn ứng
        if random.random() < 0.05:
            so_tien = 50000
            loai_nghiep_vu = 'HU'
            reason = "Hoàn ứng mua đồ dùng"
            thanh_vien = random.choice(members)

        tong_thu += so_tien
        
    else: # CHI
        so_tien = random.choices([20000, 30000, 100000, 150000, 500000], weights=[20, 30, 20, 20, 10])[0]
        thanh_vien = random.choice(members)
        reason = f"{random.choice(ly_do_chi)}"
        
        # Thỉnh thoảng thêm tạm ứng
        if random.random() < 0.15:
            so_tien = 200000
            loai_nghiep_vu = 'TU'
            reason = "Tạm ứng mua văn phòng phẩm"
            thanh_vien = random.choice(members)
            
        tong_chi += so_tien

    # Tạo đối tượng GiaoDich (không lưu vào DB ngay)
    gd = GiaoDich(
        ngay_tao=ngay_tao,
        loai=loai_nghiep_vu,
        so_tien=so_tien,
        loai_quy=random.choice(funds),
        thanh_vien=thanh_vien,
        ly_do=reason
    )
    giao_dich_list.append(gd)

# Lưu tất cả vào DB (chỉ 1 lần truy vấn)
GiaoDich.objects.bulk_create(giao_dich_list)

print("✅ Đã tạo xong 100 giao dịch!")
print(f"📊 Tổng Thu: {tong_thu:,.0f} đ | Tổng Chi: {tong_chi:,.0f} đ | Số dư: {tong_thu-tong_chi:,.0f} đ")
print("👉 Vào trang Admin để xem kết quả rực rỡ!")