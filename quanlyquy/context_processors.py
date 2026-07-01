from .models import ThanhVien

def thong_tin_vi_thanh_vien(request):
    """ Hàm vạn năng: Tự động truyền số dư ví vào TẤT CẢ các trang trên hệ thống """
    if request.user.is_authenticated:
        tv_hien_tai = ThanhVien.objects.filter(user=request.user).first()
        return {'tv_hien_tai': tv_hien_tai}
    return {'tv_hien_tai': None}