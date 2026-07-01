import sys
import io
import json
import traceback
from .views import check_and_reward_quest
from datetime import timedelta


from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from .models import GiaoDich
from decimal import Decimal

# Import đầy đủ các Models
from .models import GiaoDich, ThanhVien, LoaiQuy, DotThu, MucTieuQuy, LichSuGiaoDichXu, KhoDoThanhVien, QuaTang, HuyHieu, HuyHieuThanhVien, PhuongAnBieuQuyet,BieuQuyet, ChiTietBinhChon
from .utils import format_money
try:
    from google import genai
except ImportError:
    pass

# --- HÀM HỖ TRỢ XỬ LÝ SỐ TIỀN ---
def clean_amount(amount_str):
    if not amount_str: return 0
    return int(str(amount_str).replace('.', '').replace(',', ''))

# ==========================================
# 1. API NỘP QUỸ (GỘP CHUNG VÍ WEB, TIỀN MẶT, QR VÀ CỘNG XU)
# ==========================================
@csrf_exempt  
@login_required
@transaction.atomic 
def api_nop_quy(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
        
    try:
        data = json.loads(request.body)
        dot_thu_id = data.get('dot_thu_id')
        muc_tieu_id = data.get('muc_tieu_id')
        
        # Lọc sạch chuỗi tiền tệ (Xóa dấu chấm, chữ đ...)
        so_tien_raw = str(data.get('so_tien', '0')).replace(',', '').replace('.', '').replace('đ', '').strip()
        so_tien = int(so_tien_raw) if so_tien_raw.isdigit() else 0
        
        if so_tien <= 0:
            return JsonResponse({'status': 'error', 'message': 'Số tiền nộp phải lớn hơn 0đ!'})
        
        phuong_thuc = data.get('phuong_thuc', 'CASH')
        ly_do = data.get('ly_do', 'Đóng quỹ lớp')
        is_an_danh = data.get('is_an_danh', False)
        
        # 1. Tìm hồ sơ thành viên
        tv = ThanhVien.objects.filter(user=request.user).first()
        if not tv and getattr(request.user, 'mssv', ''):
            tv = ThanhVien.objects.filter(mssv=request.user.mssv).first()
        if not tv and getattr(request.user, 'email', ''):
            tv = ThanhVien.objects.filter(email=request.user.email).first()
            
        if not tv:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy hồ sơ thành viên!'})
            
        # 2. Định vị Quỹ & Đợt Thu/Mục Tiêu
        dot_thu_obj = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else None
        muc_tieu_obj = MucTieuQuy.objects.filter(id=muc_tieu_id).first() if muc_tieu_id else None
        
        loai_quy = dot_thu_obj.loai_quy if dot_thu_obj else (LoaiQuy.objects.filter(lop_hoc=tv.lop_hoc).first() if tv.lop_hoc else LoaiQuy.objects.first())
        if not loai_quy:
            return JsonResponse({'status': 'error', 'message': 'Hệ thống chưa có Quỹ. Vui lòng tạo quỹ!'})

        da_xac_nhan = False
        msg_thanh_cong = ""
        
        # 3. 🌟 XỬ LÝ THEO TỪNG PHƯƠNG THỨC THANH TOÁN (ĐÃ GỘP VÀO LÕI ĐIỀU HƯỚNG)
        if phuong_thuc == 'WEB_WALLET':
            # Kiểm tra số dư ví Web kỹ càng
            so_du_hien_tai = tv.so_du_vi_web or Decimal('0')
            if so_du_hien_tai < so_tien:
                # 🔥 KHÔNG ĐỦ TIỀN: Báo lỗi và gợi ý chuyển hướng qua trang nạp ví
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Ví Web của sếp không đủ lúa (Hiện có {format_money(so_du_hien_tai)}đ). Sếp hãy vào mục "Nạp Tiền" để bơm thêm nhé!',
                    'action': 'redirect_to_deposit'
                })
            
            # ĐỦ TIỀN: Tiến hành khấu trừ trực tiếp
            tv.so_du_vi_web -= so_tien
            tv.save()
            
            ly_do = f"Trích ví Web: {ly_do}"
            da_xac_nhan = True # Ví Web trừ tiền thật -> Duyệt luôn!
            msg_thanh_cong = 'Trích ví Web nộp quỹ thành công! 🎉'
            
        elif phuong_thuc in ['TRANSFER', 'BANK', 'QR']:
            # 🌟 CASE GIẢ LẬP NGÂN HÀNG: Vì chưa liên kết ngân hàng thật nên hệ thống tự động giả duyệt thành công luôn
            da_xac_nhan = True 
            ly_do = f"[MÔ PHỎNG QR AUTO] {ly_do}"
            msg_thanh_cong = 'Hệ thống mô phỏng Ngân hàng đã ghi nhận! Xác nhận nạp tiền qua mã QR thành công. 🎉'
            
        elif phuong_thuc == 'CASH':
            # TIỀN MẶT: Giữ nguyên quy trình chuẩn là treo lại chờ thủ quỹ duyệt tay
            da_xac_nhan = False 
            ly_do = f"[TIỀN MẶT CHỜ DUYỆT] {ly_do}"
            msg_thanh_cong = 'Đã ghi nhận yêu cầu. Sếp vui lòng đưa tiền mặt tận tay cho Thủ quỹ để được phê duyệt nhập quỹ!'
            
        else:
            return JsonResponse({'status': 'error', 'message': 'Phương thức thanh toán không hợp lệ!'})
            
        # 4. TẠO GIAO DỊCH VÀO LỊCH SỬ SỔ QUỸ
        GiaoDich.objects.create(
            loai='THU', so_tien=so_tien, ly_do=ly_do, loai_quy=loai_quy, 
            thanh_vien=tv, dot_thu=dot_thu_obj, muc_tieu=muc_tieu_obj,
            is_an_danh=is_an_danh, phuong_thuc=phuong_thuc, 
            da_xac_nhan=da_xac_nhan, created_by=str(request.user.id)
        )

        # 5. 🌟 LOGIC PHẦN THƯỞNG & TIẾN ĐỘ (CHỈ CHẠY KHI GIAO DỊCH ĐÃ ĐƯỢC XÁC NHẬN - WALLET HOẶC GIẢ LẬP QR)
        xu_thuong = 0
        if da_xac_nhan:
            check_and_reward_quest(request, 'Công dân gương mẫu')

            # Cộng tiền vào tiến độ Mục Tiêu trực tiếp
            if muc_tieu_obj:
                tien_ht = getattr(muc_tieu_obj, 'tien_hien_tai', getattr(muc_tieu_obj, 'so_tien_hien_tai', 0)) or 0
                tien_mt = getattr(muc_tieu_obj, 'tien_muc_tieu', getattr(muc_tieu_obj, 'so_tien_muc_tieu', 0)) or 0
                tien_ht_moi = tien_ht + so_tien
                if hasattr(muc_tieu_obj, 'tien_hien_tai'): muc_tieu_obj.tien_hien_tai = tien_ht_moi
                elif hasattr(muc_tieu_obj, 'so_tien_hien_tai'): muc_tieu_obj.so_tien_hien_tai = tien_ht_moi
                if tien_ht_moi >= tien_mt and tien_mt > 0: muc_tieu_obj.hoan_thanh = True
                muc_tieu_obj.save()

            # Gỡ nợ xấu ngay lập tức
            if tv and tv.is_no_xau:
                tv.is_no_xau = False
                tv.save()

            # Tính toán Xu Gamification thưởng
            try:
                if hasattr(tv, 'vi_xu'):
                    xu_co_ban = int(so_tien / 10000)
                    xu_thuong = xu_co_ban
                    ly_do_thuong = f"Đóng quỹ ({xu_co_ban} Xu)"

                    if dot_thu_obj and dot_thu_obj.han_chot and timezone.now().date() <= (dot_thu_obj.han_chot - timedelta(days=3)):
                        xu_thuong += 10
                        ly_do_thuong += " + Kẻ Hủy Diệt Deadline (10 Xu)"

                    if xu_thuong > 0:
                        tv.vi_xu += xu_thuong
                        tv.tong_xu_tich_luy += xu_thuong
                        tv.save()
                        
                        LichSuGiaoDichXu.objects.create(
                            thanh_vien=tv, loai_giao_dich='CONG_XU', so_xu=xu_thuong, ly_do=ly_do_thuong
                        )
            except Exception:
                pass
            
            if xu_thuong > 0:
                msg_thanh_cong += f' Sếp được thưởng thêm +{xu_thuong} Xu!'

        return JsonResponse({'status': 'success', 'message': msg_thanh_cong, 'xu': xu_thuong})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'})
