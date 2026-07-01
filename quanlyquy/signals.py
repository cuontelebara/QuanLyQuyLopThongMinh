from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DotThu, ThanhVien, SuKienNhacViec

@receiver(post_save, sender=DotThu)
def tu_dong_thong_bao_dong_quy(sender, instance, created, **kwargs):
    if created and instance.loai_quy.lop_hoc:
        # 1. Tìm tất cả thành viên thuộc lớp của Quỹ này
        danh_sach_tv = ThanhVien.objects.filter(lop_hoc=instance.loai_quy.lop_hoc)
        
        # 2. Tạo thông báo / Sự kiện nhắc việc cho từng thành viên
        for tv in danh_sach_tv:
            SuKienNhacViec.objects.create(
                ten_su_kien=f"📣 ĐỢT THU MỚI: {instance.ten_dot}",
                mo_ta=f"Quỹ lớp '{instance.loai_quy.ten_quy}' yêu cầu đóng {instance.so_tien_moi_nguoi}đ. Hạn chốt: {instance.han_chot}",
                # Nếu model SuKienNhacViec của sếp có trường thanh_vien hoặc user thì gán vào đây
            )