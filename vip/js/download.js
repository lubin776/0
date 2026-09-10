/* ============================================================
   download.js —— 下载资源模块（分页2：download-panel）
   config.downloadSources[].url 支持 ry/ 子目录（如 ry/无忧下载.json）
   ============================================================ */
async function renderDownloads(force) {
    const container = document.getElementById('downloads-content');
    if (!container || (container.dataset.rendered && !force)) return;
    container.dataset.rendered = 'true';
    container.innerHTML = '<div class="loading">⏳ 正在加载下载资源...</div>';

    let html = '';
    const sources = (window.CONFIG && window.CONFIG.downloadSources) || [];

    for (const src of sources) {
        try {
            const res = await fetch(src.url + '?t=' + Date.now());
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const raw = await res.text();
            /* 清洗中文标点，避免 JSON 解析失败 */
            const cleaned = raw
                .replace(/[\u201c\u201d]/g, '"')
                .replace(/[\u2018\u2019]/g, "'")
                .replace(/：/g, ':')
                .replace(/，/g, ',');
            const data = JSON.parse(cleaned);

            /* 每个 downloadSource = 一个分组模块 */
            let section = `<div class="source-section">`;
            if (src.name) section += `<div class="source-title">${src.name}</div>`;
            if (src.description) section += `<div class="source-desc">${src.description}</div>`;
            (data.list || data).forEach(group => {
                section += `<div class="group-block">`;
                if (group.name) section += `<div class="group-title">${group.name}</div>`;
                section += `<div class="cards-grid">`;
                (group.list || []).forEach(i => {
                    section += `<a class="download-card" href="${i.url || '#'}" target="_blank" rel="noopener noreferrer" data-name="${(i.name || '').toLowerCase()}">
                        <img class="card-icon" src="${i.icon || ''}" onerror="this.style.visibility='hidden'">
                        <div class="card-info">
                            <div class="card-name">${i.name || ''}</div>
                            ${i.version ? `<div class="card-version">${i.version}</div>` : ''}
                        </div>
                    </a>`;
                });
                section += `</div></div>`;
            });
            html += section + '</div>';
        } catch (e) {
            html += `<div class="error-msg">❌ ${src.name}（${src.url}）加载失败：${e.message}</div>`;
        }
    }

    container.innerHTML = html;
    bindCopy(container);
}
