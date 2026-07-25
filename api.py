<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>STASHServiceDesk</title>
    <style>
        :root {
            --bg-primary: #0b1a2f;
            --bg-secondary: #112240;
            --bg-card: #1a2d4a;
            --text-primary: #e8edf3;
            --text-secondary: #8ba0c7;
            --accent: #f5a623;
            --shadow: 0 4px 20px rgba(0,0,0,0.4);
            --radius: 12px;
            --nav-height: 60px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 16px;
            min-height: 100vh;
            padding-bottom: calc(var(--nav-height) + 20px);
        }
        /* ===== HEADER ===== */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0 16px;
            border-bottom: 2px solid var(--accent);
            margin-bottom: 16px;
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .header-icon { font-size: 24px; font-weight: 700; color: var(--accent); }
        .header-icon span { color: var(--text-primary); }
        .header h1 { font-size: 16px; font-weight: 600; }
        .header h1 small { display: block; font-size: 9px; font-weight: 400; color: var(--text-secondary); text-transform: uppercase; }
        .header-badge { background: var(--accent); color: var(--bg-primary); font-weight: 700; padding: 2px 12px; border-radius: 20px; font-size: 13px; }
        .back-btn {
            background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer;
            padding: 4px 8px; border-radius: 8px; transition: 0.2s;
        }
        .back-btn:hover { background: var(--bg-card); }

        /* ===== СТРАНИЦЫ ===== */
        .page { display: none; }
        .page.active { display: block; }

        /* ===== СТАТИСТИКА ===== */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 16px;
        }
        .stat-card {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            padding: 10px 8px;
            text-align: center;
            border-bottom: 3px solid var(--accent);
        }
        .stat-number { font-size: 24px; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 9px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

        /* ===== ПОИСК ===== */
        .search-wrapper { position: relative; margin-bottom: 12px; }
        .search-wrapper input {
            width: 100%; padding: 10px 16px;
            border: 1px solid var(--bg-secondary); border-radius: var(--radius);
            font-size: 14px; background: var(--bg-secondary); color: var(--text-primary); outline: none;
        }
        .search-wrapper input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(245, 166, 35, 0.2); }

        /* ===== ФИЛЬТРЫ ===== */
        .filters {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .filter-btn {
            padding: 4px 12px;
            border: 1px solid var(--bg-secondary);
            border-radius: 16px;
            background: transparent;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }
        .filter-btn.active {
            background: var(--accent);
            border-color: var(--accent);
            color: var(--bg-primary);
        }

        /* ===== СПИСОК ЗАКАЗОВ ===== */
        .order-list { display: flex; flex-direction: column; gap: 10px; }
        .order-card {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            padding: 14px;
            cursor: pointer;
            border-left: 4px solid var(--accent);
            transition: 0.2s;
        }
        .order-card:active { transform: scale(0.98); }
        .order-card .top-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }
        .order-number { font-weight: 700; font-size: 15px; }
        .order-status {
            font-size: 10px;
            font-weight: 600;
            padding: 2px 10px;
            border-radius: 10px;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .status-new { background: #1e3a5f; color: #93bbfc; }
        .status-repair { background: #5f3a1e; color: #fbbf7c; }
        .status-consultation { background: #4a1e5f; color: #d8b4fe; }
        .status-waiting { background: #5f4a1e; color: #fcd34d; }
        .status-warranty { background: #1e4a3a; color: #6ee7a7; }
        .status-ready { background: #1e3a2a; color: #34d399; }
        .status-notpaid { background: #4a1e1e; color: #fca5a5; }
        .status-paid { background: #1a3a2a; color: #86efac; }
        .status-default { background: #2d2d3f; color: #9ca3af; }

        .order-card .info {
            margin-top: 6px;
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            flex-wrap: wrap;
            gap: 4px 12px;
        }
        .order-card .device {
            margin-top: 4px;
            font-size: 13px;
            color: var(--text-primary);
            font-weight: 500;
        }

        /* ===== ДЕТАЛИ ЗАКАЗА ===== */
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
        }
        .detail-row .label { color: var(--text-secondary); }
        .detail-row .value { font-weight: 500; text-align: right; max-width: 60%; }

        /* ===== ИСТОРИЯ СТАТУСОВ (цветная лента) ===== */
        .history-timeline { margin-top: 6px; }
        .history-item {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            font-size: 13px;
            align-items: center;
        }
        .history-item .h-status { display: flex; align-items: center; gap: 8px; }
        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .history-item .h-time { color: var(--text-secondary); font-size: 12px; }

        /* ===== КОНТАКТНЫЕ КНОПКИ ===== */
        .contact-btn {
            flex: 1;
            min-width: 44px;
            color: white;
            padding: 8px 8px;
            border-radius: var(--radius);
            font-size: 12px;
            font-weight: 600;
            text-align: center;
            border: none;
            cursor: pointer;
            background: var(--bg-card);
            border-bottom: 3px solid transparent;
            transition: 0.2s;
        }
        .contact-btn:active { transform: scale(0.95); }
        .contact-btn.call { background: #1a3a2a; border-bottom-color: #22c55e; color: #86efac; }
        .contact-btn.viber { background: #2a1a4a; border-bottom-color: #8b5cf6; color: #c4b5fd; }
        .contact-btn.telegram { background: #1a2a4a; border-bottom-color: #3b82f6; color: #93bbfc; }
        .contact-btn.copy { background: #2a2a3a; border-bottom-color: var(--text-secondary); color: var(--text-secondary); flex: 0.3; min-width: 36px; }

        /* ===== КНОПКИ КЛИЕНТА ===== */
        .client-btn {
            padding: 8px;
            background: var(--bg-card);
            border: 1px solid var(--accent);
            border-radius: var(--radius);
            color: var(--text-primary);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }
        .client-btn:active { transform: scale(0.95); }

        /* ===== СПИСОК ЗАКАЗОВ КЛИЕНТА ===== */
        .client-order-item {
            cursor: pointer;
            padding: 6px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: 0.2s;
            font-size: 13px;
        }
        .client-order-item:hover { background: var(--bg-card); }

        /* ===== СТАТИСТИКА КЛИЕНТА ===== */
        .client-stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            padding: 8px 0;
        }
        .client-stat-item {
            background: var(--bg-card);
            padding: 8px;
            border-radius: 8px;
            text-align: center;
        }
        .client-stat-item .num { font-size: 18px; font-weight: 700; color: var(--accent); }
        .client-stat-item .label { font-size: 10px; color: var(--text-secondary); }

        /* ===== НАВИГАЦИЯ ===== */
        .nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: var(--nav-height);
            background: var(--bg-secondary);
            border-top: 1px solid rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 0 16px;
            z-index: 100;
        }
        .nav-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            padding: 8px 16px;
            border-radius: 8px;
            transition: 0.2s;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
        }
        .nav-btn .icon { font-size: 20px; }
        .nav-btn.active { color: var(--accent); background: rgba(245, 166, 35, 0.1); }
        .nav-btn:active { transform: scale(0.95); }

        /* ===== ОБЩЕЕ ===== */
        .empty-state { text-align: center; padding: 40px 20px; color: var(--text-secondary); }
        .empty-state .icon { font-size: 40px; margin-bottom: 8px; }
        .loader { text-align: center; padding: 30px 0; color: var(--text-secondary); }
        .spinner {
            width: 30px; height: 30px;
            border: 3px solid var(--bg-secondary);
            border-top: 3px solid var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .hidden { display: none !important; }

        @media (max-width: 480px) {
            body { padding: 12px; padding-bottom: calc(var(--nav-height) + 16px); }
            .stats-grid { gap: 6px; }
            .stat-number { font-size: 20px; }
            .stat-card { padding: 8px 4px; }
            .header h1 { font-size: 14px; }
        }
        @media (min-width: 600px) {
            .order-list { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        }
        @media (min-width: 900px) {
            .order-list { grid-template-columns: 1fr 1fr 1fr; }
            body { max-width: 1100px; margin: 0 auto; }
        }
    </style>
</head>
<body>

    <!-- ===== НАВИГАЦИЯ ===== -->
    <div class="nav" id="nav">
        <button class="nav-btn active" data-page="orders" onclick="navigateTo('orders')">
            <span class="icon">📋</span> Заказы
        </button>
        <button class="nav-btn" data-page="dashboard" onclick="navigateTo('dashboard')">
            <span class="icon">📊</span> Аналитика
        </button>
        <button class="nav-btn" data-page="profile" onclick="navigateTo('profile')">
            <span class="icon">👤</span> Профиль
        </button>
    </div>

    <!-- ===== СТРАНИЦА: ЗАКАЗЫ ===== -->
    <div class="page active" id="page-orders">
        <div class="header">
            <div class="header-left">
                <div class="header-icon">ST<span>ASH</span></div>
                <div>
                    <h1 id="userGreeting">ServiceDesk <small>сервисный центр</small></h1>
                </div>
            </div>
            <span class="header-badge" id="totalBadge">0</span>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number" id="statTotal">0</div><div class="stat-label">Всего</div></div>
            <div class="stat-card"><div class="stat-number" id="statToday">0</div><div class="stat-label">Сегодня</div></div>
            <div class="stat-card"><div class="stat-number" id="statStatuses">0</div><div class="stat-label">Статусов</div></div>
        </div>

        <div class="search-wrapper">
            <input type="text" id="searchInput" placeholder="🔍 Поиск по номеру, телефону, ФИО, устройству..." />
        </div>

        <div class="filters" id="filters">
            <button class="filter-btn active" data-filter="all">Все</button>
            <button class="filter-btn" data-filter="Принят в ремонт">Принят</button>
            <button class="filter-btn" data-filter="В ремонте">Ремонт</button>
            <button class="filter-btn" data-filter="Согласование с клиентом">Согласование</button>
            <button class="filter-btn" data-filter="Ожидание запчасти">Ожидание</button>
            <button class="filter-btn" data-filter="Гарантия">Гарантия</button>
            <button class="filter-btn" data-filter="Готово">Готово</button>
            <button class="filter-btn" data-filter="Выдано (не оплачено)">Не оплачено</button>
            <button class="filter-btn" data-filter="Выдано (оплачено)">Оплачено</button>
        </div>

        <div class="order-list" id="orderList"><div class="loader"><div class="spinner"></div>Загрузка заказов...</div></div>
    </div>

    <!-- ===== СТРАНИЦА: ДЕТАЛИ ЗАКАЗА ===== -->
    <div class="page" id="page-order-detail">
        <div class="header">
            <div class="header-left">
                <button class="back-btn" onclick="navigateTo('orders')">‹</button>
                <div>
                    <h1 id="detailTitle">Заказ #000000</h1>
                </div>
            </div>
        </div>
        <div id="detailContent"></div>
    </div>

    <!-- ===== СТРАНИЦА: КЛИЕНТ ===== -->
    <div class="page" id="page-client">
        <div class="header">
            <div class="header-left">
                <button class="back-btn" onclick="goBackFromClient()">‹</button>
                <div>
                    <h1 id="clientTitle">Клиент</h1>
                </div>
            </div>
        </div>
        <div id="clientContent"></div>
    </div>

    <!-- ===== СТРАНИЦА: АНАЛИТИКА ===== -->
    <div class="page" id="page-dashboard">
        <div class="header">
            <div class="header-left">
                <div class="header-icon">ST<span>ASH</span></div>
                <div>
                    <h1>Аналитика</h1>
                </div>
            </div>
        </div>
        <div id="dashboardPanel">
            <div id="dashboardContent"><div class="loader"><div class="spinner"></div>Загрузка...</div></div>
        </div>
    </div>

    <!-- ===== СТРАНИЦА: ПРОФИЛЬ ===== -->
    <div class="page" id="page-profile">
        <div class="header">
            <div class="header-left">
                <div class="header-icon">👤</div>
                <div>
                    <h1 id="profileName">Профиль</h1>
                </div>
            </div>
        </div>
        <div id="profileContent"></div>
    </div>

    <script>
        // ============================================================
        // 1. ПОЛУЧАЕМ USER_ID ИЗ URL
        // ============================================================
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('user_id');
        let currentUser = null;
        let USER_ROLE = 'user';

        if (!userId) {
            document.body.innerHTML = '<div class="access-denied"><div class="icon">🔒</div><h2>Доступ запрещен</h2><p>Ошибка: не передан ID пользователя</p></div>';
        } else {
            // ============================================================
            // 2. ПРОВЕРЯЕМ ПОЛЬЗОВАТЕЛЯ
            // ============================================================
            fetch('/api/auth/check', {
                headers: { 'X-User-Id': userId }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentUser = data.user;
                    USER_ROLE = currentUser.role;
                    document.getElementById('userGreeting').innerHTML = 
                        `${currentUser.full_name} <small style="display:block;font-size:9px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:1px;">${currentUser.role === 'superadmin' ? '🌟 Суперадмин' : currentUser.role === 'admin' ? '👔 Администратор' : '👤 Сотрудник'}</small>`;
                    document.getElementById('profileName').textContent = currentUser.full_name;
                    document.getElementById('profileContent').innerHTML = `
                        <div style="background:var(--bg-secondary);border-radius:var(--radius);padding:16px;">
                            <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;">
                                <div style="font-size:48px;">👤</div>
                                <div>
                                    <div style="font-size:18px;font-weight:700;">${currentUser.full_name}</div>
                                    <div style="font-size:13px;color:var(--text-secondary);">${currentUser.role === 'superadmin' ? '🌟 Суперадмин' : currentUser.role === 'admin' ? '👔 Администратор' : '👤 Сотрудник'}</div>
                                    <div style="font-size:12px;color:var(--text-secondary);">ID: ${currentUser.id}</div>
                                </div>
                            </div>
                            <div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:12px;">
                                <div style="font-size:13px;color:var(--text-secondary);">Дата регистрации: ${currentUser.created_at || '—'}</div>
                            </div>
                        </div>
                    `;
                    loadOrders();
                    loadDashboard();
                } else {
                    document.body.innerHTML = `<div class="access-denied"><div class="icon">🔒</div><h2>Доступ запрещен</h2><p>${data.detail || 'Пользователь не найден'}</p></div>`;
                }
            })
            .catch(() => {
                document.body.innerHTML = '<div class="access-denied"><div class="icon">⚠️</div><h2>Ошибка</h2><p>Не удалось проверить доступ</p></div>';
            });
        }

        // ============================================================
        // 3. НАВИГАЦИЯ
        // ============================================================
        let currentPage = 'orders';
        let previousPage = null;
        let clientData = null;

        function navigateTo(page, data = null) {
            if (page === 'order-detail' && data) {
                showOrderDetail(data);
                return;
            }
            if (page === 'client' && data) {
                showClientPage(data);
                return;
            }

            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            const target = document.getElementById('page-' + page);
            if (target) target.classList.add('active');

            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            const navBtn = document.querySelector(`.nav-btn[data-page="${page}"]`);
            if (navBtn) navBtn.classList.add('active');

            currentPage = page;
            window.scrollTo(0, 0);
        }

        function navigateToOrder(order) {
            previousPage = currentPage;
            navigateTo('order-detail', order);
        }

        function navigateToClient(phone) {
            previousPage = currentPage;
            loadClientData(phone);
        }

        function goBackFromClient() {
            if (previousPage) {
                navigateTo(previousPage);
                previousPage = null;
            } else {
                navigateTo('orders');
            }
        }

        // ============================================================
        // 4. API HELPER
        // ============================================================
        const API_BASE = window.location.origin + '/api';

        async function apiFetch(endpoint, options = {}) {
            const headers = {
                'Content-Type': 'application/json',
                'X-User-Id': userId || 'anonymous',
                ...options.headers
            };
            const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
            return response.json();
        }

        // ============================================================
        // 5. СТАТУСЫ
        // ============================================================
        const statusMap = {
            'Принят в ремонт': 'new',
            'В ремонте': 'repair',
            'Согласование с клиентом': 'consultation',
            'Ожидание запчасти': 'waiting',
            'Гарантия': 'warranty',
            'Готово': 'ready',
            'Выдано (не оплачено)': 'notpaid',
            'Выдано (оплачено)': 'paid'
        };

        const statusColors = {
            'Принят в ремонт': '#4f46e5',
            'В ремонте': '#f59e0b',
            'Согласование с клиентом': '#8b5cf6',
            'Ожидание запчасти': '#f97316',
            'Гарантия': '#14b8a6',
            'Готово': '#22c55e',
            'Выдано (не оплачено)': '#ef4444',
            'Выдано (оплачено)': '#22d3ee'
        };

        function getStatusClass(status) { return statusMap[status] || 'default'; }
        function escapeHtml(text) { if (!text) return '—'; const d = document.createElement('div'); d.textContent = text; return d.innerHTML; }

        // ============================================================
        // 6. КОНТАКТЫ
        // ============================================================
        function openViber(phone) {
            const clean = phone.replace(/[^0-9]/g, '');
            if (!clean) { alert('Номер телефона не указан'); return; }
            window.open('viber://chat?number=' + clean, '_blank');
        }

        function openTelegram(phone) {
            const clean = phone.replace(/[^0-9]/g, '');
            if (!clean) { alert('Номер телефона не указан'); return; }
            window.open('tg://resolve?phone=' + clean, '_blank');
        }

        function copyPhone(phone) {
            if (navigator.clipboard?.writeText) {
                navigator.clipboard.writeText(phone).then(() => alert('📋 Номер скопирован: ' + phone));
            } else { alert('📱 Номер: ' + phone); }
        }

        // ============================================================
        // 7. ДЕТАЛИ ЗАКАЗА
        // ============================================================
        function showOrderDetail(order) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-order-detail').classList.add('active');
            document.getElementById('detailTitle').textContent = 'Заказ #' + order.order_number;

            const phone = order.phone || '';
            let cleanPhone = phone.replace(/[^0-9+]/g, '');
            if (cleanPhone.startsWith('8') && cleanPhone.length === 11) cleanPhone = '+7' + cleanPhone.slice(1);
            if (!cleanPhone.startsWith('+') && cleanPhone.length > 0) cleanPhone = '+' + cleanPhone;

            let contactsHtml = '';
            if (cleanPhone && cleanPhone.length > 4) {
                contactsHtml = `
                    <div style="display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 4px;">
                        <a href="tel:${cleanPhone}" class="contact-btn call">📞</a>
                        <button class="contact-btn viber" onclick="openViber('${cleanPhone}')">💬</button>
                        <button class="contact-btn telegram" onclick="openTelegram('${cleanPhone}')">✈️</button>
                        <button class="contact-btn copy" onclick="copyPhone('${phone}')">📋</button>
                        <button class="client-btn" style="flex:1;min-width:60px;" onclick="navigateToClient('${phone}')">👤 Клиент</button>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary);text-align:center;margin-bottom:6px;">📱 ${phone}</div>
                `;
            }

            const historyHtml = order.history?.length > 0 ?
                `<div style="font-weight:600;font-size:13px;color:var(--accent);margin-top:12px;">📜 История статусов</div>
                <div class="history-timeline">
                    ${order.history.map(h => {
                        const color = statusColors[h.status] || '#6b7280';
                        const time = h.changed_at ? h.changed_at.slice(11, 16) : '';
                        return `
                            <div class="history-item">
                                <span class="h-status">
                                    <span class="status-dot" style="background:${color};"></span>
                                    ${escapeHtml(h.status)}
                                </span>
                                <span class="h-time">${time}</span>
                            </div>
                        `;
                    }).join('')}
                </div>`
                : '<div style="margin-top:12px;color:var(--text-secondary);font-size:12px;">Нет истории статусов</div>';

            document.getElementById('detailContent').innerHTML = `
                ${contactsHtml}
                <div class="detail-row"><span class="label">Статус</span><span class="value"><span class="order-status status-${getStatusClass(order.status)}">${escapeHtml(order.status) || 'Новый'}</span></span></div>
                <div class="detail-row"><span class="label">Дата приема</span><span class="value">${escapeHtml(order.date) || '—'}</span></div>
                <div class="detail-row"><span class="label">Приёмщик</span><span class="value">${escapeHtml(order.receiver) || '—'}</span></div>
                <div class="detail-row"><span class="label">Клиент</span><span class="value">${escapeHtml(order.client_name) || '—'}</span></div>
                <div class="detail-row"><span class="label">Телефон</span><span class="value">${escapeHtml(order.phone) || '—'}</span></div>
                <div class="detail-row"><span class="label">Устройство</span><span class="value">${escapeHtml(order.device) || '—'}</span></div>
                <div class="detail-row" style="border-bottom:none;"><span class="label">Неисправность</span><span class="value">${escapeHtml(order.problem) || '—'}</span></div>
                ${historyHtml}
            `;
        }

        // ============================================================
        // 8. СТРАНИЦА КЛИЕНТА
        // ============================================================
        async function loadClientData(phone) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-client').classList.add('active');
            document.getElementById('clientTitle').textContent = 'Клиент';

            const container = document.getElementById('clientContent');
            container.innerHTML = '<div class="loader"><div class="spinner"></div>Загрузка...</div>';

            try {
                const response = await apiFetch(`/orders?search=${phone}`);
                if (response.success) {
                    const orders = response.data;
                    const total = orders.length;
                    const statusCount = {};
                    const devices = new Set();
                    orders.forEach(o => {
                        const s = o.status || 'Без статуса';
                        statusCount[s] = (statusCount[s] || 0) + 1;
                        if (o.device) devices.add(o.device);
                    });
                    const topStatus = Object.entries(statusCount).sort((a,b) => b[1]-a[1])[0];

                    container.innerHTML = `
                        <div style="background:var(--bg-secondary);border-radius:var(--radius);padding:16px;margin-bottom:12px;">
                            <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px;">
                                <div style="font-size:36px;">👤</div>
                                <div>
                                    <div style="font-size:16px;font-weight:700;">${orders[0]?.client_name || 'Клиент'}</div>
                                    <div style="font-size:13px;color:var(--text-secondary);">📱 ${phone}</div>
                                </div>
                            </div>
                            <div class="client-stats-grid">
                                <div class="client-stat-item"><div class="num">${total}</div><div class="label">Заказов</div></div>
                                <div class="client-stat-item"><div class="num">${topStatus ? topStatus[0] : '—'}</div><div class="label">Частый статус</div></div>
                                <div class="client-stat-item"><div class="num">${devices.size}</div><div class="label">Устройств</div></div>
                            </div>
                        </div>
                        <div style="font-weight:600;font-size:13px;color:var(--accent);margin-bottom:8px;">📋 Все заказы</div>
                        ${orders.length === 0 ? '<div class="empty-state"><div class="icon">📭</div><p>Нет заказов</p></div>' :
                        orders.map(o => `
                            <div class="client-order-item" onclick="navigateToOrder(${JSON.stringify(o).replace(/"/g, '&quot;')})">
                                <div>
                                    <span style="font-weight:600;">#${o.order_number}</span>
                                    <span style="color:var(--text-secondary);font-size:12px;margin-left:8px;">${o.device || '—'}</span>
                                </div>
                                <span class="order-status status-${getStatusClass(o.status)}" style="font-size:10px;">${o.status || 'Новый'}</span>
                            </div>
                        `).join('')}
                    `;
                }
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><p>Ошибка загрузки</p></div>';
            }
        }

        function navigateToClient(phone) {
            previousPage = currentPage;
            loadClientData(phone);
        }

        // ============================================================
        // 9. ЗАГРУЗКА ЗАКАЗОВ
        // ============================================================
        let allOrders = [], currentFilter = 'all', searchQuery = '';

        async function loadOrders() {
            try {
                const response = await apiFetch('/orders?limit=200');
                if (response.success) {
                    allOrders = response.data;
                    updateStats(response.pagination.total);
                    renderOrders();
                } else {
                    showError('Не удалось загрузить заказы: ' + (response.detail || ''));
                }
            } catch (e) {
                showError('Ошибка загрузки заказов');
            }
        }

        function updateStats(total) {
            document.getElementById('totalBadge').textContent = total;
            document.getElementById('statTotal').textContent = total;
            const today = new Date().toISOString().slice(0,10);
            document.getElementById('statToday').textContent = allOrders.filter(o => o.date === today).length;
            document.getElementById('statStatuses').textContent = new Set(allOrders.map(o => o.status).filter(Boolean)).size;
        }

        function renderOrders() {
            let filtered = allOrders;
            if (currentFilter !== 'all') filtered = filtered.filter(o => o.status === currentFilter);
            const q = searchQuery.trim().toLowerCase();
            if (q) {
                filtered = filtered.filter(o =>
                    (o.order_number || '').includes(q) ||
                    (o.phone || '').includes(q) ||
                    (o.client_name || '').toLowerCase().includes(q) ||
                    (o.device || '').toLowerCase().includes(q) ||
                    (o.problem || '').toLowerCase().includes(q)
                );
            }
            const container = document.getElementById('orderList');
            if (filtered.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><h3>Заказов не найдено</h3><p>Попробуйте изменить фильтр или поиск</p></div>';
                return;
            }
            container.innerHTML = filtered.map(order => `
                <div class="order-card" onclick="navigateToOrder(${JSON.stringify(order).replace(/"/g, '&quot;')})">
                    <div class="top-row">
                        <span class="order-number">#${escapeHtml(order.order_number)}</span>
                        <span class="order-status status-${getStatusClass(order.status)}">${escapeHtml(order.status) || 'Новый'}</span>
                    </div>
                    <div class="info">
                        <span>👤 ${escapeHtml(order.client_name) || 'Не указан'}</span>
                        <span>📱 ${escapeHtml(order.phone) || 'Не указан'}</span>
                    </div>
                    <div class="device">🖥️ ${escapeHtml(order.device) || 'Устройство не указано'}</div>
                </div>
            `).join('');
        }

        function showError(msg) {
            document.getElementById('orderList').innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><h3>Ошибка</h3><p>${msg}</p></div>`;
        }

        // ============================================================
        // 10. СОБЫТИЯ
        // ============================================================
        document.getElementById('searchInput')?.addEventListener('input', function() {
            searchQuery = this.value;
            renderOrders();
        });

        document.getElementById('filters')?.addEventListener('click', function(e) {
            const btn = e.target.closest('.filter-btn');
            if (!btn) return;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderOrders();
        });

        // ============================================================
        // 11. ДАШБОРД
        // ============================================================
        async function loadDashboard() {
            if (!['admin', 'superadmin'].includes(USER_ROLE)) {
                document.getElementById('dashboardPanel').innerHTML = '<div class="empty-state"><div class="icon">🔒</div><p>Доступен только администраторам</p></div>';
                return;
            }
            try {
                const response = await apiFetch('/admin/dashboard');
                if (response.success) {
                    const stats = response.data;
                    const maxCount = stats.orders_by_day.length > 0 ? Math.max(...stats.orders_by_day.map(x => x.count)) : 1;
                    document.getElementById('dashboardContent').innerHTML = `
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                            <div style="background:var(--bg-card);padding:12px;border-radius:8px;">
                                <div style="font-size:11px;color:var(--text-secondary);">Среднее время ремонта</div>
                                <div style="font-size:20px;font-weight:700;color:var(--accent);">${stats.avg_repair_time} дн.</div>
                            </div>
                            <div style="background:var(--bg-card);padding:12px;border-radius:8px;">
                                <div style="font-size:11px;color:var(--text-secondary);">Всего заказов</div>
                                <div style="font-size:20px;font-weight:700;color:var(--accent);">${stats.total_orders}</div>
                            </div>
                        </div>
                        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;">Топ-5 неисправностей</div>
                        ${stats.top_problems.map(p => `<div style="display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);"><span>${p.problem || 'Без описания'}</span><span style="color:var(--accent);">${p.count}</span></div>`).join('')}
                        <div style="font-size:12px;color:var(--text-secondary);margin-top:12px;margin-bottom:4px;">Заказы по дням</div>
                        <div style="display:flex;gap:4px;height:36px;align-items:flex-end;">
                            ${stats.orders_by_day.slice(0,7).reverse().map(d => `
                                <div style="flex:1;display:flex;flex-direction:column;align-items:center;">
                                    <div style="background:var(--accent);width:100%;border-radius:4px;min-height:4px;height:${Math.max(4, (d.count / maxCount) * 36)}px;"></div>
                                    <div style="font-size:7px;color:var(--text-secondary);margin-top:2px;">${d.date || '—'}</div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            } catch (e) {
                document.getElementById('dashboardContent').innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><p>Ошибка загрузки</p></div>';
            }
        }
    </script>
</body>
</html>
