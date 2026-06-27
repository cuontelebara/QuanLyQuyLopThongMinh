/* ======================================================
   XỬ LÝ NGHIỆP VỤ TIẾN ĐỘ THU (tien_do.js) - BẢN FULL GỐC
   ====================================================== */

// 1. TIỆN ÍCH HỆ THỐNG
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

window.openModal = function(id) { 
    const m = document.getElementById(id);
    if(m) {
        m.style.display = 'flex';
        m.style.zIndex = '10000';
    }
};

window.closeModal = function(id) { 
    const m = document.getElementById(id);
    if(m) m.style.display = 'none'; 
};
window.selectPayMethodTD = function(method) {
    document.getElementById('inp-phuong-thuc-td').value = method;
    const btn = document.getElementById('btnSubmitNop');
    const cashCard = document.getElementById('m-cash-td');
    const bankCard = document.getElementById('m-bank-td');

    if (method === 'BANK') {
        bankCard.style.borderColor = '#00d2ff';
        bankCard.style.background = 'rgba(0, 210, 255, 0.05)';
        cashCard.style.borderColor = 'rgba(255,255,255,0.1)';
        cashCard.style.background = 'rgba(255,255,255,0.02)';
        btn.innerHTML = 'TIẾP TỤC QUÉT MÃ QR <i class="fa-solid fa-qrcode ms-2"></i>';
        btn.style.background = '#00d2ff';
    } else {
        cashCard.style.borderColor = '#10b981';
        cashCard.style.background = 'rgba(16, 185, 129, 0.05)';
        bankCard.style.borderColor = 'rgba(255,255,255,0.1)';
        bankCard.style.background = 'rgba(255,255,255,0.02)';
        btn.innerHTML = 'XÁC NHẬN NỘP TIỀN MẶT <i class="fa-solid fa-check ms-2"></i>';
        btn.style.background = '#10b981';
    }
}

// 2. TỰ ĐỘNG THÊM DẤU CHẤM KHI NHẬP TIỀN (Gõ 200000 -> 200.000)
window.formatMoneyInput = function(input) {
    let value = input.value.replace(/\D/g, ""); 
    if (value !== "") {
        value = new Intl.NumberFormat('vi-VN').format(parseInt(value));
        input.value = value;
    } else {
        input.value = "";
    }
}

// 3. HIỂN THỊ THÔNG BÁO (TOAST)
window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    const color = type === 'success' ? '#10b981' : '#ef4444';
    const icon = type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation';
    
    toast.style.cssText = `background: rgba(15, 23, 42, 0.95); border-left: 4px solid ${color}; color: white; padding: 16px 20px; border-radius: 12px; font-size: 13px; font-weight: 600; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 12px; transform: translateX(120%); transition: 0.3s; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); margin-bottom: 10px; z-index: 99999;`;
    toast.innerHTML = `<i class="fa-solid ${icon}" style="color: ${color}; font-size: 18px;"></i> ${message}`;
    
    container.appendChild(toast);
    setTimeout(() => toast.style.transform = 'translateX(0)', 10);
    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
};

