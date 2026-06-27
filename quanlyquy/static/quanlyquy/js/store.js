/* ======================================================
   XỬ LÝ NGHIỆP VỤ CỬA HÀNG (store.js)
   ====================================================== */

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
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-circle-exclamation';
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

// --- LOGIC MUA HÀNG BẰNG XU (GỌI API THẬT) ---
window.confirmExchange = function(itemId, itemName, itemPrice, userBalance) {
    // Chuyển kiểu dữ liệu sang số để so sánh chính xác
    const price = parseInt(itemPrice);
    const balance = parseInt(userBalance);

    if (balance < price) {
        showToast(`❌ Không đủ Xu! Bạn cần thêm ${price - balance} Xu nữa để đổi "${itemName}".`, 'error');
        return;
    }
    
    if (confirm(`🎁 Bạn có chắc chắn muốn dùng ${price} Xu để đổi "${itemName}" không?`)) {
        fetch('/api/shop/buy/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            // Gửi ID vật phẩm lên để Server tự check giá trong DB (Bảo mật nhất)
            body: JSON.stringify({ item_id: itemId })
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
        .catch(err => showToast("Lỗi kết nối mạng!", "error"));
    }
};