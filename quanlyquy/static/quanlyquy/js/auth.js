// ==========================================
// 1. TỪ ĐIỂN ĐA NGÔN NGỮ (Bao gồm Quên mật khẩu)
// ==========================================
const translations = {
    vi: {
        current: "VN",
        // Trang Đăng nhập
        visualTitle: "Chào mừng trở lại!",
        visualDesc: "Nền tảng ICMS giúp bạn quản lý dòng tiền lớp học minh bạch, an toàn và hoàn toàn tự động.",
        formTitle: "Đăng nhập",
        formSubtitle: "Nhập thông tin để tiếp tục vào hệ thống",
        labelUser: "Tên đăng nhập / Username",
        labelPass: "Mật khẩu / Password",
        textRemember: "Ghi nhớ tôi",
        textForgot: "Quên mật khẩu?",
        textBtnLogin: "ĐĂNG NHẬP",
        textOr: "Hoặc đăng nhập bằng",
        textNewbie: "Tân binh lớp mình?",
        textCreateAcc: "Tạo tài khoản ngay",
        loading: "Đang xử lý...",
        // Trang Đăng ký
        regVisualTitle: "Chào tân binh!",
        regVisualDesc: "Gia nhập cộng đồng FundFlow để quản lý tài chính lớp học một cách chuyên nghiệp nhất.",
        regFormTitle: "Tạo tài khoản",
        regFormSubtitle: "Hoàn thành thông tin để bắt đầu",
        labelFullname: "Họ và tên",
        labelMssv: "MSSV",
        labelRegUser: "Tên đăng nhập / Email",
        labelRegPass: "Mật khẩu",
        labelRegConfirm: "Xác nhận",
        textBtnReg: "ĐĂNG KÝ NGAY",
        textOrReg: "Hoặc đăng ký bằng",
        textAlready: "Đã có tài khoản?",
        textLoginLink: "Đăng nhập tại đây",
        // Trang Quên mật khẩu (Reset Password)
        forgotVisualTitle: "Đừng lo lắng!",
        forgotVisualDesc: "Chúng tôi sẽ giúp bạn lấy lại quyền truy cập chỉ trong vài phút.",
        forgotFormTitle: "Khôi phục mật khẩu",
        forgotFormSubtitle: "Nhập email đã đăng ký để nhận liên kết xác thực",
        labelEmail: "Địa chỉ Email",
        textBtnSend: "GỬI LIÊN KẾT",
        textRememberBack: "Nhớ ra mật khẩu?",
        textLoginBack: "Quay lại đăng nhập",
        doneTitle: "Đã gửi thành công!",
        doneDesc: "Vui lòng kiểm tra hòm thư của bạn để tiếp tục.",
        textBtnBack: "QUAY LẠI TRANG CHỦ",
        confirmTitle: "Đặt mật khẩu mới",
        confirmDesc: "Mật khẩu mới phải khác với mật khẩu cũ.",
        textBtnConfirm: "XÁC NHẬN THAY ĐỔI",
        completeTitle: "Thành công!",
        completeDesc: "Mật khẩu của bạn đã được cập nhật.",
        textBtnLoginNow: "ĐĂNG NHẬP NGAY"
    },
    en: {
        current: "EN",
        // Login Page
        visualTitle: "Welcome Back!",
        visualDesc: "ICMS platform helps you manage class cash flow transparently and automated.",
        formTitle: "Login",
        formSubtitle: "Enter your info to continue",
        labelUser: "Username / Email",
        labelPass: "Password",
        textRemember: "Remember me",
        textForgot: "Forgot password?",
        textBtnLogin: "LOGIN",
        textOr: "Or continue with",
        textNewbie: "New here?",
        textCreateAcc: "Create account now",
        loading: "Processing...",
        // Register Page
        regVisualTitle: "Welcome Newbie!",
        regVisualDesc: "Join FundFlow community to manage class finances professionally.",
        regFormTitle: "Create Account",
        regFormSubtitle: "Complete information to start",
        labelFullname: "Full Name",
        labelMssv: "Student ID",
        labelRegUser: "Username / Email",
        labelRegPass: "Password",
        labelRegConfirm: "Confirm Password",
        textBtnReg: "REGISTER NOW",
        textOrReg: "Or register with",
        textAlready: "Already have an account?",
        textLoginLink: "Login here",
        // Reset Password Page
        forgotVisualTitle: "Don't worry!",
        forgotVisualDesc: "We'll help you regain access in just a few minutes.",
        forgotFormTitle: "Reset Password",
        forgotFormSubtitle: "Enter your email to receive a reset link",
        labelEmail: "Email Address",
        textBtnSend: "SEND RESET LINK",
        textRememberBack: "Remembered it?",
        textLoginBack: "Back to Login",
        doneTitle: "Link Sent!",
        doneDesc: "Please check your inbox to continue the process.",
        textBtnBack: "BACK TO HOME",
        confirmTitle: "Set New Password",
        confirmDesc: "New password must be different from the old one.",
        textBtnConfirm: "CONFIRM CHANGE",
        completeTitle: "Success!",
        completeDesc: "Your password has been updated successfully.",
        textBtnLoginNow: "LOGIN NOW"
    }
};