// 4. XỬ LÝ MODAL KPI CHI TIẾT (FULL DỮ LIỆU CỦA SẾP)
window.showKpiDetail = function(type) {
    const modal = document.getElementById('kpiModal');
    const title = document.getElementById('kpiModalTitle');
    const content = document.getElementById('kpiModalContent');
    const d = window.FUND_DATA;

    if (!modal || !title || !content || !d) {
        console.error("Thiếu container modal hoặc window.FUND_DATA chưa được khai báo!");
        return;
    }

    if (type === 'muctieu') {
        title.innerHTML = '<i class="fa-solid fa-flag-checkered" style="color: #a855f7;"></i> Chi Tiết Đợt Thu';
        content.innerHTML = `
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1);">
                <p style="margin-bottom: 10px;"><strong>Tên đợt thu:</strong> <span style="color: white;">${d.tenDot}</span></p>
                <p style="margin-bottom: 15px;"><strong>Loại quỹ:</strong> <span style="color: var(--theme-primary);">${d.tenQuy}</span></p>
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 12px; border: 1px dashed rgba(168, 85, 247, 0.4); margin-bottom: 15px;">
                    <p style="margin: 0 0 5px 0; font-size: 12px; color: #94a3b8;">Định mức cần nộp:</p>
                    <p style="margin: 0 0 15px 0; font-size: 18px; font-weight: 900; color: #a855f7;">${new Intl.NumberFormat('vi-VN').format(d.dinhMuc)} đ <span style="font-size: 12px; font-weight: normal; color: #94a3b8;">/ thành viên</span></p>
                    <p style="margin: 0 0 5px 0; font-size: 12px; color: #94a3b8;">Mục tiêu tổng (Cả lớp):</p>
                    <p style="margin: 0 0 5px 0; font-size: 16px; font-weight: bold; color: white;">${d.totalNeeded} đ</p>
                    <p style="margin: 0; font-size: 12px; color: #10b981;"><i class="fa-solid fa-chart-pie"></i> Đã gom được: ${d.totalCollected} đ (${d.percent}%)</p>
                </div>
                <p style="margin: 0;"><strong>Hạn chót:</strong> <span style="color: #fca5a5; font-weight: 800;">${d.deadline}</span></p>
            </div>`;
    }
    else if (type === 'tiendo') {
        title.innerHTML = '<i class="fa-solid fa-chart-pie" style="color: #10b981;"></i> Thống Kê Dòng Tiền';
        content.innerHTML = `
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1);">
                <p><strong>Tiền kỳ vọng:</strong> <span style="color: white;">${d.totalNeeded} đ</span></p>
                <p><strong>Đã thu thực tế:</strong> <span style="color: #10b981; font-weight: 800;">${d.totalCollected} đ</span></p>
                <p><strong>Tỷ lệ hoàn thành:</strong> <span style="color: white;">${d.percent}%</span></p>
                <div style="width: 100%; height: 10px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; margin-top: 10px;">
                    <div style="width: ${d.percent}%; height: 100%; background: #10b981; box-shadow: 0 0 10px #10b981;"></div>
                </div>
            </div>`;
    } 
    else if (type === 'conno') {
        title.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color: #ef4444;"></i> Danh Sách Nợ Quỹ';
        let listNoHtml = d.danhSachNo.length > 0 
            ? d.danhSachNo.map(tv => `
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dashed rgba(255,255,255,0.1);">
                    <span style="color: white; font-weight: 600;">${tv.ho_ten}</span>
                    <span style="color: #94a3b8; font-family: monospace;">${tv.mssv}</span>
                </div>`).join('')
            : '<p style="text-align: center; padding: 20px; color: #10b981;">Tuyệt vời! Không ai nợ quỹ.</p>';

        content.innerHTML = `
            <p>Có <strong style="color: #f87171;">${d.debtCount}</strong> thành viên chưa hoàn tất:</p>
            <div style="max-height: 250px; overflow-y: auto; padding-right: 5px;">${listNoHtml}</div>
            ${d.isAdmin ? `
                <button onclick="runMassRemind()" id="massRemindBtn" class="hover-scale" style="width: 100%; background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 12px; border-radius: 10px; margin-top: 20px; font-weight: 800; cursor: pointer;">
                    <i class="fa-solid fa-bullhorn me-2"></i> NHẮC NỢ HÀNG LOẠT 🚀
                </button>` : ''}
        `;
    }
    modal.style.display = 'flex';
};

// 5. NGHIỆP VỤ NHẮC NỢ & DỌN DẸP THÔNG BÁO
window.runMassRemind = function() {
    const btn = document.getElementById('massRemindBtn');
    if (!btn) return;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang băm lệnh...';
    btn.disabled = true;

    fetch('/api/mass-remind/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: new URLSearchParams({ 'dot_thu_id': window.FUND_DATA.dotThuId })
    })
    .then(res => res.json())
    .then(data => {
        showToast(data.message, data.status);
        btn.innerHTML = '<i class="fa-solid fa-check"></i> ĐÃ NHẮC XONG';
    })
    .catch(() => {
        showToast("Lỗi kết nối máy chủ!", "error");
        btn.disabled = false;
    });
};

