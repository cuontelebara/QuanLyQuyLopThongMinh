/* ======================================================
   XỬ LÝ NGHIỆP VỤ ĐÓNG QUỸ LỚP - BẢN FULL ĐẦY ĐỦ 100% (BỌC THÉP)
   ====================================================== */

// 1. LUỒNG ĐỔI PHƯƠNG THỨC THANH TOÁN (ƯU TIÊN LÊN ĐẦU FILE)
window.selectPayMethodTD = function(method) {
    console.log(`[SYSTEM] Đang kích hoạt phương thức: ${method}`);
    try {
        const inpMethod = document.getElementById('inp-phuong-thuc-td');
        const btn = document.getElementById('btnSubmitNop');
        
        const walletCard = document.getElementById('m-wallet-td');
        const cashCard = document.getElementById('m-cash-td');
        const bankCard = document.getElementById('m-bank-td');

        if (!inpMethod) {
            console.error("Không tìm thấy ô input ẩn id='inp-phuong-thuc-td'!");
            return;
        }
        inpMethod.value = method;

        // Khôi phục trạng thái viền mờ ban đầu cho cả 3 thẻ phương thức
        [walletCard, cashCard, bankCard].forEach(card => {
            if(card) {
                card.style.borderColor = 'rgba(255,255,255,0.1)';
                card.style.background = 'rgba(255,255,255,0.02)';
                card.style.boxShadow = 'none';
            }
        });

        // Kích hoạt màu Neon sáng và text tương ứng khi nhấn chọn
        if (method === 'WEB_WALLET') {
            if(walletCard) {
                walletCard.style.borderColor = '#a855f7';
                walletCard.style.background = 'rgba(168, 85, 247, 0.1)';
                walletCard.style.boxShadow = '0 0 15px rgba(168, 85, 247, 0.3)';
            }
            if(btn) {
                btn.innerHTML = 'XÁC NHẬN TRÍCH VÍ WEB <i class="fa-solid fa-wallet ms-2"></i>';
                btn.style.background = '#a855f7';
            }
        } else if (method === 'BANK') {
            if(bankCard) {
                bankCard.style.borderColor = '#00d2ff';
                bankCard.style.background = 'rgba(0, 210, 255, 0.1)';
                bankCard.style.boxShadow = '0 0 15px rgba(0, 210, 255, 0.3)';
            }
            if(btn) {
                btn.innerHTML = 'TIẾP TỤC QUÉT MÃ QR <i class="fa-solid fa-qrcode ms-2"></i>';
                btn.style.background = '#00d2ff';
            }
        } else {
            if(cashCard) {
                cashCard.style.borderColor = '#10b981';
                cashCard.style.background = 'rgba(16, 185, 129, 0.1)';
                cashCard.style.boxShadow = '0 0 15px rgba(16, 185, 129, 0.3)';
            }
            if(btn) {
                btn.innerHTML = 'XÁC NHẬN NỘP TIỀN MẶT <i class="fa-solid fa-check ms-2"></i>';
                btn.style.background = '#10b981';
            }
        }
    } catch (err) {
        console.error("Lỗi thực thi đổi phương thức:", err);
    }
};

// 2. CÁC HÀM HỆ THỐNG & TIỆN ÍCH PHỤ TRỢ
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
    if(m) m.style.display = 'flex';
};

window.closeModal = function(id) { 
    const m = document.getElementById(id);
    if(m) m.style.display = 'none'; 
};

window.formatMoneyInput = function(input) {
    let value = input.value.replace(/\D/g, ""); 
    if (value !== "") {
        input.value = new Intl.NumberFormat('vi-VN').format(parseInt(value));
    }
};

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