# ==========================================
# 2. API NỘP QUỸ HỘ (ĐẠI GIA BAO NUÔI)
# ==========================================
@csrf_exempt
@login_required
@transaction.atomic
def api_nop_quy_ho(request):
    try:
        data = json.loads(request.body)
        
        # 1. Tìm người ĐƯỢC nộp hộ (Receiver)
        thanh_vien_id = data.get('tv_id') or data.get('thanh_vien_id')
        tv_duoc_nop = ThanhVien.objects.get(id=thanh_vien_id)
        
        so_tien = clean_amount(data.get('so_tien'))
        dot_thu_id = data.get('dot_thu_id')
        dot_thu_obj = DotThu.objects.filter(id=dot_thu_id).first() if dot_thu_id else None
        
        quy = LoaiQuy.objects.first()
        if not quy:
            return JsonResponse({'status': 'error', 'message': 'Hệ thống chưa có Quỹ!'})

        # 2. LƯU GIAO DỊCH TIỀN (Ghi nhận người thụ hưởng là tv_duoc_nop)
        GiaoDich.objects.create(
            loai='THU', so_tien=so_tien, ly_do=data.get('ly_do') or f"Nộp quỹ hộ cho {tv_duoc_nop.ho_ten}",
            loai_quy=quy, thanh_vien=tv_duoc_nop, dot_thu=dot_thu_obj,
            created_by=str(request.user.id)
        )

        # 3. KÍCH HOẠT BẪY NHIỆM VỤ CHO NGƯỜI BẤM NÚT (Đại gia bao nuôi)
        # Chỗ này sẽ tự động cộng 50 Xu và gắn ID Quest để hiện chữ DONE
        check_and_reward_quest(request, 'Đại gia bao nuôi')

        # 4. Gỡ nợ xấu cho người được nộp hộ (nếu có)
        if tv_duoc_nop.is_no_xau:
            tv_duoc_nop.is_no_xau = False
            tv_duoc_nop.save()

        # 5. Thưởng Xu cơ bản cho người ĐƯỢC nộp hộ (để khuyến khích trả nợ)
        xu_co_ban = int(so_tien / 10000)
        if xu_co_ban > 0 and hasattr(tv_duoc_nop, 'vi_xu'):
            tv_duoc_nop.vi_xu += xu_co_ban
            tv_duoc_nop.save()
            LichSuGiaoDichXu.objects.create(
                thanh_vien=tv_duoc_nop, loai_giao_dich='CONG_XU', 
                so_xu=xu_co_ban, ly_do=f"Được {request.user.full_name} nộp hộ"
            )

        return JsonResponse({'status': 'success', 'message': f'Nộp hộ cho {tv_duoc_nop.ho_ten} thành công!'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'})
    
# ==========================================
# 3. API TẠM ỨNG TIỀN
# ==========================================
@csrf_exempt
@login_required
def api_tam_ung(request):
    try:
        data = json.loads(request.body)
        
        tv = ThanhVien.objects.filter(mssv=getattr(request.user, 'mssv', '')).first()
        if not tv:
            tv = ThanhVien.objects.filter(email=getattr(request.user, 'email', '')).first()
        
        quy = LoaiQuy.objects.first()
        if not quy:
            return JsonResponse({'status': 'error', 'message': 'Chưa có Quỹ. Hãy vào Admin tạo quỹ!'})

        so_tien = clean_amount(data.get('so_tien')) 
        ly_do = data.get('ly_do') or f"Tạm ứng cho {request.user.username}"
        
        GiaoDich.objects.create(loai='TU', so_tien=so_tien, ly_do=ly_do, loai_quy=quy, thanh_vien=tv)
        return JsonResponse({'status': 'success', 'message': 'Phiếu tạm ứng đã được lưu!'})
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': list(e.messages)[0]})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Lỗi: {str(e)}'})
# api_views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import GiaoDich

