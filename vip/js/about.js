/* ============================================================
   about.js —— 关于页面模块（分页3：about-panel）
   域名 / 声明 / QQ群 文字内容全部来自 CONFIG.about
   ============================================================ */
function renderAbout() {
    const a = (window.CONFIG && window.CONFIG.about) || {};

    /* 模块1：备份线路域名 */
    const domEl = document.getElementById('aboutDomains');
    let domHtml = `<h3>${a.domainTitle || '🌐 备份线路域名'}</h3>`;
    if (a.domainTip) domHtml += `<p style="margin-bottom:6px;">${a.domainTip}</p>`;
    (a.domains || []).forEach(d => {
        domHtml += `<div class="domain-line"><span>${d}</span><button class="copy-btn" data-url="${d}">复制</button></div>`;
    });
    domEl.innerHTML = domHtml;
    bindCopy(domEl);

    /* 模块2：声明与联系 */
    const declEl = document.getElementById('aboutDecl');
    let declHtml = `<h3>${a.declarationLabel || '📢 声明与联系'}</h3>`;
    if (a.declaration) declHtml += `<ul><li>${a.declaration}</li></ul>`;
    const qq = a.qqGroup || (window.CONFIG && window.CONFIG.site && window.CONFIG.site.qqGroup) || '';
    if (qq) declHtml += `<p style="margin-top:10px;">${a.qqGroupLabel || 'QQ 交流群'}：<strong style="color:#4a9eff;">${qq}</strong></p>`;
    declEl.innerHTML = declHtml;
}