// 3. XỬ LÝ HIỂN THỊ MODAL KPI CHI TIẾT (HÀM QUAN TRỌNG BỊ KHUYẾT)
window.showKpiDetail = function(type) {
    const modal = document.getElementById('kpiModal');
    const title = document.getElementById('kpiModalTitle');
    const content = document.getElementById('kpiModalContent');
    const d = window.FUND_DATA;

    if (!modal || !title || !content || !d) {
        console.error("Lỗi cấu trúc: Thiếu phần tử Modal hoặc cấu hình window.FUND_DATA chưa được nạp!");
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
                    <span style="color: #94a3b8; font-family: monospace; font-size: 13px;">${tv.mssv}</span>
                </div>`).join('')
            : '<p style="text-align: center; padding: 20px; color: #10b981;">Tuyệt vời! Không ai nợ quỹ.</p>';

        content.innerHTML = `
            <p>Có <strong style="color: #f87171;">${d.debtCount}</strong> thành viên chưa hoàn tất:</p>
            <div style="max-height: 250px; overflow-y: auto; padding-right: 5px;">${listNoHtml}</div>
            ${d.isAdmin ? `
                <button onclick="runMassRemind()" id="massRemindBtn" style="width: 100%; background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 12px; border-radius: 10px; margin-top: 20px; font-weight: 800; cursor: pointer; transition: 0.2s;">
                    <i class="fa-solid fa-bullhorn me-2"></i> NHẮC NỢ HÀNG LOẠT 🚀
                </button>` : ''}
        `;
    }
    modal.style.display = 'flex';
};

// 4. NGHIỆP VỤ NHẮC NỢ & DỌN DẸP HÒM THƯ THÔNG BÁO
window.runMassRemind = function() {
    const btn = document.getElementById('massRemindBtn');
    if (!btn) return;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang gửi lệnh...';
    btn.disabled = true;

    fetch('/api/mass-remind/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: new URLSearchParams({ 'dot_thu_id': window.FUND_DATA.dotThuId })
    })
    .then(res => res.json())
    .then(data => {
        window.showToast(data.message, data.status);
        btn.innerHTML = '<i class="fa-solid fa-check"></i> ĐẠI PHÁT THÀNH CÔNG';
    })
    .catch(() => {
        window.showToast("Lỗi kết nối máy chủ!", "error");
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
        if (!res.ok) throw new Error('Lỗi liên kết máy chủ');
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
            window.showToast("Hòm thư đã sạch bóng!", "success");
        }
    })
    .catch(() => window.showToast("Lỗi: Không thể kết nối máy chủ!", "error"))
    .finally(() => {
        btn.innerHTML = originalHtml;
        btn.style.pointerEvents = 'auto';
    });
};

// 5. LOGIC SUBMIT HẠCH TOÁN NỘP TIỀN
window.submitNopHo = function() {
    const amountInput = document.getElementById('nopHoAmount');
    const tvId = document.getElementById('nopHoId').value;
    const tvName = document.getElementById('nopHoName').value;
    const method = document.getElementById('inp-phuong-thuc-td').value; 
    const cleanAmount = amountInput.value.replace(/\./g, "").replace(/\D/g, "");
    
    if (!cleanAmount || parseInt(cleanAmount) < 1000) {
        window.showToast("Số tiền không hợp lệ!", "error");
        return;
    }

    const sendNopQuyRequest = (payMethod) => {
        if (payMethod === 'WEB_WALLET') {
            window.showToast("Đang kiểm tra số dư và trích ví Web...", "info");
        } else {
            window.showToast("Đang gửi yêu cầu đóng quỹ...", "info");
        }
        
        // 🌟 ĐÃ ĐỔI URL GỌI VỀ ĐÚNG HÀM CHUẨN CỦA API_VIEWS
        fetch('/api/nop-quy/', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') 
            },
            body: JSON.stringify({
                tv_id: tvId,
                so_tien: cleanAmount,
                dot_thu_id: window.FUND_DATA.dotThuId,
                phuong_thuc: payMethod, 
                ly_do: "Đóng quỹ lớp"
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                window.showToast(data.message, "success");
                setTimeout(() => window.location.reload(), 1500);
            } else if (data.status === 'error' && data.action === 'redirect_to_deposit') {
                window.showToast(data.message, "error");
                setTimeout(() => { window.location.href = '/nap-tien/'; }, 2000);
            } else {
                window.showToast(data.message, "error");
            }
        })
        .catch(() => window.showToast("Lỗi kết nối máy chủ!", "error"));
    };
    if (method === 'BANK') {
        const BANK_ID = "MB"; 
        const ACCOUNT_NO = "123456789"; 
        const CONTENT = `FUNDSMART ${tvName}`.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D");
        const qrUrl = `https://img.vietqr.io/image/${BANK_ID}-${ACCOUNT_NO}-compact.png?amount=${cleanAmount}&addInfo=${encodeURIComponent(CONTENT)}`;
        const modalContent = document.querySelector('#nopHoModal > div');
        
        modalContent.innerHTML = `
            <div style="text-align: center; padding: 10px;">
                <button onclick="location.reload()" style="position: absolute; top: 15px; right: 15px; background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 22px;"><i class="fa-solid fa-xmark"></i></button>
                <h3 style="color: #fff; margin-bottom: 20px; font-weight: 900;">MÃ QR NỘP QUỸ</h3>
                <div style="background: #fff; padding: 15px; border-radius: 20px; display: inline-block; margin-bottom: 20px;">
                    <img src="${qrUrl}" style="width: 260px; height: 260px; display: block; border-radius: 10px;">
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 15px; margin-bottom: 25px;">
                    <p style="color: #00d2ff; font-weight: 900; font-size: 22px; margin: 0;">${amountInput.value}đ</p>
                    <p style="color: #94a3b8; font-size: 11px; margin: 5px 0 0 0;">Nội dung: <b>${CONTENT}</b></p>
                </div>
                <button id="btnConfirmQrDone" style="width: 100%; padding: 16px; border-radius: 14px; background: linear-gradient(135deg, #00d2ff, #0072ff); color: white; border: none; font-weight: 900; cursor: pointer;">TÔI ĐÃ CHUYỂN KHOẢN XONG</button>
            </div>
        `;

        document.getElementById('btnConfirmQrDone').addEventListener('click', function() {
            document.getElementById('nopHoModal').style.display = 'none';
            sendNopQuyRequest('BANK');
        });
        return; 
    }

    document.getElementById('nopHoModal').style.display = 'none';
    sendNopQuyRequest(method);
};

