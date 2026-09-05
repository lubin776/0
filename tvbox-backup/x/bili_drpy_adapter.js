/*
 * TVBox drpy2 适配层
 * 作用：读取外部 bili.json 合集，转发给 bzys.js 处理
 * 作者：适配自用
 */

var MAIN_JS = "https://gh-proxy.com/raw.githubusercontent.com/yjfqb/tvbox-source/master/js/bzys.js";

// 默认合集地址（可被子类 ext 参数覆盖）
var DEFAULT_BILI_JSON = "https://gh-proxy.com/raw.githubusercontent.com/guot55/YGBH/refs/heads/main/pro/json/bili.json";

function init() {
    // 返回分类（drpy2 必须）
    return [];
}

function home() {
    // 首页分类
    return {};
}

function category(tid, pg, filter, extend) {
    // 转发给 bzys.js 处理
    var biliJson = ext || DEFAULT_BILI_JSON;
    var url = MAIN_JS + "?type=url&params=" + encodeURIComponent(biliJson);
    return request(url, { body: JSON.stringify({ tid: tid, pg: pg, filter: filter, extend: extend }) });
}

function detail(id) {
    var biliJson = ext || DEFAULT_BILI_JSON;
    var url = MAIN_JS + "?type=detail&params=" + encodeURIComponent(biliJson) + "&id=" + id;
    return request(url);
}

function play(flag, id, flags) {
    var biliJson = ext || DEFAULT_BILI_JSON;
    var url = MAIN_JS + "?type=play&params=" + encodeURIComponent(biliJson) + "&flag=" + flag + "&id=" + id;
    return request(url);
}

function search(wd, quick) {
    var biliJson = ext || DEFAULT_BILI_JSON;
    var url = MAIN_JS + "?type=search&params=" + encodeURIComponent(biliJson) + "&wd=" + encodeURIComponent(wd);
    return request(url);
}
