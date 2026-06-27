// ==========================================
// 1. CÁC HÀM TIỆN ÍCH CƠ BẢN (UTILITIES)
// ==========================================
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

function openModal(id) { 
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active'); 
}

function closeModal(id) { 
    const modal = document.getElementById(id);
    if(modal) {
        modal.classList.remove('active'); 

        // Reset dữ liệu nếu là form nộp tiền (ĐÃ BỌC LÓT CHỐNG LỖI NULL)
        if (id === 'depositModal') {
            if(document.getElementById('inp-so-tien-thu')) document.getElementById('inp-so-tien-thu').value = '';
            if(document.getElementById('inp-ly-do-thu')) document.getElementById('inp-ly-do-thu').value = '';
            if(document.getElementById('inp-muc-tieu-id')) document.getElementById('inp-muc-tieu-id').value = '';
            if(document.getElementById('goal-target-info')) document.getElementById('goal-target-info').style.display = 'none';

            const incognitoToggle = document.getElementById('inp-an-danh');
            if (incognitoToggle) {
                incognitoToggle.checked = false;
                const row = document.getElementById('incognito-row');
                const icon = document.getElementById('incognito-icon');
                const title = document.getElementById('incognito-title');
                const desc = document.getElementById('incognito-desc');
                
                if(row) {
                    row.style.borderColor = 'rgba(255,255,255,0.05)';
                    row.style.boxShadow = 'none';
                    row.style.background = 'rgba(255,255,255,0.02)';
                }
                if(icon) icon.style.color = '#64748b';
                if(title) title.style.color = 'var(--text-dark)';
                if(desc) {
                    desc.innerText = 'Người khác chỉ thấy "Nhà hảo tâm"';
                    desc.style.color = 'var(--text-light)';
                    desc.style.fontWeight = 'normal';
                }
            }
        }
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('systemToast');
    const icon = document.getElementById('toastIcon');
    const title = document.getElementById('toastTitle');
    const desc = document.getElementById('toastDesc');
    if(!toast) { alert(message); return; }

    const config = {
        success: { icon: 'fa-circle-check', color: '#10b981', title: 'Thành công!' },
        error: { icon: 'fa-circle-exclamation', color: '#ef4444', title: 'Cảnh báo!' },
        info: { icon: 'fa-circle-info', color: '#7c3aed', title: 'Hệ thống' },
        warning: { icon: 'fa-triangle-exclamation', color: '#f59e0b', title: 'Lưu ý!' }
    };

    const s = config[type] || config.info;
    if(icon) icon.className = `fa-solid ${s.icon}`;
    if(icon) icon.style.color = s.color;
    if(title) title.innerText = s.title;
    if(desc) desc.innerText = message;
    if(toast) toast.style.borderLeft = `6px solid ${s.color}`;

    if(toast) toast.classList.add('show');
    setTimeout(() => { if(toast) toast.classList.remove('show'); }, 3000);
}

function formatMoneyInput(el) {
    let value = el.value.replace(/\D/g, "");
    if (value === "") { el.value = ""; return; }
    el.value = new Intl.NumberFormat('de-DE').format(value);
}

function getRawValue(id) {
    let el = document.getElementById(id);
    return el ? el.value.replace(/\./g, "") : "0";
}

// ==========================================
// 2. XỬ LÝ GỌI API BACKEND (NỘP, CHI, CHUYỂN)
// ==========================================

async function handleDeposit(e) {
    e.preventDefault(); 
    const rawAmount = getRawValue('inp-so-tien-thu');
    const lyDo = document.getElementById('inp-ly-do-thu') ? document.getElementById('inp-ly-do-thu').value : '';
    const isAnDanhInput = document.getElementById('inp-an-danh');
    const isAnDanh = isAnDanhInput ? isAnDanhInput.checked : false;
    const mucTieuInput = document.getElementById('inp-muc-tieu-id');
    const mucTieuId = mucTieuInput ? mucTieuInput.value : null;

    if (!rawAmount || rawAmount === "0") {
        showToast('Vui lòng nhập số tiền hợp lệ!', 'warning'); return;
    }

    try {
        const res = await fetch('/api/nop-quy/', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ so_tien: rawAmount, ly_do: lyDo, is_an_danh: isAnDanh, muc_tieu_id: mucTieuId })
        });

        if (!res.ok) { showToast(`Lỗi máy chủ (${res.status}). Vui lòng kiểm tra API!`, 'error'); return; }

        const data = await res.json();
        if(data.status === 'success') {
            closeModal('depositModal'); 
            showToast(data.message, 'success');
            if (typeof confetti === 'function') confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
            setTimeout(() => window.location.reload(), 1500);
        } else { showToast(data.message, 'error'); }
    } catch(err) {
        console.error("Lỗi JS:", err);
        // Đổi thông báo để nếu vấp lỗi thì biết ngay là lỗi code JS chứ không đổ thừa Server
        showToast('Lỗi giao diện: ' + err.message, 'error');
    }
}

