/* ============================================================
   app.js —— 入口/组合模块
   - 加载 config.json
   - 应用头部（标题行 + 小字两行）+ footer（均 config 驱动）
   - 导航栏组合（全能版）
   - 分页控制（每页一个模块）
   - 搜索（全局）
   - 简洁版 / 全能版 模式切换 + 搜索框位置切换
   ============================================================ */
const MODE_KEY = 'site_mode';
const btn = document.getElementById('modeToggleBtn');
const searchBox = document.getElementById('search');
const mainCard = document.querySelector('.main-card');
const navTabs = document.getElementById('navTabs');

let currentMode = localStorage.getItem(MODE_KEY) || 'simple';
document.body.className = currentMode + '-mode';
updateBtnText();
positionSearchBox();

/* ===== 加载 config.json ===== */
async function loadConfig() {
    try {
        const res = await fetch('config.json?t=' + Date.now(), { cache: 'no-store' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        window.CONFIG = await res.json();
    } catch (e) {
        console.error('config.json 加载失败', e);
        window.CONFIG = { tabs: [], api: {}, downloadSources: [], about: {} };
    }
    applyConfig();        // 头部 + footer
    renderTabs();         // 导航栏组合
    renderApi();          // 分页1（始终渲染）
    if (currentMode !== 'simple') {
        renderDownloads(true);  // 分页2（全能版才渲染）
        renderAbout();          // 分页3
    }
}

/* ===== 头部模块：标题行（logo + 大字）+ 小字两行 ===== */
function applyConfig() {
    const s = (window.CONFIG && window.CONFIG.site) || {};
    document.title = s.title || '加载中...';
    const titleEl = document.getElementById('siteTitle');
    if (titleEl) {
        titleEl.innerHTML = `<img class="header-logo" src="${s.logo || ''}" alt="Logo"><span>${s.title || ''}</span>`;
    }
    const subEl = document.getElementById('siteSubtitle');
    if (subEl) {
        /* 小字两行：第一行副标题，第二行 QQ群 */
        subEl.innerHTML = `${s.subtitle || ''}<br>QQ交流群：${s.qqGroup || ''}`;
    }
    /* Footer 模块 */
    const footer = document.getElementById('footerText');
    if (footer) {
        const footerText = window.CONFIG.footer || '';
        const qq = s.qqGroup || '';
        footer.innerHTML = `<p>${footerText}${qq ? ' QQ 群：' + qq : ''}</p>`;
    }
}

/* ===== 导航栏组合模块（全能版）===== */
function renderTabs() {
    const tabs = (window.CONFIG && window.CONFIG.tabs) || [];
    const nav = document.getElementById('navTabs');
    nav.innerHTML = tabs.map(t =>
        `<button class="nav-tab ${t.id === 'api' ? 'active' : ''}" data-tab="${t.id}">${t.label}</button>`
    ).join('');
    nav.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            nav.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            showPanel(this.getAttribute('data-tab'));
        });
    });
}

/* ===== 分页控制：每页一个模块 ===== */
function showPanel(tabId) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(tabId + '-panel');
    if (panel) panel.classList.add('active');

    /* 切换分页时按需渲染（下载/关于 懒加载） */
    if (tabId === 'download') renderDownloads();
    if (tabId === 'about') renderAbout();

    /* 部分分页隐藏搜索框 */
    const tabsConfig = (window.CONFIG && window.CONFIG.tabs) || [];
    const targetTab = tabsConfig.find(t => t.id === tabId);
    if (searchBox) {
        searchBox.style.display = (targetTab && targetTab.hideSearch) ? 'none' : '';
    }
}

/* ===== 全局搜索 ===== */
function globalSearch() {
    const kw = (searchBox.value || '').toLowerCase().trim();
    document.querySelectorAll('#api-panel .entry').forEach(e => {
        const name = e.getAttribute('data-name') || '';
        e.classList.toggle('hidden', !name.includes(kw));
    });
    if (currentMode !== 'simple') {
        document.querySelectorAll('.download-card').forEach(c => {
            const name = c.getAttribute('data-name') || '';
            c.classList.toggle('hidden', !name.includes(kw));
        });
    }
}

/* ===== 搜索框位置切换（简洁版在卡片外 / 全能版在卡片内）===== */
function positionSearchBox() {
    if (currentMode === 'simple') {
        if (searchBox.parentNode !== mainCard.parentNode) {
            mainCard.parentNode.insertBefore(searchBox, mainCard);
        }
    } else {
        if (searchBox.parentNode !== mainCard) {
            navTabs.insertAdjacentElement('afterend', searchBox);
        }
    }
}

/* ===== 切换按钮文字 ===== */
function updateBtnText() {
    btn.innerHTML = currentMode === 'simple' ? '切换<br>全能版' : '切换<br>简洁版';
}

/* ===== 模式切换（简洁版 ⇄ 全能版）===== */
btn.addEventListener('click', () => {
    currentMode = (currentMode === 'simple') ? 'full' : 'simple';
    localStorage.setItem(MODE_KEY, currentMode);
    document.body.className = currentMode + '-mode';
    updateBtnText();
    positionSearchBox();

    if (currentMode !== 'simple') {
        renderDownloads();   // 进入全能版时渲染下载页
        renderAbout();        // 进入全能版时渲染关于页
    } else {
        showPanel('api');     // 回到简洁版默认显示接口页
    }
});

/* ===== 启动 ===== */
loadConfig().then(() => { positionSearchBox(); });
