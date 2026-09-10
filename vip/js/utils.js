/* ============================================================
   utils.js —— 工具模块
   - 全局 CONFIG 引用
   - ensureJson：文件名无 .json 后缀时自动补全
   - bindCopy：统一复制按钮逻辑
   ============================================================ */
window.CONFIG = null;

/* 文件名没有 .json 后缀时自动补上（保证备份线路 URL 正确） */
function ensureJson(name) {
    return name.endsWith('.json') ? name : name + '.json';
}

/* 为容器内所有 .copy-btn 绑定复制事件 */
function bindCopy(container) {
    if (!container) return;
    container.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const url = this.getAttribute('data-url');
            if (!url) return;
            const done = () => {
                const orig = this.textContent;
                this.textContent = '✅ 已复制';
                this.classList.add('copied');
                setTimeout(() => { this.textContent = orig; this.classList.remove('copied'); }, 1500);
            };
            if (navigator.clipboard) navigator.clipboard.writeText(url).then(done).catch(fallback);
            else fallback();
            function fallback() {
                const input = document.createElement('input');
                input.value = url; document.body.appendChild(input);
                input.select(); document.execCommand('copy'); document.body.removeChild(input); done();
            }
        });
    });
}