// 6. KHỞI TẠO POPUP KHI BẤM NÚT NỘP TIỀN
window.openNopQuyCaNhan = function(targetId, displayName) {
    const modal = document.getElementById('nopHoModal');
    const inputId = document.getElementById('nopHoId');
    const inputName = document.getElementById('nopHoName');
    const inputAmount = document.getElementById('nopHoAmount');

    if (modal && inputId && inputName && inputAmount) {
        inputId.value = targetId;
        inputName.value = displayName || "Không xác định";
        
        let rawDinhMuc = String(window.FUND_DATA?.dinhMuc || "200000").replace(/\D/g, "");
        inputAmount.value = new Intl.NumberFormat('vi-VN').format(parseInt(rawDinhMuc));

        modal.style.display = 'flex';
        modal.style.opacity = '0';
        
        setTimeout(() => {
            modal.style.opacity = '1';
            modal.style.transition = 'opacity 0.2s ease-in-out';
            inputAmount.focus();
            inputAmount.setSelectionRange(0, inputAmount.value.length);
        }, 50);
        console.log(`[SYSTEM] Đã khởi tạo phiên đóng quỹ cho thành viên ID: ${targetId}`);
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

window.sendChatMessage = function() {
    const input = document.getElementById('chat-input');
    const body = document.getElementById('chat-body');
    if (!input || !input.value.trim()) return;

    const userMsg = input.value;
    input.value = '';

    // Render tin nhắn của User
    body.innerHTML += `<div style="align-self: flex-end; background: var(--theme-primary); color: #0f172a; padding: 10px 15px; border-radius: 15px 0 15px 15px; font-size: 13px; font-weight: 700;">${userMsg}</div>`;
    body.scrollTop = body.scrollHeight;

    // Gọi API Chatbot
    fetch('/api/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ message: userMsg })
    })
    .then(res => res.json())
    .then(data => {
        body.innerHTML += `<div style="background: white; padding: 10px 15px; border-radius: 0 15px 15px 15px; font-size: 13px; max-width: 80%; align-self: flex-start; color: #334155;">${data.reply}</div>`;
        body.scrollTop = body.scrollHeight;
    })
    .catch(() => {
        body.innerHTML += `<div style="background: white; padding: 10px 15px; border-radius: 0 15px 15px 15px; font-size: 13px; max-width: 80%; align-self: flex-start; color: #ef4444;">[ERROR] Lỗi kết nối trợ lý ảo!</div>`;
        body.scrollTop = body.scrollHeight;
    });
};

function updateRealtimeDate() {
    const el = document.getElementById('realtime-date');
    if (el) {
        const d = new Date();
        const days = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
        el.innerText = `${days[d.getDay()]}, ${d.getDate()}/${d.getMonth() + 1}`;
    }
}

// 8. KHỞI TẠO HOÀN CHỈNH KHI TẢI TRANG
document.addEventListener('DOMContentLoaded', () => {
    updateRealtimeDate();
    document.getElementById('chatbot-fab')?.addEventListener('click', window.toggleChatbot);
    document.getElementById('close-bot')?.addEventListener('click', window.toggleChatbot);
    document.getElementById('send-chat')?.addEventListener('click', window.sendChatMessage);
    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') window.sendChatMessage();
    });
    console.log("[SYSTEM] Khởi chạy thành công bộ điều khiển FundSmart Pro Core!");
});