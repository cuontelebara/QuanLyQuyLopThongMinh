/* ======================================================
   XỬ LÝ NGHIỆP VỤ TRANG GIAO DỊCH (giao_dich.js)
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
    const m = document.getElementById(id);
    if(m) { m.style.display = 'flex'; m.classList.add('active'); }
};
window.closeModal = function(id) { 
    const m = document.getElementById(id);
    if(m) { m.style.display = 'none'; m.classList.remove('active'); }
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

// --- LOGIC LỌC TÌM KIẾM ---
function applyFilters() {
    const typeFilter = document.getElementById('typeFilter');
    const searchInput = document.getElementById('searchInput');
    const rows = document.querySelectorAll('.tx-row');

    if (!rows.length) return;

    const filterType = typeFilter ? typeFilter.value : 'ALL';
    const searchText = searchInput ? searchInput.value.toLowerCase().trim() : '';

    rows.forEach(row => {
        const rowType = row.getAttribute('data-type');
        const textContent = row.textContent.toLowerCase();

        let isMatch_Type = false;
        if (filterType === 'ALL') {
            isMatch_Type = true;
        } else if (filterType === 'THU' && (rowType === 'THU' || rowType === 'LAI')) {
            isMatch_Type = true;
        } else if (filterType === 'CHI' && (rowType === 'CHI' || rowType === 'TU')) {
            isMatch_Type = true;
        }

        let isMatch_Search = textContent.includes(searchText);

        if (isMatch_Type && isMatch_Search) {
            row.style.display = 'flex'; 
        } else {
            row.style.display = 'none';
        }
    });
}

function setupEventListeners() {
    const typeFilter = document.getElementById('typeFilter');
    const searchInput = document.getElementById('searchInput');

    if (typeFilter) typeFilter.addEventListener('change', applyFilters);
    if (searchInput) searchInput.addEventListener('keyup', applyFilters);
}

function checkUrlSearchParam() {
    const urlParams = new URLSearchParams(window.location.search);
    const searchKey = urlParams.get('search');
    
    if (searchKey) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = searchKey;
            applyFilters(); 
            showToast(`Đang lọc lịch sử của: ${searchKey}`, 'info');
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    setupEventListeners();
    checkUrlSearchParam();
});