@login_required
def confirm_transaction_api(request, gd_id):
    # Chỉ Admin hoặc Lớp trưởng mới có quyền duyệt
    if request.user.role not in ['SUPER_ADMIN', 'LEADER']:
        return JsonResponse({'status': 'error', 'message': 'Không có quyền!'}, status=403)
    
    try:
        # Tìm giao dịch (kể cả những cái bị SoftDeleteManager lọc)
        gd = GiaoDich.all_objects.get(id=gd_id)
        gd.da_xac_nhan = True
        gd.save() # Lưu lại sẽ kích hoạt Signal ở Bước 2 để trừ nợ
        return JsonResponse({'status': 'success'})
    except GiaoDich.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Giao dịch không tồn tại!'}, status=404)
# ==========================================
# 4. API ĐIỀU CHUYỂN NỘI BỘ
# ==========================================
@csrf_exempt
@login_required
def api_chuyen_noi_bo(request):
    try:
        data = json.loads(request.body)
        so_tien = clean_amount(data.get('so_tien'))
        id_quy_di = data.get('id_quy_di')
        id_quy_den = data.get('id_quy_den')
        ly_do = data.get('ly_do') or "Chuyển tiền nội bộ"

        if id_quy_di == id_quy_den:
            return JsonResponse({'status': 'error', 'message': 'Quỹ nguồn và đích không được trùng nhau!'})

        quy_di = LoaiQuy.objects.get(id=id_quy_di)
        quy_den = LoaiQuy.objects.get(id=id_quy_den)

        GiaoDich.objects.create(loai='NB', so_tien=so_tien, ly_do=f"[-] {ly_do} (Sang {quy_den.ten_quy})", loai_quy=quy_di)
        GiaoDich.objects.create(loai='NB', so_tien=so_tien, ly_do=f"[+] {ly_do} (Từ {quy_di.ten_quy})", loai_quy=quy_den)

        return JsonResponse({'status': 'success', 'message': f'Đã điều chuyển {format_money(so_tien)}đ thành công!'})
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': list(e.messages)[0]})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==========================================
# 5. API TẠO QUỸ MỚI
# ==========================================      
@csrf_exempt
@login_required
def api_tao_quy(request):
    try:
        data = json.loads(request.body)
        ten_quy = data.get('ten_quy')
        if ten_quy:
            LoaiQuy.objects.create(ten_quy=ten_quy)
            return JsonResponse({'status': 'success', 'message': f'Đã tạo quỹ "{ten_quy}" thành công!'})
        return JsonResponse({'status': 'error', 'message': 'Tên quỹ không được để trống'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==========================================
# 6. API NHẮC NỢ QUA EMAIL
# ==========================================        
@csrf_exempt
@login_required
def api_nhac_no(request):
    try:
        data = json.loads(request.body)
        tv_id = data.get('tv_id')
        
        tv = ThanhVien.objects.filter(id=tv_id).first()
        if not tv:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy thành viên!'})

        return JsonResponse({'status': 'success', 'message': f'Đã gửi Email nhắc nợ đến {tv.ho_ten} ({tv.email or "chưa cập nhật email"})'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==========================================
# 7. API LẤY DỮ LIỆU VẼ BIỂU ĐỒ (CHART.JS)
# ==========================================
@csrf_exempt
@login_required
def api_chart_data(request):
    filter_type = request.GET.get('filter', '7days')
    now = timezone.now()
    labels = []; data_thu = []; data_chi = []

    def get_sum(start, end):
        stats = GiaoDich.objects.filter(ngay_tao__gte=start, ngay_tao__lte=end).aggregate(
            thu=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
            chi=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
        )
        return float(stats['thu'] or 0), float(stats['chi'] or 0)

    try:
        if filter_type == 'today':
            for i in range(0, 24, 3):
                labels.append(f"{i}h")
                start = now.replace(hour=i, minute=0, second=0)
                end = start + timedelta(hours=2, minutes=59)
                t, c = get_sum(start, end)
                data_thu.append(t); data_chi.append(c)

        elif filter_type in ['3days', '7days']:
            days = 3 if filter_type == '3days' else 7
            for i in range(days-1, -1, -1):
                d = now - timedelta(days=i)
                labels.append(d.strftime('%d/%m'))
                start = d.replace(hour=0, minute=0, second=0)
                end = d.replace(hour=23, minute=59, second=59)
                t, c = get_sum(start, end)
                data_thu.append(t); data_chi.append(c)

        elif filter_type == 'this_month':
            for i in range(1, now.day + 1):
                d = now.replace(day=i)
                labels.append(d.strftime('%d/%m'))
                start = d.replace(hour=0, minute=0, second=0)
                end = d.replace(hour=23, minute=59, second=59)
                t, c = get_sum(start, end)
                data_thu.append(t); data_chi.append(c)

        elif filter_type == 'this_quarter':
            current_quarter = (now.month - 1) // 3 + 1
            start_month = 3 * current_quarter - 2
            for i in range(3):
                m = start_month + i
                labels.append(f"Tháng {m}")
                t, c = get_sum(now.replace(month=m, day=1), now.replace(month=m, day=28) if m==2 else now.replace(month=m, day=30))
                data_thu.append(t); data_chi.append(c)

        elif filter_type == 'this_year':
            for m in range(1, 13):
                labels.append(f"T{m}")
                stats = GiaoDich.objects.filter(ngay_tao__year=now.year, ngay_tao__month=m).aggregate(
                    thu=Sum('so_tien', filter=Q(loai__in=['THU', 'LAI', 'HU'])),
                    chi=Sum('so_tien', filter=Q(loai__in=['CHI', 'TU']))
                )
                data_thu.append(float(stats['thu'] or 0)); data_chi.append(float(stats['chi'] or 0))

        return JsonResponse({'status': 'success', 'labels': labels, 'data_thu': data_thu, 'data_chi': data_chi})
    except Exception as e:
        return JsonResponse({'status': 'error', 'labels': ['Lỗi'], 'data_thu': [0], 'data_chi': [0]})
    
# ==========================================
# 8. API CHATBOT TRỢ LÝ ẢO (TÍCH HỢP GEMINI AI)
# ==========================================
@csrf_exempt
@login_required
def api_chatbot(request):
    try:
        check_and_reward_quest(request, 'Lời chào tới FundBot')
        data = json.loads(request.body.decode('utf-8'))
        message = data.get('message', '').strip().lower() 
        
        user_name = request.user.full_name or request.user.username
        
        tv_hien_tai = ThanhVien.objects.filter(mssv=getattr(request.user, 'mssv', '')).first()
        if not tv_hien_tai:
            tv_hien_tai = ThanhVien.objects.filter(email=getattr(request.user, 'email', '')).first()
        
        danh_sach_quy = LoaiQuy.objects.all()
        tong_du = sum([q.so_du_hien_tai for q in danh_sach_quy])
        chi_tiet_quy = "<br>".join([f"• **{q.ten_quy}**: {format_money(q.so_du_hien_tai)}đ" for q in danh_sach_quy])
        
        ds_no_xau = ThanhVien.objects.filter(is_no_xau=True)
        so_nguoi_no = ds_no_xau.count()
        ten_nguoi_no = ", ".join([tv.user.full_name for tv in ds_no_xau if tv.user]) if so_nguoi_no > 0 else "Không có ai"
        gd_cuoi = GiaoDich.objects.order_by('-ngay_tao').first()
        
        reply = f"Chào {user_name}! Mình là Trợ lý ảo của hệ thống quản lý quỹ lớp thông minh."

        if any(word in message for word in ['còn bao nhiêu', 'tổng tiền', 'số dư', 'giàu không']):
            reply = f"💰 Báo cáo sếp, tổng tài sản của lớp mình hiện tại là: **{format_money(tong_du)} VNĐ**.<br>{chi_tiet_quy}"
        elif any(word in message for word in ['mới nhất', 'gần đây', 'vừa chi', 'vừa thu']):
            if gd_cuoi:
                loai_gd = gd_cuoi.get_loai_display()
                icon = "🟢" if gd_cuoi.loai in ['THU', 'LAI'] else "🔴"
                reply = f"📅 Biến động mới nhất:<br>{icon} **{loai_gd}**: {format_money(gd_cuoi.so_tien)}đ<br>📝 Lý do: {gd_cuoi.ly_do}"
            else:
                reply = "Chưa có giao dịch nào được ghi nhận."
        elif any(word in message for word in ['nợ xấu', 'ai đang nợ']):
            reply = f"⚠️ Hiện tại có {so_nguoi_no} người đang bị đánh dấu nợ xấu: {ten_nguoi_no}"
        else:
            reply = f"Xin lỗi sếp, em chưa hiểu câu: '{message}'. Sếp thử hỏi về 'số dư', 'giao dịch mới nhất' xem sao ạ!"
            

        return JsonResponse({'status': 'success', 'reply': reply}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'status': 'error', 'reply': f'Lỗi Bot: {str(e)}'})

# ==========================================
# 9. API XÁC THỰC MÃ PIN
# ==========================================
@csrf_exempt
def api_verify_pin(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Vui lòng đăng nhập!"})
    
    try:
        data = json.loads(request.body)
        pin = data.get('pin', '')
        
        if len(pin) != 6:
            return JsonResponse({"status": "error", "message": "Mã PIN phải đủ 6 số!"})

        is_valid = False
        if getattr(request.user, 'secure_pin', None):
            is_valid = check_password(pin, request.user.secure_pin)
        elif pin == '123456': 
            is_valid = True

        if is_valid:
            return JsonResponse({"status": "success", "message": "Xác thực bảo mật thành công!"})
        else:
            return JsonResponse({"status": "error", "message": "Mã PIN không chính xác!"})
    except Exception as e:
         return JsonResponse({"status": "error", "message": f"Lỗi: {str(e)}"})
    


@csrf_exempt
@login_required
@transaction.atomic
def api_spin_gacha(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ nhận phương thức POST!'})
        
    try:
        user = request.user
        
        # Nhận diện chức vụ để xưng hô cho mượt
        is_admin = getattr(user, 'role', '') == 'ADMIN' or user.is_superuser
        xung_ho = "sếp" if is_admin else "bạn"
        danh_xung_hoa = "Sếp" if is_admin else "Bạn"
        
        # 1. TÌM HOẶC TẠO THÀNH VIÊN
        tv = ThanhVien.objects.filter(user=user).first()
        if not tv and getattr(user, 'mssv', ''):
            tv = ThanhVien.objects.filter(mssv=user.mssv).first()
        if not tv and getattr(user, 'email', ''): 
            tv = ThanhVien.objects.filter(email=user.email).first()
            
        if not tv:
            import time
            tv = ThanhVien.objects.create(
                ho_ten=user.full_name or user.username,
                mssv=user.mssv or f"ADMIN-{user.id}-{int(time.time())}",
                user=user,
                vi_xu=getattr(user, 'credit_score', 0)
            )
        elif not tv.user:
            tv.user = user
            tv.save()

        # [FIX LỖI ẢO MA]: ĐỒNG BỘ XU CHO ADMIN
        # Nếu sếp buff điểm trong Django Admin, hệ thống sẽ tự cập nhật vào ví thực tế
        if is_admin and getattr(user, 'credit_score', 0) > tv.vi_xu:
            tv.vi_xu = user.credit_score
            tv.save()

        # 2. KIỂM TRA SỐ DƯ
        if tv.vi_xu < 20:
            return JsonResponse({'status': 'error', 'message': f'{danh_xung_hoa} ơi, không đủ 20 Xu để quay! (Ví thực tế đang có {tv.vi_xu} Xu)'})

        # 3. QUAY GACHA VÀ TÍNH QUÀ
        import random
        rand = random.randint(1, 100)
        prize_xu, prize_type, voucher_name, angle, message = 0, "XU", "", 0, ""

        if rand <= 40: 
            angle = random.choice([345, 255, 105]); message = "Trượt rồi! Đen thôi đỏ quên đi."
        elif rand <= 65: 
            prize_xu = 10; angle = random.choice([315, 135]); message = "An ủi! Gỡ gạc được +10 Xu"
        elif rand <= 80: 
            prize_xu = 20; angle = random.choice([285, 75]); message = "Hú vía! Hòa vốn +20 Xu"
        elif rand <= 90: 
            prize_xu = 30; angle = random.choice([225, 15]); message = "Ngon lành! Lời được +30 Xu"
        elif rand <= 95: 
            prize_xu = 50; angle = 195; message = "Quá đã! Trúng quả đậm +50 Xu"
        elif rand <= 99: # 4% TRÚNG VOUCHER
            qua_tang = QuaTang.objects.filter(is_active=True, so_luong_kho__gt=0).order_by('?').first()
            if qua_tang:
                prize_type, voucher_name, angle = "VOUCHER", qua_tang.ten_qua, 45
                message = f"🎁 Đỉnh! {danh_xung_hoa} trúng quà: {voucher_name}"
                qua_tang.so_luong_kho -= 1
                qua_tang.save()
                KhoDoThanhVien.objects.create(thanh_vien=tv, qua_tang=qua_tang)
            else:
                prize_xu, angle, message = 100, 45, f"Quà hết rồi, bù {xung_ho} 100 Xu nè!"
        else: # 1% ĐỘC ĐẮC
            prize_xu, angle, message = 500, 165, "🔥 JACKPOT! NỔ ĐỘC ĐẮC +500 XU!"

        # 4. TRỪ XU VÀ LƯU LỊCH SỬ GIAO DỊCH
        tv.vi_xu -= 20
        if prize_xu > 0:
            tv.vi_xu += prize_xu
            tv.tong_xu_tich_luy += prize_xu
        tv.save()

        # Đồng bộ ngược lại cho User
        user.credit_score = tv.vi_xu 
        user.save()

        LichSuGiaoDichXu.objects.create(
            thanh_vien=tv, loai_giao_dich='TRU_XU', so_xu=20, 
            ly_do=f"Quay Gacha ({message})", created_by=str(user.id)
        )
        if prize_xu > 0:
            LichSuGiaoDichXu.objects.create(
                thanh_vien=tv, loai_giao_dich='CONG_XU', so_xu=prize_xu, 
                ly_do="Trúng thưởng Gacha", created_by=str(user.id)
            )
        
        check_and_reward_quest(request, 'Con nghiện Gacha')
        return JsonResponse({
            'status': 'success', 'message': message, 'angle': angle, 
            'prize': prize_xu, 'prize_type': prize_type, 'voucher_name': voucher_name,
            'new_balance': tv.vi_xu
        })
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'LỖI DATABASE: {str(e)}'})
# ==========================================
# API: VOTE KHẢO SÁT (BẢN BỌC THÉP CHỐNG CRASH)
# ==========================================
@csrf_exempt
@login_required
@transaction.atomic
def api_submit_vote(request):
    try:
        if request.method == 'POST':
            # Nhét import vào thẳng đây để đảm bảo 100% không bị sót
            from .models import PhuongAnBieuQuyet, ThanhVien, LichSuGiaoDichXu
            
            check_and_reward_quest(request, 'Tiếng nói cử tri')
            data = json.loads(request.body)
            poll_id = data.get('poll_id')
            phuong_an_id = data.get('phuong_an_id')
            user = request.user
            
            # 1. Tìm/Tạo hồ sơ thành viên
            tv = ThanhVien.objects.filter(user=user).first()
            if not tv and getattr(user, 'mssv', ''): tv = ThanhVien.objects.filter(mssv=user.mssv).first()
            if not tv and getattr(user, 'email', ''): tv = ThanhVien.objects.filter(email=user.email).first()
            
            if not tv:
                import time
                tv = ThanhVien.objects.create(
                    ho_ten=user.full_name or user.username,
                    mssv=user.mssv or f"ADMIN-{user.id}-{int(time.time())}",
                    user=user, vi_xu=getattr(user, 'credit_score', 0)
                )
            elif not tv.user:
                tv.user = user
                tv.save()

            if not tv: return JsonResponse({'status': 'error', 'message': 'Lỗi tài khoản!'})

            # 2. Check xem đã vote chưa
            da_vote = LichSuGiaoDichXu.objects.filter(thanh_vien=tv, ly_do=f"Vote khảo sát ID:{poll_id}").exists()
            if da_vote: return JsonResponse({'status': 'error', 'message': 'Sếp đã tham gia bình chọn này rồi!'})

            # 3. LÕI VOTE: TĂNG LƯỢT BÌNH CHỌN CHO PHƯƠNG ÁN ĐƯỢC CHỌN
            phuong_an = PhuongAnBieuQuyet.objects.filter(id=phuong_an_id).first()
            if phuong_an:
                phuong_an.luot_chon += 1
                phuong_an.save()
            # [MỚI CẤY VÀO]: Lưu lại bằng chứng đứa nào vote!
                ChiTietBinhChon.objects.create(
                    bieu_quyet_id=poll_id,
                    phuong_an=phuong_an,
                    thanh_vien=tv
                    )

            # 4. Trả thưởng 10 Xu
            tv.vi_xu += 10
            tv.tong_xu_tich_luy += 10
            tv.save()

            LichSuGiaoDichXu.objects.create(
                thanh_vien=tv, loai_giao_dich='CONG_XU', so_xu=10, 
                ly_do=f"Vote khảo sát ID:{poll_id}"
            )
            
            return JsonResponse({'status': 'success', 'message': 'Đã ghi nhận bình chọn! +10 Xu'})
            
    except Exception as e:
        import traceback
        traceback.print_exc() # In chi tiết lỗi ra màn hình đen (Terminal)
        # Ném đúng lỗi ra ngoài màn hình cho sếp xem thay vì báo mất kết nối
        return JsonResponse({'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'})

# ==========================================
# API 3: MUA ĐỒ TRONG SHOP (TRỪ XU)
# ==========================================
@csrf_exempt
@login_required
@transaction.atomic
def api_buy_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Lấy dữ liệu linh hoạt: kiểm tra cả 'item_id' và 'item_name'
            raw_id = data.get('item_id') or data.get('item_name')
            
            # 1. Tìm Thành Viên
            tv = ThanhVien.objects.filter(user=request.user).first()
            if not tv:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy hồ sơ thành viên!'})

            # 2. Tìm Quà Tặng (Thông minh hơn)
            # Thử tìm theo ID (nếu raw_id là số), nếu không thì tìm theo Tên
            item = None
            if str(raw_id).isdigit():
                item = QuaTang.objects.filter(id=int(raw_id)).first()
            
            if not item:
                item = QuaTang.objects.filter(ten_qua=raw_id).first()

            if not item:
                return JsonResponse({'status': 'error', 'message': f'Vật phẩm "{raw_id}" không tồn tại!'})

            # 3. Kiểm tra kho và xu
            if item.so_luong_kho <= 0:
                return JsonResponse({'status': 'error', 'message': 'Quà này đã hết hàng mất rồi!'})
                
            if tv.vi_xu < item.gia_xu:
                return JsonResponse({'status': 'error', 'message': f'Sếp chỉ có {tv.vi_xu} Xu, cần {item.gia_xu} Xu mới đổi được!'})

            # 4. Thực hiện giao dịch
            tv.vi_xu -= item.gia_xu
            tv.save()
            
            item.so_luong_kho -= 1
            item.save()
            
            # Tạo túi đồ và lịch sử
            from .models import KhoDoThanhVien # Đảm bảo đã import đúng
            KhoDoThanhVien.objects.create(thanh_vien=tv, qua_tang=item, trang_thai='CHUA_DUNG')
            
            LichSuGiaoDichXu.objects.create(
                thanh_vien=tv, 
                loai_giao_dich='TRU_XU', 
                so_xu=item.gia_xu, 
                ly_do=f"Mua {item.ten_qua} tại Shop"
            )

            return JsonResponse({'status': 'success', 'message': f'Chúc mừng sếp! Đã đổi thành công {item.ten_qua}.'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Lỗi Server: {str(e)}'})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'})