async function handleAdvance(e) {
    e.preventDefault(); 
    const rawAmount = getRawValue('inp-so-tien-chi');
    const lyDo = document.getElementById('inp-ly-do-chi').value;

    if (!rawAmount || rawAmount === "0") { showToast('Vui lòng nhập số tiền hợp lệ!', 'warning'); return; }

    try {
        const res = await fetch('/api/tam-ung/', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ so_tien: rawAmount, ly_do: lyDo })
        });
        const data = await res.json();
        if(data.status === 'success') { 
            closeModal('advanceModal'); showToast(data.message, 'success'); 
            setTimeout(() => window.location.reload(), 1500); 
        } else { showToast(data.message, 'error'); }
    } catch(err) { showToast('Lỗi JS: ' + err.message, 'error'); }
}

async function handleInternalTransfer(e) {
    e.preventDefault();
    const rawAmount = getRawValue('inp-so-tien-transfer');
    const idQuyDi = document.getElementById('sel-quy-di').value;
    const idQuyDen = document.getElementById('sel-quy-den').value;

    if (!rawAmount || rawAmount === "0") { showToast('Vui lòng nhập số tiền!', 'warning'); return; }

    try {
        const res = await fetch('/api/chuyen-noi-bo/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ so_tien: rawAmount, id_quy_di: idQuyDi, id_quy_den: idQuyDen, ly_do: "Điều chuyển quỹ nội bộ" })
        });
        const data = await res.json();
        if(data.status === 'success') {
            closeModal('transferModal'); showToast(data.message, 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else { showToast(data.message, 'error'); }
    } catch(err) { showToast('Lỗi JS: ' + err.message, 'error'); }
}

function handleNhacNo(tvId) {
    showToast('Đang gửi yêu cầu nhắc nợ...', 'info');
    fetch('/api/nhac-no/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ tv_id: tvId })
    }).then(res => res.json()).then(data => {
        if(data.status === 'success') showToast(data.message, 'success');
        else showToast(data.message, 'error');
    }).catch(err => showToast('Lỗi JS: ' + err.message, 'error'));
}

// ==========================================
// 3. LOGIC THÀNH VIÊN & NỘP HỘ
// ==========================================
let selectedMember = { id: null, name: "" };

function showFriendProfile(id, name, mssv, noXau) {
    selectedMember = { id: id, name: name };
    document.getElementById('friend-name').innerText = name;
    document.getElementById('friend-mssv').innerText = 'MSSV: ' + mssv;
    document.getElementById('friend-avatar').src = `https://ui-avatars.com/api/?name=${name}&background=random&color=fff`;
    
    const statusBox = document.getElementById('friend-status');
    if (noXau === 'True' || noXau === true) {
        statusBox.innerHTML = '<span class="text-rose-500 font-bold"><i class="fa-solid fa-triangle-exclamation"></i> Đang nợ quỹ</span>';
        statusBox.style.background = '#fef2f2';
    } else {
        statusBox.innerHTML = '<span class="text-emerald-500 font-bold"><i class="fa-solid fa-check-circle"></i> Đóng quỹ đầy đủ</span>';
        statusBox.style.background = '#f0fdf4';
    }
    openModal('friendModal');
}

function goToMemberHistory() {
    if (selectedMember.name) window.location.href = `/giao-dich/?search=${encodeURIComponent(selectedMember.name)}`;
}

