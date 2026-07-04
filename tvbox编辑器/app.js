/**
 * TVBox 接口配置编辑器 - 核心 JavaScript
 * 功能：可视编辑 / 源码编辑 / 导入导出 / 本地存储
 */
(function () {
    'use strict';

    // ==================== State ====================
    const state = {
        sites: [],
        parses: [],
        lives: [],
        theme: localStorage.getItem('tvbox-theme') || 'dark',
    };

    // ==================== DOM Refs ====================
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ==================== Init ====================
    function init() {
        applyTheme();
        loadFromStorage();
        bindEvents();
        renderAll();
        updateSourceEditor();
    }

    // ==================== Theme ====================
    function applyTheme() {
        document.documentElement.setAttribute('data-theme', state.theme);
        const icon = $('#themeIcon');
        if (icon) icon.textContent = state.theme === 'dark' ? '🌙' : '☀️';
    }

    function toggleTheme() {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('tvbox-theme', state.theme);
        applyTheme();
    }

    // ==================== Persistence ====================
    function saveToStorage() {
        const data = { sites: state.sites, parses: state.parses, lives: state.lives };
        localStorage.setItem('tvbox-config', JSON.stringify(data));
    }

    function loadFromStorage() {
        try {
            const raw = localStorage.getItem('tvbox-config');
            if (raw) {
                const data = JSON.parse(raw);
                state.sites = data.sites || [];
                state.parses = data.parses || [];
                state.lives = data.lives || [];
            }
        } catch (e) {
            console.warn('Failed to load from storage:', e);
        }
    }

    // ==================== Render ====================
    function renderAll() {
        renderList('sites');
        renderList('parses');
        renderList('lives');
        updateEmptyStates();
    }

    function renderList(type) {
        const container = $(`#${type}List`);
        const items = state[type];
        container.innerHTML = items.map((item, idx) => renderItem(type, item, idx)).join('');
    }

    function renderItem(type, item, idx) {
        const fields = getFieldsForType(type);
        const title = item.name || item.key || `#${idx + 1}`;
        const fieldsHtml = fields
            .filter(f => item[f.key] !== undefined)
            .map(f => `
                <div class="field-group">
                    <span class="field-label">${f.label}</span>
                    <input class="field-input" data-type="${type}" data-idx="${idx}" data-field="${f.key}"
                           value="${escapeHtml(String(item[f.key] || ''))}" placeholder="${f.placeholder || ''}">
                </div>
            `).join('');

        return `
            <div class="config-item" data-type="${type}" data-idx="${idx}">
                <div class="config-item-header">
                    <span class="config-item-title">${escapeHtml(title)}</span>
                    <div class="config-item-actions">
                        <button class="btn-edit" onclick="app.moveItem('${type}',${idx},-1)" title="上移">↑</button>
                        <button class="btn-edit" onclick="app.moveItem('${type}',${idx},1)" title="下移">↓</button>
                        <button class="btn-delete" onclick="app.removeItem('${type}',${idx})" title="删除">✕</button>
                    </div>
                </div>
                <div class="config-item-fields">${fieldsHtml}</div>
            </div>
        `;
    }

    function getFieldsForType(type) {
        switch (type) {
            case 'sites':
                return [
                    { key: 'key', label: '标识 Key', placeholder: '如: xiaoyu' },
                    { key: 'name', label: '名称 Name', placeholder: '如: 小鱼' },
                    { key: 'type', label: '类型 Type', placeholder: '如: xiaoyu' },
                    { key: 'api', label: 'API 地址', placeholder: 'https://...' },
                    { key: 'download', label: '下载地址', placeholder: 'https://...' },
                    { key: 'ext', label: '扩展 Ext', placeholder: '扩展参数' },
                ];
            case 'parses':
                return [
                    { key: 'name', label: '名称 Name', placeholder: '如: 解析1' },
                    { key: 'type', label: '类型', placeholder: '1' },
                    { key: 'url', label: '解析地址', placeholder: 'https://...' },
                    { key: 'ext', label: '扩展', placeholder: '' },
                ];
            case 'lives':
                return [
                    { key: 'name', label: '名称', placeholder: '如: 直播源1' },
                    { key: 'type', label: '类型', placeholder: 'proxy' },
                    { key: 'url', label: '直播地址', placeholder: 'https://...' },
                    { key: 'ext', label: '扩展', placeholder: '' },
                ];
            default:
                return [];
        }
    }

    function updateEmptyStates() {
        ['sites', 'parses', 'lives'].forEach(type => {
            const empty = $(`#${type}Empty`);
            const list = $(`#${type}List`);
            if (empty && list) {
                empty.style.display = state[type].length === 0 ? 'block' : 'none';
                list.style.display = state[type].length === 0 ? 'none' : 'block';
            }
        });
    }

    // ==================== Item Operations ====================
    function addItem(type) {
        const template = getEmptyTemplate(type);
        state[type].push(template);
        renderAll();
        saveToStorage();
        showToast('success', `已添加 ${type} 项`);
    }

    function removeItem(type, idx) {
        if (!confirm(`确定删除该 ${type} 项吗？`)) return;
        state[type].splice(idx, 1);
        renderAll();
        saveToStorage();
        showToast('info', `已删除 ${type} 项`);
    }

    function moveItem(type, idx, direction) {
        const arr = state[type];
        const newIdx = idx + direction;
        if (newIdx < 0 || newIdx >= arr.length) return;
        [arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]];
        renderAll();
        saveToStorage();
    }

    function getEmptyTemplate(type) {
        switch (type) {
            case 'sites': return { key: '', name: '', type: '', api: '', download: '', ext: '' };
            case 'parses': return { name: '', type: '', url: '', ext: '' };
            case 'lives': return { name: '', type: '', url: '', ext: '' };
        }
    }

    // ==================== Field Change ====================
    function onFieldChange(e) {
        const input = e.target;
        if (!input.matches('.field-input')) return;
        const { type, idx, field } = input.dataset;
        const value = input.value;
        state[type][parseInt(idx)][field] = value;
        saveToStorage();
        // Update title if name/key changed
        const itemEl = input.closest('.config-item');
        if (itemEl) {
            const titleEl = itemEl.querySelector('.config-item-title');
            if (titleEl) {
                const item = state[type][parseInt(idx)];
                titleEl.textContent = item.name || item.key || `#${parseInt(idx) + 1}`;
            }
        }
    }

    // ==================== Source Editor ====================
    function updateSourceEditor() {
        const editor = $('#sourceEditor');
        if (!editor) return;
        const data = { sites: state.sites, parses: state.parses, lives: state.lives };
        editor.value = JSON.stringify(data, null, 2);
        updateLineNumbers();
        updateStatusBar();
    }

    function syncFromSource() {
        const editor = $('#sourceEditor');
        if (!editor) return;
        try {
            const data = JSON.parse(editor.value);
            state.sites = data.sites || [];
            state.parses = data.parses || [];
            state.lives = data.lives || [];
            renderAll();
            saveToStorage();
            setJsonStatus(true);
            showToast('success', '从源码同步成功');
        } catch (e) {
            setJsonStatus(false, e.message);
            showToast('error', 'JSON 解析失败: ' + e.message);
        }
    }

    function formatSource() {
        const editor = $('#sourceEditor');
        try {
            const obj = JSON.parse(editor.value);
            editor.value = JSON.stringify(obj, null, 2);
            updateLineNumbers();
            setJsonStatus(true);
            showToast('success', '格式化完成');
        } catch (e) {
            setJsonStatus(false, e.message);
            showToast('error', '无法格式化：JSON 无效');
        }
    }

    function minifySource() {
        const editor = $('#sourceEditor');
        try {
            const obj = JSON.parse(editor.value);
            editor.value = JSON.stringify(obj);
            updateLineNumbers();
            setJsonStatus(true);
            showToast('success', '压缩完成');
        } catch (e) {
            setJsonStatus(false, e.message);
        }
    }

    function validateSource() {
        const editor = $('#sourceEditor');
        try {
            JSON.parse(editor.value);
            setJsonStatus(true);
            showToast('success', 'JSON 格式正确 ✓');
        } catch (e) {
            setJsonStatus(false, e.message);
            showToast('error', 'JSON 格式错误: ' + e.message);
        }
    }

    function setJsonStatus(valid, msg) {
        const el = $('#jsonStatus');
        if (valid) {
            el.textContent = '✅ 有效 JSON';
            el.style.color = 'var(--accent-green)';
        } else {
            el.textContent = '❌ ' + (msg || '无效 JSON');
            el.style.color = 'var(--accent-red)';
        }
    }

    function updateLineNumbers() {
        const editor = $('#sourceEditor');
        const lineNum = $('#lineNumbers');
        if (!editor || !lineNum) return;
        const lines = editor.value.split('\n').length;
        lineNum.innerHTML = Array.from({ length: lines }, (_, i) => i + 1).join('<br>');
    }

    function updateStatusBar() {
        const editor = $('#sourceEditor');
        if (!editor) return;
        const charCount = $('#charCount');
        if (charCount) charCount.textContent = `字符: ${editor.value.length}`;
    }

    // ==================== Tabs ====================
    function switchTab(tabName) {
        $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
        $$('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'panel' + tabName.charAt(0).toUpperCase() + tabName.slice(1)));
        if (tabName === 'source') {
            updateSourceEditor();
        }
    }

    // ==================== Dropdown ====================
    function toggleDropdown() {
        const menu = $('#moreMenu');
        if (menu) menu.classList.toggle('show');
    }

    function closeDropdown(e) {
        if (!e.target.closest('#dropdownMore')) {
            const menu = $('#moreMenu');
            if (menu) menu.classList.remove('show');
        }
    }

    // ==================== Modal ====================
    function showModal(title, bodyHtml, footerHtml) {
        const overlay = $('#modalOverlay');
        const titleEl = $('#modalTitle');
        const bodyEl = $('#modalBody');
        const footerEl = $('#modalFooter');
        titleEl.textContent = title;
        bodyEl.innerHTML = bodyHtml;
        footerEl.innerHTML = footerHtml || '';
        overlay.classList.add('show');
    }

    function closeModal() {
        $('#modalOverlay').classList.remove('show');
    }

    // ==================== Toast ====================
    function showToast(type, message) {
        const container = $('#toastContainer');
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span>${icons[type] || '📢'}</span><span>${escapeHtml(message)}</span>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // ==================== Export / Import ====================
    function downloadJson() {
        const data = { sites: state.sites, parses: state.parses, lives: state.lives };
        const json = JSON.stringify(data, null, 2);
        downloadFile(json, 'tvbox-config.json', 'application/json');
        showToast('success', 'JSON 文件已下载');
    }

    function downloadFile(content, filename, mime) {
        const blob = new Blob([content], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function copyConfig() {
        const data = { sites: state.sites, parses: state.parses, lives: state.lives };
        navigator.clipboard.writeText(JSON.stringify(data, null, 2))
            .then(() => showToast('success', '已复制到剪贴板'))
            .catch(() => {
                // Fallback
                const ta = document.createElement('textarea');
                ta.value = JSON.stringify(data, null, 2);
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('success', '已复制到剪贴板');
            });
    }

    function clearConfig() {
        if (!confirm('确定清空所有配置吗？此操作不可撤销。')) return;
        state.sites = [];
        state.parses = [];
        state.lives = [];
        renderAll();
        updateSourceEditor();
        saveToStorage();
        showToast('warning', '已清空所有配置');
    }

    function uploadFile() {
        const input = $('#fileInput');
        input.onchange = function () {
            const file = input.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function (e) {
                try {
                    const data = JSON.parse(e.target.result);
                    state.sites = data.sites || [];
                    state.parses = data.parses || [];
                    state.lives = data.lives || [];
                    renderAll();
                    updateSourceEditor();
                    saveToStorage();
                    showToast('success', `已导入 ${file.name}`);
                } catch (err) {
                    showToast('error', '文件解析失败，请检查格式');
                }
            };
            reader.readAsText(file);
            input.value = '';
        };
        input.click();
    }

    // ==================== Event Bindings ====================
    function bindEvents() {
        // Theme
        $('#btnTheme').addEventListener('click', toggleTheme);

        // Tabs
        $$('.tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });

        // Add buttons
        $('#addSite').addEventListener('click', () => addItem('sites'));
        $('#addParse').addEventListener('click', () => addItem('parses'));
        $('#addLive').addEventListener('click', () => addItem('lives'));

        // Field changes (delegated)
        $('#panelEditor').addEventListener('input', onFieldChange);

        // Source editor
        const sourceEditor = $('#sourceEditor');
        sourceEditor.addEventListener('input', () => {
            updateLineNumbers();
            updateStatusBar();
        });
        sourceEditor.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = e.target.selectionStart;
                const end = e.target.selectionEnd;
                e.target.value = e.target.value.substring(0, start) + '  ' + e.target.value.substring(end);
                e.target.selectionStart = e.target.selectionEnd = start + 2;
                updateLineNumbers();
            }
        });

        // Source toolbar
        $('#btnFormat').addEventListener('click', formatSource);
        $('#btnMinify').addEventListener('click', minifySource);
        $('#btnValidate').addEventListener('click', validateSource);

        // Toolbar buttons
        $('#btnCopy').addEventListener('click', copyConfig);
        $('#btnClear').addEventListener('click', clearConfig);
        $('#btnSave').addEventListener('click', () => {
            syncFromSource();
            showToast('success', '配置已保存');
        });
        $('#btnDownloadJson').addEventListener('click', downloadJson);
        $('#btnUploadEncrypt').addEventListener('click', uploadFile);

        // More dropdown
        $('#btnMore').addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown();
        });
        document.addEventListener('click', closeDropdown);

        // Modal
        $('#modalClose').addEventListener('click', closeModal);
        $('#modalOverlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) closeModal();
        });

        // Other toolbar buttons (placeholder actions)
        const placeholderActions = {
            'btnLoadMulti': '加载多仓功能',
            'btnMakeMulti': '制作多仓功能',
            'btnSearch': '搜索接口功能',
            'btnHistory': '历史记录功能',
            'btnToImage': '配置转图片功能',
            'btnImgToCode': '图片转代码功能',
            'btnDownloadJar': '下载 JAR 功能',
            'btnLocalPack': '本地包检测功能',
            'btnSpeedTest': '接口测速功能',
            'btnUpload1': '上传配置1',
            'btnUpload2': '上传配置2',
            'btnUpload3': '上传配置3',
            'btnToCode': '配置转码功能',
            'btnBoxSource': '壳子源码功能',
            'btnAppStore': '应用商店功能',
        };

        Object.entries(placeholderActions).forEach(([id, name]) => {
            const el = $(`#${id}`);
            if (el) {
                el.addEventListener('click', (e) => {
                    e.preventDefault();
                    showToast('info', `${name} 待实现`);
                });
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 's') {
                    e.preventDefault();
                    syncFromSource();
                    showToast('success', '已保存 (Ctrl+S)');
                }
            }
            if (e.key === 'Escape') closeModal();
        });
    }

    // ==================== Utilities ====================
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ==================== Expose API ====================
    window.app = {
        addItem,
        removeItem,
        moveItem,
        showToast,
        showModal,
        closeModal,
        switchTab,
    };

    // ==================== Boot ====================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
