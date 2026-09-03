/**
 * title: "喵物次元",
 * logo: "https://www.mwcy.net/favicon.ico",
 * more: {
 *   sourceTag: "动漫"
 * }
 */
import { Crypto, load, _ } from 'assets://js/lib/cat.js';

const HOST = 'https://www.mwcy.net';
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

let siteKey = "", siteType = "", sourceKey = "", ext = "";

function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    sourceKey = cfg.sourceKey;
    ext = cfg.ext;
    // 如果ext传入则覆盖HOST（保持兼容）
    if (ext && ext.indexOf('http') == 0) HOST = ext;
}

// ==================== 辅助函数 ====================
function fixUrl(url) {
    if (!url) return '';
    url = url.trim();
    if (url.startsWith('//')) return 'https:' + url;
    if (url.startsWith('/')) return HOST + url;
    return url;
}

function cleanText(text) {
    if (!text) return '';
    return text.replace(/\s+/g, ' ').trim();
}

function isVideoFormat(url) {
    if (!url) return false;
    return /\.(m3u8|mp4|mkv|flv|avi|mov|wmv|webm)(\?.*)?$/i.test(url);
}

// ==================== 1. 首页内容与筛选配置 ====================
function home(filter) {
    // 固定分类（6个）
    const classes = [
        { type_id: "1", type_name: "番剧" },
        { type_id: "22", type_name: "连载新番" },
        { type_id: "24", type_name: "国漫" },
        { type_id: "2", type_name: "剧场" },
        { type_id: "25", type_name: "欧美动漫" },
        { type_id: "26", type_name: "4K专区" }
    ];

    // ---- 公共筛选选项 ----
    // 年份：当前年份往前30年 + 更早
    const yearList = (() => {
        const years = [{ n: "全部", v: "" }];
        const currentYear = new Date().getFullYear();
        for (let y = currentYear; y >= currentYear - 30; y--) {
            years.push({ n: String(y), v: String(y) });
        }
        years.push({ n: "更早", v: "更早" });
        return years;
    })();

    // 字母
    const letterList = (() => {
        const letters = [{ n: "全部", v: "" }];
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
        chars.forEach(c => letters.push({ n: c, v: c }));
        letters.push({ n: "0-9", v: "0-9" });
        return letters;
    })();

    // 排序
    const orderList = [
        { n: "最新", v: "time" },
        { n: "最热", v: "hits" },
        { n: "评分", v: "score" }
    ];

    // 地区（用于剧场、欧美动漫）
    const areaList = [
        { n: "全部", v: "" },
        { n: "大陆", v: "大陆" },
        { n: "香港", v: "香港" },
        { n: "台湾", v: "台湾" },
        { n: "美国", v: "美国" },
        { n: "法国", v: "法国" },
        { n: "英国", v: "英国" },
        { n: "日本", v: "日本" },
        { n: "韩国", v: "韩国" },
        { n: "德国", v: "德国" },
        { n: "泰国", v: "泰国" },
        { n: "印度", v: "印度" },
        { n: "意大利", v: "意大利" },
        { n: "西班牙", v: "西班牙" },
        { n: "加拿大", v: "加拿大" },
        { n: "其他", v: "其他" }
    ];

    // ---- 按分类配置筛选器 ----
    const filters = {
        "1": [  // 番剧
            { key: "year", name: "年份", value: yearList },
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ],
        "22": [ // 连载新番
            { key: "year", name: "年份", value: yearList },
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ],
        "24": [ // 国漫
            { key: "year", name: "年份", value: yearList },
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ],
        "2": [  // 剧场
            { key: "area", name: "地区", value: areaList },
            { key: "year", name: "年份", value: yearList },
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ],
        "25": [ // 欧美动漫
            { key: "area", name: "地区", value: areaList },
            { key: "year", name: "年份", value: yearList },
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ],
        "26": [ // 4K专区
            { key: "letter", name: "字母", value: letterList },
            { key: "order", name: "排序", value: orderList }
        ]
    };

    return JSON.stringify({ class: classes, filters: filters });
}