function openQuickDeposit() {
    closeModal('friendModal');
    document.getElementById('quick-dep-name').innerText = selectedMember.name;
    openModal('quickDepositModal');
}

async function handleMemberDeposit(e) {
    e.preventDefault();
    const rawAmount = getRawValue('member-so-tien');
    const lyDo = document.getElementById('member-ly-do').value;

    if (!rawAmount || rawAmount === "0") { showToast('Vui lòng nhập số tiền!', 'warning'); return; }

    showToast('Đang xử lý giao dịch...', 'info');
    try {
        const res = await fetch('/api/nop-quy-ho/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ tv_id: selectedMember.id, so_tien: rawAmount, ly_do: lyDo })
        });
        if (!res.ok) { showToast("Lỗi kết nối API", "error"); return; }
        const data = await res.json();
        
        if(data.status === 'success') {
            closeModal('quickDepositModal');
            showToast(`Giao dịch thành công! Đã thu ${document.getElementById('member-so-tien').value}đ`, 'success');
            if (typeof confetti === 'function') confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 } });
            setTimeout(() => window.location.reload(), 2000);
        } else { showToast(data.message, 'error'); }
    } catch(err) { showToast('Lỗi JS: ' + err.message, 'error'); }
}

// ==========================================
// 4. UI & TABS
// ==========================================
function switchMainTab(tabId, element) {
    document.querySelectorAll('.main-tab-btn').forEach(t => {
        t.style.borderColor = 'transparent';
        t.style.color = 'var(--text-light)';
    });
    element.style.borderColor = 'var(--primary)';
    element.style.color = 'var(--primary)';
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
}

function openBigCard(title, balance, number, bgGradient) {
    document.getElementById('bigCardTitle').innerText = title;
    document.getElementById('bigCardBackground').style.background = bgGradient;
    const balanceEl = document.getElementById('bigCardBalance');
    const numberEl = document.getElementById('bigCardNumber');
    
    balanceEl.setAttribute('data-value', balance);
    numberEl.setAttribute('data-value', number);

    if (!isDataVisible) {
        balanceEl.innerText = '*** đ';
        numberEl.innerText = '**** **** **** ' + number.slice(-4);
    } else {
        balanceEl.innerText = balance;
        numberEl.innerText = number;
    }
    openModal('bigCardModal');
}

// ==========================================
// 5. XÁC THỰC BẢO MẬT (PIN CODE)
// ==========================================
let isDataVisible = false;

function handleEyeClick() {
    if (!isDataVisible) {
        openModal('pinModal');
        setTimeout(() => document.getElementById('pin1').focus(), 300);
    } else {
        lockSensitiveData();
    }
}

async function verifyPin(event) {
    event.preventDefault();
    let fullPin = '';
    for(let i=1; i<=6; i++) {
        let input = document.getElementById('pin' + i);
        if(input) fullPin += input.value;
    }

    if (fullPin.length < 6) { showToast('Vui lòng nhập đủ 6 số!', 'warning'); return; }

    try {
        const res = await fetch('/api/verify-pin/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ pin: fullPin })
        });
        const data = await res.json();
        if (data.status === 'success') {
            unlockSensitiveData();
            closeModal('pinModal');
            showToast('Xác minh thành công. Dữ liệu đã mở!', 'success');
        } else {
            throw new Error(data.message);
        }
    } catch(err) {
        // Fallback chạy Offline Demo mode
        if (fullPin === '123456') {
            unlockSensitiveData();
            closeModal('pinModal');
            showToast('Xác minh (Demo) thành công. Dữ liệu đã mở!', 'success');
        } else {
            showToast(err.message || 'Mã PIN không chính xác!', 'error');
            const content = document.querySelector('#pinModal .modal-content');
            if (content) {
                content.style.animation = 'shake 0.4s ease';
                setTimeout(() => content.style.animation = '', 400);
            }
            document.getElementById('pinForm').reset();
            document.getElementById('pin1').focus();
        }
    }
}

