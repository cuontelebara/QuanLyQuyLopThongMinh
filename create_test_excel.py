import pandas as pd
import random

# Tạo dữ liệu giả lập sao kê ngân hàng
data = {
    'Ngày': ['06/03/2026', '06/03/2026', '05/03/2026', '04/03/2026', '03/03/2026'],
    'Nội dung': [
        'QUAN TRAN NOP QUY THANG 3',
        'CHI TIEN MUA LOA KEO LOP',
        'LAI TIEN GUI THANG 02',
        'TAM UNG DI MUA DO AN 20/11',
        'HOAN UNG TIEN DU MUA DO AN'
    ],
    # Cột này quan trọng nhất, phải khớp tên với logic trong admin.py
    'Số tiền': [100000, -2500000, 15200, -500000, 45000] 
}

# Tạo DataFrame
df = pd.DataFrame(data)

# Xuất ra file Excel
file_name = 'sao_ke_test.xlsx'
df.to_excel(file_name, index=False)

print(f"✅ Đã tạo file thành công: {file_name}")
print("👉 Bây giờ Quân vào Admin, chọn các giao dịch rồi upload file này lên để xem báo cáo nhé!")