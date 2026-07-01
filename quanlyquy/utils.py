def format_money(value):
    """
    Định dạng tiền tệ chuẩn VN:
    - Nếu là số nguyên: 100.000.338
    - Nếu có phần thập phân: 100.000.338,338
    """
    try:
        # Chuyển về float để xử lý số thập phân, nếu là None hoặc rỗng thì về 0
        val = float(value or 0)
        
        # Nếu là số nguyên (chia hết cho 1), hiển thị không phần lẻ
        if val.is_integer():
            return "{:,.0f}".format(val).replace(",", ".")
        
        # Nếu có phần lẻ, hiển thị đến 3 chữ số thập phân (để giữ lại 0.338)
        # Lưu ý: đổi dấu phẩy thành dấu chấm để khớp với yêu cầu của sếp
        return "{:,.3f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0"