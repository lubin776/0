/* ============================================================
   api.js —— 接口列表模块（分页1：api-panel）
   还原原始渲染：备份时间/新(绿)旧(橙)颜色/权重排序/自动补 .json
   所有可变内容来自 CONFIG.api（domains / weights）
   ============================================================ */
function renderApi() {
    const container = document.getElementById('listContainer');
    const WEIGHTS = (window.CONFIG && window.CONFIG.api && window.CONFIG.api.weights) || {};
    const DOMAINS = (window.CONFIG && window.CONFIG.api && window.CONFIG.api.domains) || [];

    /* 日期格式：20260910 → 2026年09月10日 */
    function formatDateToChinese(d) {
        if (!d || d.length !== 8) return '----';
        return `${d.slice(0,4)}年${d.slice(4,6)}月${d.slice(6,8)}日`;
    }
    /* 是否在最近 2 天内（用于新旧颜色判断） */
    function isRecent(d) {
        if (!d || d.length !== 8) return false;
        const y = parseInt(d.slice(0,4),10), m = parseInt(d.slice(4,6),10)-1, day = parseInt(d.slice(6,8),10);
        return (Date.now() - new Date(y, m, day).getTime()) / 86400000 <= 2;
    }

    fetch('list.txt?t=' + Date.now(), { cache: 'no-store' })
        .then(res => res.ok ? res.text() : Promise.reject('HTTP ' + res.status))
        .then(text => {
            const loadingTip = document.getElementById('apiLoading');
            if (loadingTip) loadingTip.style.display = 'none';

            const lines = text.trim().split('\n').filter(l => l.trim());
            let items = lines.map(line => {
                const parts = line.split('|').map(s => s.trim());
                const file = parts[0];
                return {
                    file: file,
                    name: file.replace(/\.json$/i, ''),
                    date: parts[1] || '',
                    size: parts[2] || '',
                    origUrl: parts[3] || '',
                    weight: WEIGHTS.hasOwnProperty(file) ? WEIGHTS[file] : 999
                };
            });
            /* 排序：有权重的按权重升序排前面，其余按名字典序稳定排列 */
            items.sort((a, b) => {
                if (a.weight !== b.weight) return a.weight - b.weight;
                return a.name.localeCompare(b.name, 'zh');
            });

            let html = '';
            items.forEach(it => {
                const isNew = isRecent(it.date);
                const cls = isNew ? 'badge-new' : 'badge-old';
                const jsonName = ensureJson(it.file);  // 关键：无后缀自动补 .json
                let linesHtml = '';
                if (it.origUrl) {
                    linesHtml += `<div class="url-line"><span class="url-tag">原始线路</span><span class="url-text">${it.origUrl}</span><button class="copy-btn" data-url="${it.origUrl}">复制</button></div>`;
                }
                DOMAINS.forEach(d => {
                    const url = d.base + jsonName;
                    linesHtml += `<div class="url-line"><span class="url-tag">${d.tag}</span><span class="url-text">${url}</span><button class="copy-btn" data-url="${url}">复制</button></div>`;
                });
                html += `<div class="entry" data-name="${it.name.toLowerCase()}">
                    <div class="entry-header">
                        <div class="entry-name" title="${it.name}">${it.name}</div>
                        <div class="entry-meta-inline">
                            <span class="${cls}">备份时间 ${formatDateToChinese(it.date)}</span>
                            ${it.size ? '&nbsp;&nbsp;' + it.size : ''}
                        </div>
                    </div>
                    <div class="entry-urls">${linesHtml}</div>
                </div>`;
            });
            container.innerHTML = html;
            bindCopy(container);
        })
        .catch(err => {
            const loadingTip = document.getElementById('apiLoading');
            if (loadingTip) loadingTip.style.display = 'none';
            container.innerHTML = `<div class="error-msg">❌ 接口加载失败：${err}</div>`;
        });
}