// ==================== 2. 首页推荐视频 ====================
async function homeVod() {
    try {
        const res = await req(HOST, { headers: { 'User-Agent': UA } });
        const $ = load(res.content);

        // 定位“十月新番”区域
        let section = null;
        $('.box-width.wow.fadeInUp .title .title-h').each((i, el) => {
            if ($(el).text().trim() === '十月新番') {
                section = $(el).closest('.box-width').find('.public-r');
                return false;
            }
        });
        if (!section) {
            section = $('.public-list-box.public-pic-b').parent();
        }

        const items = section ? section.find('.public-list-box.public-pic-b') : $('.public-list-box.public-pic-b');
        const videos = [];
        const seen = new Set();

        items.each((i, el) => {
            const $el = $(el);
            const $link = $el.find('a.public-list-exp');
            const href = $link.attr('href');
            if (!href || !href.startsWith('/bangumi/')) return;
            const title = $el.find('.time-title').text().trim() || $link.attr('title') || '';
            const pic = $link.find('img').attr('data-src') || $link.find('img').attr('src') || '';
            const remarks = $el.find('.public-list-prb').text().trim() || '';
            if (title && href) {
                const vod_id = href.startsWith('http') ? href : HOST + href;
                if (!seen.has(vod_id)) {
                    seen.add(vod_id);
                    videos.push({ vod_id, vod_name: title, vod_pic: pic, vod_remarks: remarks });
                }
            }
        });

        return JSON.stringify({ list: videos });
    } catch (e) {
        console.log('homeVod error:', e);
        return null;
    }
}

// ==================== 3. 分类内容爬取 ====================
async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    extend = extend || {};
    const area = extend.area || '';
    const year = extend.year || '';
    const letter = extend.letter || '';
    const order = extend.order || '';

    // 构建URL
    let url = `${HOST}/show/${tid}`;
    const parts = [];
    if (area) parts.push(`area/${encodeURIComponent(area)}`);
    if (order) parts.push(`by/${encodeURIComponent(order)}`);
    if (letter) parts.push(`letter/${encodeURIComponent(letter)}`);
    if (year) parts.push(`year/${encodeURIComponent(year)}`);
    if (pg > 1) parts.push(`page/${pg}`);

    if (parts.length > 0) {
        url += '/' + parts.join('/') + '.html';
    } else {
        url += (pg === 1 ? '.html' : `/page/${pg}.html`);
    }


    try {
        const res = await req(url, { headers: { 'User-Agent': UA } });
        const $ = load(res.content);

        // 解析视频列表（多级兜底）
        let items = $('.public-list-box.public-pic-b');
        if (!items.length) items = $('.public-list-div').parent();

        const videos = [];
        const seen = new Set();

        items.each((i, el) => {
            const $el = $(el);
            const $link = $el.find('a.public-list-exp');
            const href = $link.attr('href');
            if (!href) return;

            let vod_id = href;
            if (!href.startsWith('http')) vod_id = HOST + href;
            // 如果是 /play/ 链接，转换为 /bangumi/
            if (href.startsWith('/play/')) {
                const match = href.match(/^\/play\/([^-]+)/);
                if (match) {
                    vod_id = HOST + `/bangumi/${match[1]}.html`;
                } else {
                    return;
                }
            } else if (!href.startsWith('/bangumi/')) {
                return;
            }

            const title = $el.find('.time-title').text().trim() || $link.attr('title') || '';
            const pic = $link.find('img').attr('data-src') || $link.find('img').attr('src') || '';
            const remarks = $el.find('.public-list-prb').text().trim() || '';
            if (title && vod_id && !seen.has(vod_id)) {
                seen.add(vod_id);
                videos.push({
                    vod_id,
                    vod_name: title,
                    vod_pic: fixUrl(pic),
                    vod_remarks: remarks
                });
            }
        });

        // 提取总页数
        let pagecount = 1;
        const pageTip = $('.page-tip').text().trim();
        if (pageTip) {
            const match = pageTip.match(/当前\d+\/(\d+)页/);
            if (match) pagecount = parseInt(match[2]) || 1;
        }
        if (pagecount === 1) {
            const lastPage = $('.page-link').last().attr('href');
            if (lastPage) {
                const m = lastPage.match(/page\/(\d+)\.html/);
                if (m) pagecount = parseInt(m[1]) || 1;
            }
        }

        return JSON.stringify({
            list: videos,
            page: pg,
            pagecount: pagecount,
            limit: 20,
            total: videos.length
        });
    } catch (e) {
        console.log('category error:', e);
        return JSON.stringify({ list: [] });
    }
}