// ==========================================
// 2. HÀM TOÀN CỤC (GLOBAL FUNCTIONS)
// ==========================================

// Hàm đổi ngôn ngữ
window.changeLanguage = function(lang) {
    const t = translations[lang];
    const langBtn = document.getElementById('current-lang');
    if (langBtn) langBtn.innerHTML = `<i class="fa-solid fa-globe"></i> ${t.current}`;
    
    // Tự động quét và thay text dựa trên camelCase sang kebab-case
    Object.keys(t).forEach(key => {
        const id = key.replace(/([A-Z])/g, "-$1").toLowerCase();
        const element = document.getElementById(id);
        if (element) {
            if (element.tagName === 'INPUT') {
                element.placeholder = t[key];
            } else {
                element.innerText = t[key];
            }
        }
    });
    localStorage.setItem('preferredLang', lang);
};

// Hàm hiện thông báo Toast
function showToast(message, type = 'error') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'error' ? 'fa-circle-xmark' : 'fa-circle-check';
    const title = type === 'error' ? 'LỖI HỆ THỐNG' : 'THÀNH CÔNG';
    
    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <div>
            <div style="font-weight: 800; font-size: 13px;">${title}</div>
            <div style="font-size: 12px; opacity: 0.8;">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// ==========================================
// 3. LOGIC KHI TẢI TRANG (DOM LOADED)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    
    // Khởi tạo ngôn ngữ & Theme
    const savedLang = localStorage.getItem('preferredLang') || 'vi';
    changeLanguage(savedLang);

    // Chế độ Sáng/Tối
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        const themeIcon = themeToggleBtn.querySelector('i');
        const currentTheme = localStorage.getItem('theme') || 'dark';
        
        if (currentTheme === 'light') {
            document.body.classList.add('light-mode');
            themeIcon.classList.replace('fa-moon', 'fa-sun');
        }

        themeToggleBtn.addEventListener('click', () => {
            const isLight = document.body.classList.toggle('light-mode');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            themeIcon.classList.toggle('fa-moon', !isLight);
            themeIcon.classList.toggle('fa-sun', isLight);
        });
    }

    // Hiệu ứng Loading cho tất cả các Form
    const authForm = document.querySelector('form');
    const btnSubmit = document.querySelector('.btn-auth');
    if (authForm && btnSubmit) {
        authForm.addEventListener('submit', function() {
            const lang = localStorage.getItem('preferredLang') || 'vi';
            btnSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${translations[lang].loading}`;
            btnSubmit.style.pointerEvents = 'none';
        });
    }

    // Ẩn/Hiện mật khẩu
    document.querySelectorAll('.fa-eye').forEach(icon => {
        icon.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (input) {
                const isPass = input.type === 'password';
                input.type = isPass ? 'text' : 'password';
                this.classList.toggle('fa-eye', !isPass);
                this.classList.toggle('fa-eye-slash', isPass);
            }
        });
    });

    // Check trùng mật khẩu (Trang Register)
    const pwd = document.querySelector('input[name="password"]');
    const confirmPwd = document.querySelector('input[name="confirm_password"]');
    if (pwd && confirmPwd) {
        confirmPwd.addEventListener('input', () => {
            confirmPwd.style.borderColor = pwd.value === confirmPwd.value ? '#10b981' : '#ef4444';
        });
    }

    // Hiển thị lỗi từ Django (Toast)
    document.querySelectorAll('.django-message').forEach(msg => {
        showToast(msg.innerText, msg.dataset.type);
    });
});