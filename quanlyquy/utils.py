# File: quanlyquy/utils.py

def format_money(value):
    """
    Định dạng tiền tệ kiểu Việt Nam (VD: 2.210.000)
    """
    if not value:
        return "0"
    return "{:,.0f}".format(value).replace(',', '.')