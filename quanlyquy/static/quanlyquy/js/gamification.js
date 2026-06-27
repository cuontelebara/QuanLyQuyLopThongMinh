/* ======================================================
   JAVASCRIPT CHO GAMIFICATION (gamification.js)
   ====================================================== */

// --- BỘ CÔNG CỤ DÙNG CHUNG ---
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

window.showToast = function(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; top: 30px; right: 30px; z-index: 99999; display: flex; flex-direction: column; gap: 12px;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const color = type === 'success' ? '#10b981' : (type === 'error' ? '#ef4444' : '#3b82f6');
    const icon = type === 'success' ? 'fa-gift' : 'fa-circle-exclamation';
    toast.style.cssText = `background: rgba(15, 23, 42, 0.95); border-left: 4px solid ${color}; color: white; padding: 16px 20px; border-radius: 12px; font-size: 13px; font-weight: 600; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 12px; transform: translateX(120%); transition: 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); margin-bottom: 10px;`;
    toast.innerHTML = `<i class="fa-solid ${icon}" style="color: ${color}; font-size: 18px;"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.style.transform = 'translateX(0)', 10);
    setTimeout(() => { toast.style.transform = 'translateX(120%)'; setTimeout(() => toast.remove(), 300); }, 4000);
};

window.openModal = function(id) { 
    const el = document.getElementById(id);
    if(el) { el.style.display = 'flex'; el.classList.add('active'); }
};
window.closeModal = function(id) { 
    const el = document.getElementById(id);
    if(el) { el.style.display = 'none'; el.classList.remove('active'); }
};

// --- CHATBOT AI ---
window.toggleChatbot = function() {
    const bot = document.getElementById('chatbot-window');
    if(!bot) return;
    if(bot.style.transform === 'scale(1)') {
        bot.style.transform = 'scale(0)'; bot.style.opacity = '0';
    } else {
        bot.style.transform = 'scale(1)'; bot.style.opacity = '1';
        document.getElementById('chat-input').focus();
    }
};

window.sendChatMessage = async function() {
    const input = document.getElementById('chat-input');
    const body = document.getElementById('chat-body');
    if(!input || !body) return;
    const message = input.value.trim();
    if (!message) return;

    const userMsg = document.createElement('div');
    userMsg.style.cssText = "align-self: flex-end; background: var(--theme-primary); color: white; padding: 10px 15px; border-radius: 15px 0 15px 15px; font-size: 13px; max-width: 80%; margin-top: 10px;";
    userMsg.innerText = message;
    body.appendChild(userMsg);
    input.value = '';
    body.scrollTop = body.scrollHeight;

    const botTyping = document.createElement('div');
    botTyping.style.cssText = "align-self: flex-start; background: white; padding: 10px 15px; border-radius: 0 15px 15px 15px; font-size: 13px; color: #64748b; font-style: italic; margin-top: 10px;";
    botTyping.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang phân tích...';
    body.appendChild(botTyping);
    body.scrollTop = body.scrollHeight;

    try {
        const response = await fetch('/api/chatbot/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();
        body.removeChild(botTyping);

        const botMsg = document.createElement('div');
        botMsg.style.cssText = "align-self: flex-start; background: white; padding: 10px 15px; border-radius: 0 15px 15px 15px; font-size: 13px; max-width: 80%; box-shadow: 0 2px 5px rgba(0,0,0,0.05); line-height: 1.5; margin-top: 10px;";
        botMsg.innerHTML = data.reply; 
        body.appendChild(botMsg);
        body.scrollTop = body.scrollHeight;
    } catch (error) { if(botTyping.parentNode) body.removeChild(botTyping); }
};

// ==========================================
// LOGIC VÒNG QUAY CASINO PRO 
// ==========================================
let bigWheelDrawn = false;
let bigGachaRotation = 0;
let isBigSpinning = false;
let ledInterval;
let idleAnimationId;

// HÀM MỚI: TỰ ĐỘNG XOAY CHỜ CHẦM CHẬM
function startIdleSpin() {
    if (isBigSpinning) return; // Nếu đang quay thật thì dừng hàm này
    const wheel = document.getElementById('wheel-inner');
    if (wheel) {
        wheel.style.transition = 'none'; // Tắt hiệu ứng mượt để xoay từng frame
        bigGachaRotation += 0.25; // Tốc độ xoay (Có thể tăng/giảm số này)
        wheel.style.transform = `rotate(${bigGachaRotation}deg)`;
        idleAnimationId = requestAnimationFrame(startIdleSpin);
    }
}

window.initBigWheel = function() {
    if (bigWheelDrawn) return; 
    const wheel = document.getElementById('wheel-inner');
    const ledContainer = document.getElementById('led-container');
    if(!wheel || !ledContainer) return;

   const items = [
        { text: "XỊT", color: "#ef4444", icon: "fa-ghost" },           // Đỏ (rgb 239, 68, 68)
        { text: "10 XU", color: "#f97316", icon: "fa-coins" },         // Cam (rgb 249, 115, 22)
        { text: "20 XU", color: "#f59e0b", icon: "fa-money-bill-wave" },// Vàng Amber (rgb 245, 158, 11)
        { text: "XỊT", color: "#ef4444", icon: "fa-ghost" },           // Đỏ
        { text: "30 XU", color: "#10b981", icon: "fa-money-bill" },    // Xanh lục (rgb 16, 185, 129)
        { text: "50 XU", color: "#3b82f6", icon: "fa-money-bill-alt" },// Xanh dương (rgb 59, 130, 246)
        { text: "ĐỘC ĐẮC", color: "#991b1b", icon: "fa-crown", isJackpot: true }, // Đỏ sẫm (Trộn từ Gradient đỏ/vàng của Jackpot để nổi bật chữ vàng)
        { text: "10 XU", color: "#f97316", icon: "fa-coins" },         // Cam
        { text: "XỊT", color: "#ef4444", icon: "fa-ghost" },           // Đỏ
        { text: "20 XU", color: "#f59e0b", icon: "fa-money-bill-wave" },// Vàng Amber
        { text: "QUÀ TẶNG", color: "#a855f7", icon: "fa-gift" },       // Tím Voucher (rgb 168, 85, 247)
        { text: "30 XU", color: "#10b981", icon: "fa-money-bill" }     // Xanh lục
    ];

    const degPerItem = 360 / items.length;
    let conicString = [];

    items.forEach((item, i) => {
        const startDeg = i * degPerItem;
        const endDeg = (i + 1) * degPerItem;
        conicString.push(`${item.color} ${startDeg}deg ${endDeg}deg`);

        const span = document.createElement('div');
        span.style.cssText = `position: absolute; width: 50%; height: 30px; top: 50%; left: 50%; transform-origin: 0 50%; display: flex; justify-content: flex-end; align-items: center; padding-right: 30px; color: white; font-weight: 900; gap: 8px; text-shadow: 1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 0 3px 5px rgba(0,0,0,0.8); z-index: 2; box-sizing: border-box;`;
        
        const textAngle = startDeg + (degPerItem / 2) - 90; 
        span.style.transform = `translateY(-50%) rotate(${textAngle}deg)`;
        span.style.fontSize = item.isJackpot ? '14px' : '17px'; 
        span.innerHTML = `<i class="fa-solid ${item.icon}" style="color: #ffd700; font-size: 15px; filter: drop-shadow(1px 1px 1px #000);"></i> ${item.text}`;

        const borderLine = document.createElement('div');
        borderLine.style.cssText = `position: absolute; width: 50%; height: 3px; background: rgba(255,255,255,0.4); top: 50%; left: 50%; transform-origin: 0 50%; z-index: 3; box-shadow: 0 0 5px rgba(0,0,0,0.5);`;
        borderLine.style.transform = `translateY(-50%) rotate(${startDeg}deg)`;
        
        wheel.appendChild(borderLine);
        wheel.appendChild(span);
    });

    wheel.style.background = `conic-gradient(${conicString.join(', ')})`;

    // VẼ ĐÈN LED CHẠY VIỀN
    const totalLeds = 40; 
    const degreePerLed = 360 / totalLeds;
    for (let i = 0; i < totalLeds; i++) {
        const led = document.createElement('div');
        led.className = 'gacha-led-dot';
        led.style.transform = `translate(-50%, -50%) rotate(${degreePerLed * i}deg) translateY(-235px)`; 
        ledContainer.appendChild(led);
    }
    
    let ledIndex = 0;
    if(ledInterval) clearInterval(ledInterval);
    ledInterval = setInterval(() => {
        const leds = document.querySelectorAll('.gacha-led-dot');
        if(leds.length === 0) return;
        leds.forEach(l => l.classList.remove('active'));
        for (let i = 0; i < 5; i++) {
            const index = (ledIndex + i * 8) % leds.length;
            leds[index].classList.add('active');
        }
        ledIndex = (ledIndex + 1) % leds.length;
    }, 100);
    
    bigWheelDrawn = true;
    
    // KÍCH HOẠT XOAY CHỜ NGAY KHI VẼ XONG
    startIdleSpin();
};

// HÀM QUAY GACHA VÀ XỬ LÝ LỖI
window.executeBigSpin = function() {
    if (isBigSpinning) return;
    
    const btn = document.getElementById('spin-button-pro'); 
    const wheel = document.getElementById('wheel-inner');
    const popup = document.getElementById('gacha-result-popup');
    const title = document.getElementById('result-title');
    const msg = document.getElementById('result-msg');
    const icon = document.getElementById('result-icon');
    let actionBtn = null;
    if(popup) actionBtn = popup.querySelector('button');

    if (!wheel || !btn) return;

    // BẮT ĐẦU QUAY (Dừng xoay nhàn rỗi)
    isBigSpinning = true;
    cancelAnimationFrame(idleAnimationId);

    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size: 32px;"></i>';
    wheel.classList.add('gacha-spinning-effect');

    fetch('/api/gacha/spin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }
    })
    .then(async res => {
        const data = await res.json();
        
        // NẾU PYTHON BÁO LỖI (Hết xu, lỗi DB...)
        if (data.status === 'error') {
            isBigSpinning = false;
            btn.innerHTML = '<span id="spin-text" style="font-size: 20px;">QUAY<br><span style="font-size: 11px; color: #ffd700;">-20 XU</span></span>';
            wheel.classList.remove('gacha-spinning-effect');
            startIdleSpin(); // Bật lại xoay rù rù
            
            // Hiện Popup Đỏ Báo Lỗi Trực Quan (Không dùng alert gây kẹt)
            if(popup && title && msg && icon && actionBtn) {
                icon.innerText = "🚨";
                title.innerText = "KHÔNG THỂ QUAY!";
                title.style.color = "#ef4444";
                popup.style.borderColor = "#ef4444";
                popup.style.boxShadow = "0 0 50px rgba(239, 68, 68, 0.5)";
                msg.innerHTML = `<b style="color: #ef4444;">${data.message}</b><br><span style="font-size: 12px; color: #94a3b8;">Cày thêm nhiệm vụ hoặc báo Admin nhé!</span>`;
                actionBtn.innerText = "ĐÓNG";
                actionBtn.style.background = "#ef4444";
                actionBtn.onclick = function() { popup.classList.remove('show'); };
                popup.classList.add('show');
            }
            return;
        }

        // NẾU THÀNH CÔNG: QUAY MƯỢT
        let currentMod = bigGachaRotation % 360;
        let spinTo = data.angle - currentMod;
        if (spinTo < 0) spinTo += 360; 
        bigGachaRotation += spinTo + 3600; 
        
        void wheel.offsetWidth; // Refresh CSS
        wheel.style.transition = 'transform 6s cubic-bezier(0.1, 0.7, 0.1, 1)';
        wheel.style.transform = `rotate(${bigGachaRotation}deg)`; 

        // KHI DỪNG LẠI SAU 6 GIÂY
        setTimeout(() => {
            isBigSpinning = false;
            wheel.classList.remove('gacha-spinning-effect');
            btn.innerHTML = '<span id="spin-text" style="font-size: 20px;">QUAY<br><span style="font-size: 11px; color: #ffd700;">-20 XU</span></span>';
            
            // Cập nhật số dư trực tiếp trên Web
            const balanceEl = document.querySelector('h2[style*="text-shadow"]');
            if(balanceEl && data.new_balance !== undefined) {
                balanceEl.innerHTML = `${data.new_balance} <span style="font-size: 12px; color: #fbbf24;">XU</span>`;
            }

            if(popup && title && msg && icon && actionBtn) {
                popup.style.borderColor = "#ffd700";
                popup.style.boxShadow = "0 0 50px rgba(251, 191, 36, 0.5)";
                actionBtn.innerText = "NHẬN THƯỞNG";
                actionBtn.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
                actionBtn.onclick = function() { location.reload(); };

                if (data.prize_type === "VOUCHER") {
                    title.innerText = "🎁 TRÚNG QUÀ THẬT!";
                    title.style.color = "#4ade80";
                    msg.innerHTML = `Sếp nhận được: <b style="color: #ffd700; font-size: 18px;">${data.voucher_name}</b><br>Đã cất vào kho đồ!`;
                    icon.innerText = "📦";
                } else {
                    title.innerText = data.prize > 0 ? "THẮNG LỚN!" : "XUI QUÁ!";
                    title.style.color = "#ffd700";
                    msg.innerText = data.message;
                    icon.innerText = data.prize > 0 ? "💰" : "👻";
                }
                popup.classList.add('show');
            }
            if (typeof confetti === 'function' && (data.prize > 0 || data.prize_type === "VOUCHER")) {
                confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, zIndex: 3000 });
            }
        }, 6100);
    })
    .catch(err => {
        // Lỗi rớt mạng hoặc sập hẳn Server
        console.error(err);
        isBigSpinning = false;
        btn.innerHTML = '<span id="spin-text" style="font-size: 20px;">QUAY<br><span style="font-size: 11px; color: #ffd700;">-20 XU</span></span>';
        wheel.classList.remove('gacha-spinning-effect');
        startIdleSpin();
        alert('Server không phản hồi! Sếp F5 lại web nha.');
    });
};

// --- CÁC TÍNH NĂNG KHÁC ---
window.submitVote = function(pollId) {
    fetch('/api/gacha/vote/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ poll_id: pollId })
    })
    .then(res => res.json())
    .then(data => {
        if(data.status === 'success') {
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.message, 'error');
        }
    })
    .catch(err => showToast('Lỗi mạng!', 'error'));
};

window.toggleQuests = function() {
    const extraQuests = document.querySelectorAll('.extra-quest');
    const btn = document.getElementById('toggleQuestBtn');
    if (!extraQuests.length) return;

    const isHidden = extraQuests[0].style.display === 'none';
    if (isHidden) {
        extraQuests.forEach(q => q.style.display = 'flex');
        btn.innerHTML = 'Thu gọn danh sách <i class="fa-solid fa-chevron-up ms-2"></i>';
        btn.style.background = 'rgba(239, 68, 68, 0.05)';
        btn.style.color = '#f87171';
        btn.style.borderColor = 'rgba(239, 68, 68, 0.3)';
    } else {
        extraQuests.forEach(q => q.style.display = 'none');
        btn.innerHTML = `Xem thêm ${extraQuests.length} nhiệm vụ <i class="fa-solid fa-chevron-down ms-2"></i>`;
        btn.style.background = 'rgba(56, 189, 248, 0.05)';
        btn.style.color = '#38bdf8';
        btn.style.borderColor = 'rgba(56, 189, 248, 0.3)';
        document.getElementById('quest-container').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
};

// Gọi vẽ vòng quay khi load web
document.addEventListener("DOMContentLoaded", function() {
    window.initBigWheel();
});


window.handleQuestGo = function(questName) {
    const name = questName.toLowerCase();
    
    if (name.includes("phân tích")) window.location.href = "/thong-ke/";
    else if (name.includes("điểm danh")) window.location.href = "/";
    else if (name.includes("mẫn cán")) window.location.href = "/giao-dich/";
    else if (name.includes("nợ nần") || name.includes("gương mẫu") || name.includes("bao nuôi")) window.location.href = "/tien-do/";
    else if (name.includes("shopping")) window.location.href = "/cua-hang/";
    else if (name.includes("gacha") || name.includes("cử tri")) {
        document.getElementById('quest-container').scrollIntoView({behavior: "smooth"});
        showToast('Nhiệm vụ này làm ngay tại trang Giải Trí sếp nhé!', 'info');
    }
    else if (name.includes("bot")) {
        if(typeof window.toggleChatbot === 'function') window.toggleChatbot();
    } 
};

window.submitVoteCustom = function(pollId, phuongAnId) {
    // 1. Hàm tự động rà quét Token bảo mật (Không lo lỗi 403)
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

    // 2. Tạo hiệu ứng Loading để sếp biết là nút đã nhận lệnh
    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nộp phiếu...';
    btn.style.pointerEvents = 'none'; // Khóa nút chống bấm 2 lần

    // 3. Bắn dữ liệu lên Server
    fetch('/api/submit-vote/', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json', 
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ poll_id: pollId, phuong_an_id: phuongAnId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') { 
            location.reload(); // Load lại trang để hiện thanh tiến độ %
        } else { 
            alert("⚠️ Lỗi: " + data.message); 
            btn.innerHTML = originalText;
            btn.style.pointerEvents = 'auto';
        }
    })
    .catch(err => {
        alert("⚠️ Không thể kết nối đến máy chủ!");
        btn.innerHTML = originalText;
        btn.style.pointerEvents = 'auto';
    });
};