window.clearNotifications = function(btn) {
    window.lastClickedClearBtn = btn;
    const modal = document.getElementById('customConfirmModal');
    if(modal) modal.style.display = 'flex';
};

window.executeDeleteNotifications = function() {
    const btn = window.lastClickedClearBtn;
    const modal = document.getElementById('customConfirmModal');
    if(modal) modal.style.display = 'none';
    if(!btn) return;

    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btn.style.pointerEvents = 'none';

    fetch('/api/clear-notifications/', {
        method: 'POST',
        headers: { 
            'X-CSRFToken': getCookie('csrftoken'), 
            'Content-Type': 'application/json'
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Lỗi server');
        return res.json();
    })
    .then(data => {
        if(data.status === 'success') {
            const badge = document.querySelector('.fa-bell + span');
            if(badge) badge.style.display = 'none';
            const container = document.getElementById('notif-list-container');
            if(container) {
                container.innerHTML = `<div style="text-align: center; padding: 50px 0;"><i class="fa-solid fa-mailbox" style="font-size: 30px; opacity: 0.1; margin-bottom: 20px;"></i><p style="font-weight: 800; color: white;">Hộp thư trống</p></div>`;
            }
            showToast("Hòm thư đã sạch bóng!", "success");
        }
    })
    .catch(() => showToast("Lỗi: Không thể kết nối máy chủ!", "error"))
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.style.pointerEvents = 'auto';
    });
};

// 6. XỬ LÝ NGHIỆP VỤ HẠCH TOÁN (PHÂN QUYỀN ADMIN & THÀNH VIÊN)
window.submitNopHo = function() {
    const amountInput = document.getElementById('nopHoAmount');
    const tvName = document.getElementById('nopHoName').value;
    const method = document.getElementById('inp-phuong-thuc-td').value;

    // Làm sạch số tiền (bỏ dấu chấm)
    const cleanAmount = amountInput.value.replace(/\./g, "").replace(/\D/g, ""); 

    if (!cleanAmount || parseInt(cleanAmount) < 1000) {
        showToast("Số tiền không hợp lệ!", "error");
        return;
    }

    // --- KHÚC NÀY LÀ CHỖ HIỆN MÃ QR ---
    if (method === 'BANK') {
        const BANK_ID = "MB"; // Thay bằng ngân hàng của sếp (VD: VCB, ACB, ICB...)
        const ACCOUNT_NO = "123456789"; // Thay bằng STK của sếp
        // Tạo nội dung không dấu
        const CONTENT = `FUNDSMART ${tvName}`.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D");
        
        // Link tạo mã QR tự động
        const qrUrl = `https://img.vietqr.io/image/${BANK_ID}-${ACCOUNT_NO}-compact.png?amount=${cleanAmount}&addInfo=${encodeURIComponent(CONTENT)}`;

        // Tìm khung nội dung của Modal để dán đè QR vào
        const modalContent = document.querySelector('#nopHoModal > div');
        
        // BIẾN MODAL THÀNH MÀN HÌNH QUÉT MÃ
        modalContent.innerHTML = `
            <div style="text-align: center; padding: 10px;">
                <button onclick="location.reload()" style="position: absolute; top: 15px; right: 15px; background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 22px;"><i class="fa-solid fa-xmark"></i></button>
                <h3 style="color: #fff; margin-bottom: 20px; font-weight: 900;">MÃ QR NỘP QUỸ</h3>
                <div style="background: #fff; padding: 15px; border-radius: 20px; display: inline-block; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                    <img src="${qrUrl}" style="width: 260px; height: 260px; display: block; border-radius: 10px;">
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 15px; margin-bottom: 25px;">
                    <p style="color: #00d2ff; font-weight: 900; font-size: 22px; margin: 0;">${amountInput.value}đ</p>
                    <p style="color: #94a3b8; font-size: 11px; margin: 5px 0 0 0;">Nội dung: <b>${CONTENT}</b></p>
                </div>
                <button onclick="location.reload()" style="width: 100%; padding: 16px; border-radius: 14px; background: linear-gradient(135deg, #00d2ff, #0072ff); color: white; border: none; font-weight: 900; cursor: pointer;">TÔI ĐÃ CHUYỂN KHOẢN XONG</button>
            </div>
        `;
        return; // DỪNG LẠI TẠI ĐÂY - KHÔNG GỬI LỆNH LÊN SERVER
    }

    // --- NẾU LÀ TIỀN MẶT THÌ MỚI CHẠY TIẾP LUỒNG DƯỚI NÀY ---
    document.getElementById('nopHoModal').style.display = 'none';
    showToast("Đang gửi xác nhận đóng quỹ cá nhân...", "info");

    fetch('/api/nop-quy-ho/', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') 
        },
        body: JSON.stringify({
            tv_id: document.getElementById('nopHoId').value,
            so_tien: cleanAmount,
            dot_thu_id: window.FUND_DATA.dotThuId,
            phuong_thuc: 'CASH'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showToast("Đã gửi yêu cầu nộp tiền mặt!", "success");
            setTimeout(() => window.location.reload(), 1000);
        }
    });
};


