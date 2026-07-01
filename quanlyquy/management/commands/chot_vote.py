from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from quanlyquy.models import BieuQuyet, ChiTietBinhChon, ThanhVien, GiaoDich

class Command(BaseCommand):
    help = 'Tự động chốt các cuộc biểu quyết sau 3 ngày và ép những người im lặng thành ĐỒNG Ý'

    def handle(self, *args, **options):
        now = timezone.now()
        # Tìm các cuộc biểu quyết đã tạo quá 3 ngày (hoặc quá hạn chót han_chot) và vẫn đang mở
        thoi_gian_han_chot = now - timedelta(days=3)
        
        # Sếp có thể filter theo ngày tạo hoặc theo trường han_chot <= now của sếp
        cac_cuoc_vote = BieuQuyet.objects.filter(dang_mo=True, han_chot__lte=now)

        if not cac_cuoc_vote.exists():
            self.stdout.write(self.style.WARNING("▶️ Không có cuộc biểu quyết nào quá hạn cần xử lý."))
            return

        for vote_item in cac_cuoc_vote:
            # Lấy tổng số thành viên thực tế trong lớp học thuộc quỹ này
            if not vote_item.loai_quy or not vote_item.loai_quy.lop_hoc:
                continue
                
            lop = vote_item.loai_quy.lop_hoc
            tat_ca_tv = ThanhVien.objects.filter(lop_hoc=lop, deleted_at__isnull=True)
            total_members = tat_ca_tv.count()
            
            if total_members == 0:
                continue

            with transaction.atomic():
                # 1. Tìm danh sách ID những thành viên đã thực hiện bấm Vote thực tế
                voted_member_ids = ChiTietBinhChon.objects.filter(bieu_quyet=vote_item).values_list('thanh_vien_id', flat=True)
                
                # 2. Hệ thống tự động điền phiếu ĐỒNG Ý (AUTO_YES) hộ những người im lặng
                for member in tat_ca_tv:
                    if member.id not in voted_member_ids:
                        ChiTietBinhChon.objects.create(
                            bieu_quyet=vote_item,
                            thanh_vien=member,
                            phuong_an=None,  # Không chọn phương án cụ thể nào
                            created_by="SYSTEM_CRON"
                        )
                
                # 3. Tính toán tỷ lệ phê duyệt dòng tiền
                total_votes = ChiTietBinhChon.objects.filter(bieu_quyet=vote_item).count()
                yes_percentage = (total_votes / total_members) * 100
                
                # 4. Nếu đạt điều kiện đồng thuận vĩ mô >= 70%, tự động trích tiền đi đầu tư ngân hàng
                if yes_percentage >= 70.0 and getattr(vote_item, 'so_tien_dau_tu', 0) > 0:
                    vote_item.trang_thai_duyet = 'APPROVED'
                    vote_item.dang_mo = False
                    vote_item.save()
                    
                    # Chèn lệnh chi tiền quỹ để giải ngân gói đầu tư
                    GiaoDich.objects.create(
                        loai='CHI',
                        so_tien=vote_item.so_tien_dau_tu,
                        loai_quy=vote_item.loai_quy,
                        phuong_thuc='BANK',
                        da_xac_nhan=True,
                        ly_do=f"💥 [ĐẦU TƯ] Tự động giải ngân gửi tiết kiệm theo Biểu quyết ID {vote_item.id}"
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Biểu quyết {vote_item.id} THÔNG QUA -> Đã trích {vote_item.so_tien_dau_tu}đ đi đầu tư."))
                else:
                    vote_item.trang_thai_duyet = 'REJECTED'
                    vote_item.dang_mo = False
                    vote_item.save()
                    self.stdout.write(self.style.WARNING(f"❌ Biểu quyết {vote_item.id} BỊ HỦY do không đủ tỷ lệ đồng thuận."))