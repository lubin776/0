/**
 * TVBox 白壳 1741 兼容 B站合集 Spider
 * 零 import / 零 export / 零外部依赖
 * 用法：sites.api 指向此文件，ext = bili.json 的 raw 地址
 */

var UA = "Mozilla/5.0 (Linux; Android 11; TV) AppleWebKit/537.36 Chrome/77.0";
var BILI_JSON = "";

function log(s) {
    try { console.log(s) } catch(e) {}
}

/* ========== 工具 ========== */
function getJson() {
    if (BILI_JSON) return BILI_JSON;
    // ext 传进来的就是 bili.json 地址
    BILI_JSON = fetch(ext || "https://gh-proxy.com/raw.githubusercontent.com/guot55/YGBH/refs/heads/main/pro/json/bili.json", {
        headers: { "User-Agent": UA }
    });
    return BILI_JSON;
}

function parseJson(txt) {
    // 老壳子 JSON.parse 可用
    return JSON.parse(txt);
}

/* ========== init ========== */
function init() {
    log("bili_csp_legacy init");
    return "";
}

/* ========== home（分类） ========== */
function home() {
    var txt = getJson();
    var j = parseJson(txt);
    var classes = [];
    if (j && j.class_name && j.class_url) {
        var ns = j.class_name.split("&");
        var us = j.class_url.split("&");
        for (var i = 0; i < ns.length && i < us.length; i++) {
            classes.push({ type_id: us[i], type_name: ns[i] });
        }
    }
    return JSON.stringify({ class: classes });
}

/* ========== category ========== */
function category(tid, pg, filter, extend) {
    var txt = getJson();
    var j = parseJson(txt);
    var list = [];
    if (j && j.video_list) {
        // 简单分页：每页 20
        pg = parseInt(pg) || 1;
        var start = (pg - 1) * 20;
        for (var i = 0; i < j.video_list.length && list.length < 20; i++) {
            var v = j.video_list[i];
            // 按 tid 过滤（合集 json 里一般有 tid 或 tag）
            if (tid && v.tid && v.tid !== tid) continue;
            if (list.length >= start) {
                list.push({
                    vod_id: v.bvid || v.url || ("bili:" + i),
                    vod_name: v.title || v.name || "未知",
                    vod_pic: v.pic || v.cover || "",
                    vod_remarks: v.desc || ""
                });
            }
        }
    }
    return JSON.stringify({ page: pg, pagecount: 99, limit: 20, total: 999, list: list });
}

/* ========== detail ========== */
function detail(ids) {
    // ids 格式：bili:BV1xx 或 原 bvid
    var bvid = ids.replace("bili:", "");
    return JSON.stringify({
        list: [{
            vod_id: ids,
            vod_name: "B站视频",
            vod_pic: "",
            vod_play_from: "B站",
            vod_play_url: "播放$" + bvid
        }]
    });
}

/* ========== play（关键：返回直链或跳转） ========== */
function play(flag, id, flags) {
    // 老壳子方案：parse:0 让壳子走嗅探 / 或返回已签好的 m3u8
    // 这里返回 bvid，让壳子用内置 csp_Bili 逻辑（需 jar 支持）
    // 若壳子不支持，可改为主站直链（仅预览）
    return JSON.stringify({
        parse: 0,
        url: "https://www.bilibili.com/video/" + id,
        jx: 0
    });
}

/* ========== search ========== */
function search(wd, quick, pg) {
    var txt = getJson();
    var j = parseJson(txt);
    var list = [];
    if (j && j.video_list) {
        wd = (wd || "").toLowerCase();
        for (var i = 0; i < j.video_list.length && list.length < 20; i++) {
            var v = j.video_list[i];
            var name = (v.title || v.name || "").toLowerCase();
            if (name.indexOf(wd) !== -1) {
                list.push({
                    vod_id: v.bvid || v.url || ("bili:" + i),
                    vod_name: v.title || v.name,
                    vod_pic: v.pic || "",
                    vod_remarks: v.desc || ""
                });
            }
        }
    }
    return JSON.stringify({ page: 1, pagecount: 1, limit: 20, total: list.length, list: list });
}

/* ========== proxy（可选，留空） ========== */
function proxy(params) {
    return "";
}