// 8. KHỞI TẠO MODAL GIAO DỊCH (TỐI ƯU TRẢI NGHIỆM VÀ ĐỊNH DẠNG)
window.openNopQuyCaNhan = function(targetId, displayName) {
    const modal = document.getElementById('nopHoModal');
    const inputId = document.getElementById('nopHoId');
    const inputName = document.getElementById('nopHoName');
    const inputAmount = document.getElementById('nopHoAmount');

    if (modal && inputId && inputName && inputAmount) {
        inputId.value = targetId;
        inputName.value = displayName || "Không xác định";
        
        // FIX LỖI "200": Ép về chuỗi -> Quét sạch ký tự lạ -> Ép lại thành số nguyên -> Đóng mộc VNĐ
        let rawDinhMuc = String(window.FUND_DATA?.dinhMuc || "200000").replace(/\D/g, "");
        inputAmount.value = new Intl.NumberFormat('vi-VN').format(parseInt(rawDinhMuc));

        modal.style.display = 'flex';
        modal.style.opacity = '0';
        
        setTimeout(() => {
            modal.style.opacity = '1';
            modal.style.transition = 'opacity 0.2s ease-in-out';
            
            // Tự động focus và bôi đen toàn bộ số tiền
            inputAmount.focus();
            inputAmount.setSelectionRange(0, inputAmount.value.length);
        }, 50);

        console.log(`[SYSTEM] Khởi tạo phiên hạch toán cho ID: ${targetId}`);
    } else {
        console.error("[CRITICAL] Lỗi cấu trúc Modal: Kiểm tra lại các ID trong HTML.");
        showToast("Lỗi khởi tạo giao diện báo cáo!", "error");
    }
};

// 7. CHATBOT AI LOGIC
window.toggleChatbot = function() {
    const bot = document.getElementById('chatbot-window');
    if (!bot) return;
    const isClosed = bot.style.opacity === "0" || bot.style.opacity === "";
    bot.style.transform = isClosed ? 'scale(1)' : 'scale(0)';
    bot.style.opacity = isClosed ? '1' : '0';
    bot.style.pointerEvents = isClosed ? 'auto' : 'none';
    if (isClosed) document.getElementById('chat-input')?.focus();
};
// 9. CẬP NHẬT NGÀY GIỜ & KHỞI TẠO
function updateRealtimeDate() {
    const el = document.getElementById('realtime-date');
    if (el) {
        const d = new Date();
        const days = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
        el.innerText = `${days[d.getDay()]}, ${d.getDate()}/${d.getMonth() + 1}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateRealtimeDate();
    document.getElementById('chatbot-fab')?.addEventListener('click', toggleChatbot);
    document.getElementById('close-bot')?.addEventListener('click', toggleChatbot);
    document.getElementById('send-chat')?.addEventListener('click', sendChatMessage);
    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
});