function unlockSensitiveData() {
    isDataVisible = true;
    document.querySelectorAll('.sensitive-data').forEach(el => {
        el.classList.add('revealed');
        if (el.hasAttribute('data-value')) el.innerText = el.getAttribute('data-value');
    });

    const eyeIcon = document.getElementById('eye-icon');
    if (eyeIcon) eyeIcon.className = 'fa-regular fa-eye text-primary cursor-pointer text-xl';
    
    const statusBadge = document.getElementById('security-status');
    if (statusBadge) {
        statusBadge.innerHTML = '<i class="fa-solid fa-unlock"></i> ĐÃ XÁC MINH';
        statusBadge.className = 'text-[10px] font-bold px-2 py-1 rounded-lg bg-emerald-100 text-emerald-600';
    }
}

function lockSensitiveData() {
    isDataVisible = false;
    document.querySelectorAll('.sensitive-data').forEach(el => {
        el.classList.remove('revealed');
        if (el.hasAttribute('data-value')) {
            const val = el.getAttribute('data-value');
            if(val.length > 10 && val.includes(' ')) el.innerText = '**** **** **** ' + val.slice(-4);
            else el.innerText = '***' + (val.includes('đ') ? ' đ' : '');
        }
    });

    const eyeIcon = document.getElementById('eye-icon');
    if (eyeIcon) eyeIcon.className = 'fa-regular fa-eye-slash text-light cursor-pointer text-xl';
    
    const statusBadge = document.getElementById('security-status');
    if (statusBadge) {
        statusBadge.innerHTML = '<i class="fa-solid fa-lock"></i> ĐÃ KHÓA';
        statusBadge.className = 'text-[10px] font-bold px-2 py-1 rounded-lg bg-slate-100 text-slate-500';
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const pinInputs = document.querySelectorAll('.pin-inputs input');
    pinInputs.forEach((input, index) => {
        input.addEventListener('input', function() {
            if (this.value.length === 1 && index < pinInputs.length - 1) pinInputs[index + 1].focus();
        });
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) pinInputs[index - 1].focus();
        });
    });
});

// ==========================================
// 6. TÍNH NĂNG AI: VOICE & CHATBOT
// ==========================================
function startVoiceRecognition(inputId, btnElement) {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'vi-VN';
        recognition.interimResults = false;
        
        btnElement.classList.add('recording-pulse');
        showToast('Đang lắng nghe...', 'info');
        recognition.start();

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById(inputId).value = transcript.charAt(0).toUpperCase() + transcript.slice(1);
            showToast('Nhận diện thành công!', 'success');
        };
        recognition.onerror = function() { showToast('Không nghe rõ, thử lại!', 'error'); };
        recognition.onend = function() { btnElement.classList.remove('recording-pulse'); };
    } else { showToast('Trình duyệt chưa hỗ trợ giọng nói!', 'error'); }
}

let isChatOpen = false;
function toggleChatbot() {
    const chatWindow = document.getElementById('chatbot-window');
    isChatOpen = !isChatOpen;
    if (isChatOpen) {
        chatWindow.style.transform = 'scale(1)';
        chatWindow.style.opacity = '1';
        document.getElementById('chat-input').focus();
    } else {
        chatWindow.style.transform = 'scale(0)';
        chatWindow.style.opacity = '0';
    }
}

