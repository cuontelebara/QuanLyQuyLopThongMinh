document.addEventListener('DOMContentLoaded', function() {
    // 1. Hàm định dạng tiền chi tiết (khi chỉ chuột vào)
    const formatVND = (value) => new Intl.NumberFormat('vi-VN').format(value) + ' đ';

    // 2. HÀM MỚI: Rút gọn số (Tr, K) cho trục Y
    const compactMoney = (value) => {
        if (value >= 1000000000) return (value / 1000000000).toLocaleString('vi-VN') + ' Tỷ';
        if (value >= 1000000) return (value / 1000000).toLocaleString('vi-VN') + ' Tr';
        if (value >= 1000) return (value / 1000).toLocaleString('vi-VN') + ' K';
        return value;
    };

    // 3. Hàm đọc dữ liệu cực an toàn (Thần chú JS)
    const getJSONData = (id) => {
        const el = document.getElementById(id);
        if (!el) return [];
        try { 
            let data = JSON.parse(el.textContent); 
            if (typeof data === 'string') data = JSON.parse(data);
            return Array.isArray(data) ? data : [];
        } catch(e) { return []; }
    };

    // ==========================================
    // CẤU HÌNH GIAO DIỆN CHUẨN UI/UX DOANH NGHIỆP
    // ==========================================
    Chart.defaults.color = '#94a3b8'; // Màu chữ xám nhạt hiện đại
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
    
    // Tút tát lại cái Tooltip (khung thông tin khi hover)
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
    Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: 'bold' };
    Chart.defaults.plugins.tooltip.bodyFont = { size: 13 };
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    
    // Đổi hình vuông thành chấm tròn cho các chú thích (Legend)
    Chart.defaults.plugins.legend.labels.usePointStyle = true; 
    Chart.defaults.plugins.legend.labels.boxWidth = 8;

    const gridConfig = { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false };

    // --- ĐỌC DỮ LIỆU ---
    const c1_labels = getJSONData('c1-labels'), c1_thu = getJSONData('c1-thu'), c1_chi = getJSONData('c1-chi');
    const c2_labels = getJSONData('c2-labels'), c2_data = getJSONData('c2-data');
    const c3_labels = getJSONData('c3-labels'), c3_data = getJSONData('c3-data');
    const c4_labels = getJSONData('c4-labels'), c4_dathu = getJSONData('c4-dathu'), c4_no = getJSONData('c4-no');
    const c5_labels = getJSONData('c5-labels'), c5_data = getJSONData('c5-data');

    // --- AI PREDICTION (Dự báo) ---
    if (c1_labels.length >= 2) {
        const predict = (dataArray) => {
            let n = dataArray.length;
            let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
            for (let i = 0; i < n; i++) {
                sumX += i; sumY += dataArray[i];
                sumXY += i * dataArray[i]; sumXX += i * i;
            }
            let m = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
            let b = (sumY - m * sumX) / n;
            let pred = m * n + b;
            return pred > 0 ? Math.round(pred) : 0;
        };
        c1_labels.push('Tháng tới (AI)');
        c1_thu.push(predict(c1_thu));
        c1_chi.push(predict(c1_chi));
    }

    // ==========================================
    // VẼ 5 BIỂU ĐỒ (ÁP DỤNG RÚT GỌN SỐ TRỤC Y)
    // ==========================================
    
    // 1. Biểu đồ đường (Tăng trưởng) - Có chấm tròn & bóng mờ
    if(document.getElementById('trendChart')) {
        new Chart(document.getElementById('trendChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: c1_labels,
                datasets: [
                    { 
                        label: 'Thu vào', data: c1_thu, borderColor: '#10b981', 
                        backgroundColor: 'rgba(16, 185, 129, 0.15)', fill: true, 
                        tension: 0.4, pointRadius: 4, pointHoverRadius: 6, borderWidth: 2 
                    },
                    { 
                        label: 'Chi ra', data: c1_chi, borderColor: '#ef4444', 
                        tension: 0.4, pointRadius: 4, pointHoverRadius: 6, borderWidth: 2 
                    }
                ]
            },
            options: { 
                maintainAspectRatio: false, 
                interaction: { mode: 'index', intersect: false }, // Hover 1 lúc lên cả 2 cột
                plugins: { 
                    tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatVND(ctx.raw)}` } },
                    legend: { position: 'top', align: 'end' } // Nằm trên góc phải
                },
                scales: {
                    x: { grid: { display: false } }, // Ẩn lưới dọc cho giống mẫu
                    y: { 
                        grid: gridConfig, border: { display: false },
                        ticks: { callback: (value) => compactMoney(value) } // ÉP SỐ RÚT GỌN
                    }
                }
            }
        });
    }

    // 2. Biểu đồ Doughnut (Cơ cấu chi tiêu)
    if(document.getElementById('expensePieChart')) {
        new Chart(document.getElementById('expensePieChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: c2_labels.length ? c2_labels : ['Trống'],
                datasets: [{ 
                    data: c2_data.length ? c2_data : [1], 
                    backgroundColor: ['#8b5cf6', '#3b82f6', '#f43f5e', '#f59e0b', '#10b981'], 
                    borderWidth: 0, hoverOffset: 5 // Nảy lên khi hover
                }]
            },
            options: { 
                maintainAspectRatio: false, cutout: '75%', 
                plugins: { 
                    tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${formatVND(ctx.raw)}` } },
                    legend: { position: 'right' } // Dời legend qua phải giống hình
                } 
            }
        });
    }

    // 3. Biểu đồ Bar Ngang (Top đóng góp)
    if(document.getElementById('topMemberChart')) {
        new Chart(document.getElementById('topMemberChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: c3_labels,
                datasets: [{ 
                    label: 'Đã đóng', data: c3_data, 
                    backgroundColor: '#8b5cf6', borderRadius: 4, barThickness: 15 
                }]
            },
            options: { 
                indexAxis: 'y', maintainAspectRatio: false, 
                plugins: { 
                    tooltip: { callbacks: { label: (ctx) => ` Đã đóng: ${formatVND(ctx.raw)}` } },
                    legend: { display: false } // Ẩn legend cho gọn
                },
                scales: {
                    x: { 
                        grid: gridConfig, border: { display: false },
                        ticks: { callback: (value) => compactMoney(value) } // ÉP SỐ RÚT GỌN 
                    },
                    y: { grid: { display: false }, border: { display: false } }
                }
            }
        });
    }

    // 4. Biểu đồ Stacked Bar (Tiến độ thu)
    if(document.getElementById('progressChart')) {
        new Chart(document.getElementById('progressChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: c4_labels,
                datasets: [
                    { label: 'Đã thu', data: c4_dathu, backgroundColor: '#10b981', borderRadius: {topLeft: 0, topRight: 0, bottomLeft: 4, bottomRight: 4} },
                    { label: 'Còn nợ', data: c4_no, backgroundColor: '#334155', borderRadius: {topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0} }
                ]
            },
            options: { 
                maintainAspectRatio: false, 
                plugins: { tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatVND(ctx.raw)}` } }, legend: { position: 'top', align: 'end' } },
                scales: { 
                    x: { stacked: true, grid: { display: false }, border: { display: false } }, 
                    y: { 
                        stacked: true, grid: gridConfig, border: { display: false },
                        ticks: { callback: (value) => compactMoney(value) } // ÉP SỐ RÚT GỌN
                    } 
                } 
            }
        });
    }

    // 5. Biểu đồ Phân bổ quỹ (Đổi thành Doughnut luôn cho đồng bộ)
    if(document.getElementById('fundDistributionChart')) {
        new Chart(document.getElementById('fundDistributionChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: c5_labels.length ? c5_labels : ['Trống'],
                datasets: [{ 
                    data: c5_data.length ? c5_data : [1], 
                    backgroundColor: ['#0ea5e9', '#f59e0b', '#10b981'], 
                    borderWidth: 0, hoverOffset: 5 
                }]
            },
            options: { 
                maintainAspectRatio: false, cutout: '65%',
                plugins: { tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${formatVND(ctx.raw)}` } }, legend: { position: 'right' } } 
            }
        });
    }
});


// --- 2. CHATBOT AI ---
window.toggleChatbot = function() {
    const bot = document.getElementById('chatbot-window');
    if(!bot) return;
    if(bot.style.transform === 'scale(1)') {
        bot.style.transform = 'scale(0)'; bot.style.opacity = '0';
    } else {
        bot.style.transform = 'scale(1)'; bot.style.opacity = '1';
        setTimeout(() => { document.getElementById('chat-input').focus(); }, 100);
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