// ==================== 4. 搜索功能 ====================
async function search(wd) {
    try {
        const encoded = encodeURIComponent(wd);
        const url = `${HOST}/search/wd/${encoded}.html`;

        const res = await req(url, { headers: { 'User-Agent': UA } });
        const $ = load(res.content);

        // 搜索页结果使用 .vod-detail.search-list
        let items = $('.vod-detail.search-list');
        if (!items.length) items = $('.vod-detail');

        const videos = [];
        const seen = new Set();

        items.each((i, el) => {
            const $el = $(el);
            // 标题和链接
            let title = '';
            let vod_id = '';
            const titleEl = $el.find('h3.slide-info-title');
            if (titleEl.length) title = titleEl.text().trim();

            const linkEl = $el.find('a[target="_blank"]');
            if (linkEl.length) {
                const href = linkEl.attr('href');
                if (href) {
                    if (href.startsWith('/bangumi/')) {
                        vod_id = HOST + href;
                    } else if (href.startsWith('/play/')) {
                        const match = href.match(/^\/play\/([^-]+)/);
                        if (match) vod_id = HOST + `/bangumi/${match[1]}.html`;
                    }
                }
                if (!title) title = linkEl.text().trim();
            }
            if (!title) {
                // 从其他位置找
                const altTitle = $el.find('.slide-info-title').text().trim();
                if (altTitle) title = altTitle;
            }

            const pic = $el.find('.detail-pic img').attr('data-src') || $el.find('.detail-pic img').attr('src') || '';
            const remarks = $el.find('.slide-info-remarks').first().text().trim() || '';

            if (title && vod_id && !seen.has(vod_id)) {
                seen.add(vod_id);
                videos.push({
                    vod_id,
                    vod_name: title,
                    vod_pic: fixUrl(pic),
                    vod_remarks: remarks
                });
            }
        });

        // 总页数
        let pagecount = 1;
        const pageTip = $('.page-tip').text().trim();
        if (pageTip) {
            const match = pageTip.match(/当前\d+\/(\d+)页/);
            if (match) pagecount = parseInt(match[2]) || 1;
        }
        return JSON.stringify({
            list: videos,
            page: 1,
            pagecount: pagecount,
            limit: 20,
            total: videos.length
        });
    } catch (e) {
        console.log('search error:', e);
        return JSON.stringify({ list: [] });
    }
}

// ==================== 5. 详情页解析 ====================
async function detail(id) {
    try {
        const url = id.startsWith('http') ? id : HOST + id;
        const res = await req(url, { headers: { 'User-Agent': UA } });
        const $ = load(res.content);

        // 标题
        let vod_name = $('h3.slide-info-title').text().trim();
        if (!vod_name) vod_name = $('.player-title-link').text().trim();
        if (!vod_name) vod_name = $('title').text().replace(/^.*? - /, '').replace(/ - .*$/, '');

        // 封面
        let vod_pic = $('.detail-pic img').attr('data-src') || $('.detail-pic img').attr('src') || '';
        if (!vod_pic) vod_pic = $('.vod-detail .detail-pic img').attr('data-src') || '';

        // 简介
        let vod_content = $('#height_limit').text().trim() || $('.vod-news .text').first().text().trim() || '';

        // 元数据：年份、地区、类型
        let vod_year = '', vod_area = '';
        $('.slide-info .slide-info-remarks a').each((i, el) => {
            const text = $(el).text().trim();
            if (/^\d{4}$/.test(text)) vod_year = text;
            else if (['日本','大陆','香港','台湾','美国','英国','韩国','法国','德国','泰国','印度','意大利','西班牙','加拿大','其他'].includes(text)) {
                vod_area = text;
            }
        });
        // 类型
        // ---- 提取演员和导演 ----
        let vod_actor = '', vod_director = '', type_name = '';

        // 方式1：从 .slide-info.partition 中提取
        $('.slide-info.partition').each((i, el) => {
            const $el = $(el);
          
          	// 类型
            const typeStrong = $el.find('strong:contains("类型")');
            if (typeStrong.length) {
                const typeLinks = typeStrong.nextAll('a').map((j, a) => $(a).text().trim()).get();
                if (typeLinks.length) type_name = typeLinks.join(',');
            }
            // 导演
            const dirStrong = $el.find('strong:contains("导演")');
            if (dirStrong.length) {
                const dirLinks = dirStrong.nextAll('a').map((j, a) => $(a).text().trim()).get();
                if (dirLinks.length) vod_director = dirLinks.join(',');
            }
            // 演员
            const actorStrong = $el.find('strong:contains("演员")');
            if (actorStrong.length) {
                const actorLinks = actorStrong.nextAll('a').map((j, a) => $(a).text().trim()).get();
                if (actorLinks.length) vod_actor = actorLinks.join(',');
            }
        });

        // ---- 播放源与剧集 ----
        const playFrom = [];
        const playUrls = [];

        // 获取线路名称
        const sourceNames = [];
        $('.anthology-tab a').each((i, el) => {
            let name = $(el).text().trim();
            name = name.replace(/<i[^>]*>.*?<\/i>/, '').replace(/&nbsp;/g, '').replace(/<span[^>]*>.*?<\/span>/, '').trim();
            if (name) sourceNames.push(name);
        });
        if (!sourceNames.length) {
            $('.vod-playerUrl').each((i, el) => {
                let name = $(el).text().trim();
                name = name.replace(/<i[^>]*>.*?<\/i>/, '').replace(/<span[^>]*>.*?<\/span>/, '').trim();
                if (name) sourceNames.push(name);
            });
        }

        const boxes = $('.anthology-list-box');
        if (boxes.length && sourceNames.length) {
            boxes.each((idx, box) => {
                const name = sourceNames[idx] || ('线路' + (idx+1));
                const episodes = [];
                $(box).find('ul.anthology-list-play li a').each((j, ep) => {
                    const $ep = $(ep);
                    let epName = $ep.find('span').text().trim() || $ep.text().trim();
                    let href = $ep.attr('href');
                    if (epName && href) {
                        href = fixUrl(href);
                        episodes.push(epName + '$' + href);
                    }
                });
                if (episodes.length) {
                    playFrom.push(name);
                    playUrls.push(episodes.join('#'));
                }
            });
        }

        if (!playFrom.length) {
            const singleBox = $('.anthology-list-play');
            if (singleBox.length) {
                const episodes = [];
                singleBox.find('li a').each((j, ep) => {
                    const $ep = $(ep);
                    let epName = $ep.find('span').text().trim() || $ep.text().trim();
                    let href = $ep.attr('href');
                    if (epName && href) {
                        href = fixUrl(href);
                        episodes.push(epName + '$' + href);
                    }
                });
                if (episodes.length) {
                    playFrom.push('默认线路');
                    playUrls.push(episodes.join('#'));
                }
            }
        }

        const vod = {
            vod_id: id,
            vod_name,
            vod_pic: fixUrl(vod_pic),
            type_name,
            vod_actor: vod_actor,
            vod_director: vod_director,
            vod_year,
            vod_area,
            vod_remarks: '',
            vod_content,
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playUrls.join('$$$')
        };

        return JSON.stringify({ list: [vod] });
    } catch (e) {
        console.log('detail error:', e);
        return null;
    }
}

