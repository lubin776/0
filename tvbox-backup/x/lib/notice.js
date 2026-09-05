function homeContent() {
    // 时间戳：防止壳子缓存旧数据
    let t = new Date().getTime();

    // 分类 Tab（页顶菜单）
    let classes = [
        {
            type_id: "recommend_" + t,
            type_name: "🏠 推荐"
        },
        {
            type_id: "tutorial_" + t,
            type_name: "📦 教程"
        },
        {
            type_id: "notice_" + t,
            type_name: "⚠️ 免责"
        }
    ];

    // 视频列表（每张卡片一个唯一 vod_id）
    let list = [];

    // 推荐
    list.push({
        type_id: "recommend_" + t,
        vod_id: "x4_" + t,
        vod_name: "X4 直连线路",
        vod_pic: "https://via.placeholder.com/300x450/222222/FFFFFF?text=X4",
        vod_remarks: "推荐",
        vod_content: "✅ 本地直连，速度快\n✅ 稳定性高\n✅ 适合网络较差环境\n\n输入地址：\nclan://localhost/tvbox/x4/x4.json"
    });

    // 教程
    list.push({
        type_id: "tutorial_" + t,
        vod_id: "tutorial_" + t,
        vod_name: "本地包配置教程",
        vod_pic: "https://via.placeholder.com/300x450/1E90FF/FFFFFF?text=LOCAL",
        vod_remarks: "📦 必看",
        vod_content: "本接口由【误道者】打包上传。\n\n配置步骤：\n1️⃣ 点击在线更新本地包\n2️⃣ 输入：\nclan://localhost/tvbox/x4/x4.json\n\n更多本地包请加 QQ 群：1067685939"
    });

    // 免责声明
    list.push({
        type_id: "notice_" + t,
        vod_id: "notice_" + t,
        vod_name: "免责声明",
        vod_pic: "https://via.placeholder.com/300x450/8B0000/FFFFFF?text=NOTICE",
        vod_remarks: "重要",
        vod_content: "⚠️ 免责声明\n\n所有资源来自互联网，版权归原作者所有。\n仅供测试学习使用，请勿用于违法及商业用途。\n请勿付费购买任何影视资源。\n\n如涉及侵权，请联系删除。\n\nQQ 群：1067685939"
    });

    return JSON.stringify({
        page: 1,
        pagecount: 1,
        limit: list.length,
        total: list.length,
        class: classes,
        list: list
    });
}

// ===== 以下方法留空即可 =====
function categoryContent(tid, pg, filter, extend) {
    return "";
}

function detailContent(ids) {
    return "";
}

function playerContent(flag, id, vipFlags) {
    return "";
}

function searchContent(key) {
    return "";
}