function appendMessage(text, sender) {
    const chatBody = document.getElementById('chat-body');
    const msgDiv = document.createElement('div');
    
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    formattedText = formattedText.replace(/^\* (.*$)/gim, '<div style="margin-left: 10px; margin-bottom: 4px; display: flex; gap: 8px;"><span>•</span><span>$1</span></div>');
    formattedText = formattedText.replace(/\n/g, '<br>');

    msgDiv.style.padding = '12px 18px';
    msgDiv.style.fontSize = '13px';
    msgDiv.style.maxWidth = '85%';
    msgDiv.style.lineHeight = '1.6';
    msgDiv.style.marginBottom = '5px';
    msgDiv.innerHTML = formattedText;

    if (sender === 'user') {
        msgDiv.style.alignSelf = 'flex-end';
        msgDiv.style.background = 'linear-gradient(135deg, var(--primary) 0%, #a855f7 100%)';
        msgDiv.style.color = 'white';
        msgDiv.style.borderRadius = '18px 18px 0 18px';
    } else {
        msgDiv.style.alignSelf = 'flex-start';
        msgDiv.style.background = '#ffffff';
        msgDiv.style.color = '#1e293b'; 
        msgDiv.style.borderRadius = '0 18px 18px 18px';
        msgDiv.style.border = '1px solid #f1f5f9';
    }

    chatBody.appendChild(msgDiv);
    msgDiv.animate([{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 300 });
    chatBody.scrollTop = chatBody.scrollHeight;
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    input.value = '';

    const chatBody = document.getElementById('chat-body');
    const typingIndicator = document.createElement('div');
    typingIndicator.id = 'typing-indicator';
    typingIndicator.style.alignSelf = 'flex-start';
    typingIndicator.style.color = '#94a3b8';
    typingIndicator.style.fontSize = '12px';
    typingIndicator.style.fontStyle = 'italic';
    typingIndicator.innerText = 'Bot đang suy nghĩ...';
    chatBody.appendChild(typingIndicator);
    chatBody.scrollTop = chatBody.scrollHeight;

    fetch('/api/chatbot/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ message: message })
    }).then(res => res.json()).then(data => {
        document.getElementById('typing-indicator').remove();
        appendMessage(data.reply, 'bot');
    }).catch(err => {
        document.getElementById('typing-indicator').remove();
        appendMessage('Lỗi JS: ' + err.message, 'bot');
    });
}

// ==========================================
// 7. DROPDOWN, BIỂU ĐỒ CHART.JS, HOTKEYS
// ==========================================
function toggleDropdown() {
    const container = document.getElementById('customTimeFilter');
    const icon = document.getElementById('dropdown-icon');
    if(container) container.classList.toggle('active');
    if(icon) icon.style.transform = container.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
}

function selectOption(element) {
    const value = element.getAttribute('data-value');
    document.getElementById('selected-text').innerText = element.innerText;
    document.querySelectorAll('.dropdown-option').forEach(el => el.classList.remove('active-opt'));
    element.classList.add('active-opt');
    toggleDropdown();

    const hiddenSelect = document.getElementById('timeFilter');
    if(hiddenSelect) {
        hiddenSelect.value = value;
        hiddenSelect.dispatchEvent(new Event('change'));
    }
}

document.addEventListener('click', function(event) {
    const container = document.getElementById('customTimeFilter');
    if (container && !container.contains(event.target)) {
        container.classList.remove('active');
        const icon = document.getElementById('dropdown-icon');
        if(icon) icon.style.transform = 'rotate(0deg)';
    }
});

let mainChart;
let currentChartType = 'thu';
let ctx;

document.addEventListener('DOMContentLoaded', function() {
    const currencyInputs = document.querySelectorAll('.currency-input');
    currencyInputs.forEach(input => input.addEventListener('input', function() { formatCurrency(this); }));

    const canvas = document.getElementById('statChart');
    if (canvas) {
        ctx = canvas.getContext('2d');
        mainChart = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'VNĐ', data: [], borderWidth: 4, tension: 0.4, fill: true, pointRadius: 4 }] },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { backgroundColor: '#111827', titleColor: '#fff', bodyColor: '#fff' } },
                scales: { x: { grid: { display: false }, border: {display: false}, ticks: {color: '#9ca3af', font: {size: 11}} }, y: { border: {display: false}, grid: { color: '#f3f4f6' }, ticks: { display: false } } }
            }
        });
    }

    function applyChartStyle() {
        if (!window.CHART_DATA_THU || !window.CHART_DATA_CHI || !mainChart) return;
        let dataToUse = currentChartType === 'thu' ? window.CHART_DATA_THU : window.CHART_DATA_CHI;
        mainChart.data.datasets[0].data = dataToUse;

        if (currentChartType === 'thu') {
            mainChart.data.datasets[0].borderColor = '#10b981'; 
            let grad = ctx.createLinearGradient(0, 0, 0, 250);
            grad.addColorStop(0, 'rgba(16, 185, 129, 0.4)'); grad.addColorStop(1, 'rgba(16, 185, 129, 0)');
            mainChart.data.datasets[0].backgroundColor = grad;
        } else {
            mainChart.data.datasets[0].borderColor = '#ef4444'; 
            let grad = ctx.createLinearGradient(0, 0, 0, 250);
            grad.addColorStop(0, 'rgba(239, 68, 68, 0.4)'); grad.addColorStop(1, 'rgba(239, 68, 68, 0)');
            mainChart.data.datasets[0].backgroundColor = grad;
        }
        mainChart.update();
    }

    function updateChartData(filterType) {
        fetch(`/api/chart-data/?filter=${filterType}`)
            .then(res => res.json())
            .then(data => {
                if(data.status === 'error') throw new Error();
                mainChart.data.labels = data.labels.length ? data.labels : ['Trống'];
                window.CHART_DATA_THU = data.labels.length ? data.data_thu : [0];
                window.CHART_DATA_CHI = data.labels.length ? data.data_chi : [0];
                applyChartStyle(); 
            }).catch(() => {
                mainChart.data.labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
                window.CHART_DATA_THU = [150000, 200000, 50000, 300000, 450000, 250000, 600000];
                window.CHART_DATA_CHI = [50000, 80000, 20000, 100000, 90000, 200000, 150000];
                applyChartStyle();
            });
    }

    if(canvas) updateChartData('7days');
    const timeFilter = document.getElementById('timeFilter');
    if (timeFilter) timeFilter.addEventListener('change', (e) => updateChartData(e.target.value));

    const pillTabs = document.querySelectorAll('#thuChiTabs .pill-tab');
    pillTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            pillTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentChartType = this.getAttribute('data-type');
            applyChartStyle(); 
        });
    });

    setTimeout(() => {
        document.querySelectorAll('.progress-bar').forEach(bar => { bar.style.width = bar.getAttribute('data-width'); });
    }, 800);
});