// ==================== 6. 播放链接解析 ====================
async function play(flag, id, flags) {
    try {
        const playUrl = id.startsWith('http') ? id : HOST + id;
        const res = await req(playUrl, { headers: { 'User-Agent': UA } });
        const html = res.content;
      
        const match = html.match(/player_.*?=([^]*?)</);    	
        if (!match) return JSON.stringify({ parse: 1, url: playUrl });
        
        const config = JSON.parse(match[1]);
        let videoUrl = (config.url || '').trim();
        if (!videoUrl) return JSON.stringify({ parse: 1, url: playUrl });
        
        const directVideoPattern = /\.(m3u8|mp4|mkv|flv|avi|mov|wmv|webm)(\?.*)?$/i;
        if (directVideoPattern.test(videoUrl)) {
          	console.log('videoUrl:', videoUrl);
            return JSON.stringify({ parse: 0, url: videoUrl });
        }

		const tryParse = async (apiPath) => {
            try {
                const apiUrl = `https://player.catw.moe${apiPath}${encodeURIComponent(videoUrl)}&_t=${Date.now()}`;
                const res = await req(apiUrl, { headers: { 'User-Agent': UA } });
                const html = res.content;
                // 提取 uid
                const uidMatch = html.match(/"uid"\s*:\s*"([^"]+)"/);
                const uid = uidMatch ? uidMatch[1] : null;
				console.log('uid:', uid);
                // 提取 url (ConFig 根层级那个长字符串)
                const urlMatch = html.match(/"url"\s*:\s*"([^"]+)"/);
                const url = urlMatch ? urlMatch[1] : null;
              	console.log('url:', url);
                if (!uid || !url) {
                    console.log('[喵物次元] ConFig 缺少 uid 或 url');
                    return null;
                }

                const realUrl = decryptEcUrl(url, uid);
                if (realUrl) {
                    return { url: realUrl, ua: UA };
                }
                return null;
            } catch (e) {
                return null;
            }
        };
        
        let parsed = await tryParse('/player/ec.php?code=qw&if=1&url=');
        if (!parsed) parsed = await tryParse('/art.php?url=');
        
        if (parsed) {
            return JSON.stringify({
                parse: 0,
                url: parsed.url,
                header: { 'User-Agent': parsed.ua }
            });
        }
        
        return JSON.stringify({ parse: 1, url: playUrl });
    } catch (e) {
        return JSON.stringify({ parse: 1, url: id });
    }
}

function decryptEcUrl(encryptedBase64, uid) {
    try {
        const aesKey = '2890' + uid + 'tB959C';
        const aesIv = '2F131BE91247866E';
        // aesX(算法, 加密?false=解密, 数据, 输入是Base64?, key, iv, 输出是Base64?)
        const realUrl = aesX('AES/CBC/PKCS7', false, encryptedBase64, true, aesKey, aesIv, false);
      	console.log(realUrl)
        return realUrl;
    } catch (e) {
        return null;
    }
}

// ==================== 导出 ====================
export function __jsEvalReturn() {
    return {
        init,
        home,
      	homeVod,
        category,
        detail,
        play,
        search
    };
}