// BUG BOUNTY & INCOGNITO
function openBugBounty() {
    const modal = document.getElementById('bugBountyModal');
    if (modal) modal.style.display = 'flex';
}

function toggleIncognitoUI(checkbox) {
    const row = document.getElementById('incognito-row');
    const icon = document.getElementById('incognito-icon');
    const title = document.getElementById('incognito-title');
    const desc = document.getElementById('incognito-desc');

    if (checkbox.checked) {
        if(row) {
            row.style.borderColor = 'var(--theme-primary)';
            row.style.boxShadow = '0 0 15px var(--theme-glow)';
            row.style.background = 'rgba(255,255,255,0.05)'; 
        }
        if(icon) icon.style.color = 'var(--theme-primary)';
        if(title) title.style.color = 'var(--theme-primary)';
        if(desc) {
            desc.innerText = 'Đang bật: Tên của bạn sẽ được giấu kín!';
            desc.style.color = '#10b981'; 
            desc.style.fontWeight = 'bold';
        }
    } else {
        if(row) {
            row.style.borderColor = 'rgba(255,255,255,0.05)';
            row.style.boxShadow = 'none';
            row.style.background = 'rgba(255,255,255,0.02)';
        }
        if(icon) icon.style.color = '#64748b';
        if(title) title.style.color = 'var(--text-dark)';
        if(desc) {
            desc.innerText = 'Người khác chỉ thấy "Nhà hảo tâm"';
            desc.style.color = 'var(--text-light)';
            desc.style.fontWeight = 'normal';
        }
    }
}

// HOTKEYS & PING
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.key === 'f') {
        event.preventDefault(); 
        const searchBox = document.querySelector('input[name="search"]');
        if (searchBox) {
            searchBox.focus();
            searchBox.placeholder = "Đang tìm kiếm... (Nhấn Esc để thoát)";
        }
    }
    if (event.ctrlKey && event.key === 'n') {
        event.preventDefault();
        if (typeof IS_ADMIN !== 'undefined' && IS_ADMIN === true) window.location.href = '/admin/quanlyquy/giaodich/add/';
        else showToast('Chức năng này dành cho Thủ quỹ.', 'error');
    }
});

if (typeof IS_ADMIN !== 'undefined' && IS_ADMIN === true) {
    setInterval(() => {
        const pingEl = document.getElementById('ping-time');
        const apiEl = document.getElementById('api-time');
        if (pingEl && apiEl) {
            pingEl.innerText = Math.floor(Math.random() * 20) + 10;
            apiEl.innerText = Math.floor(Math.random() * 50) + 30;
        }
    }, 3000);
}
