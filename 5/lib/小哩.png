/**
内容仅供交流学习使用 如侵犯了您的权益 请通知作者 将及时删除侵权内容
夏夜:
基于原js代码在基础上修改了预告显示问题，现不会显示预告
2025.12.27修复搜索问题
2025.12.28屏蔽搜索无结果 再优化搜索响应速度
 */


var rule = {
    title:'哔哩影视[官]',
    host:'https://api.bilibili.com',
    url:'/fyclass-fypage&vmid=$vmid',
    detailUrl:'/pgc/view/web/season?season_id=fyid',
    filter_url:'fl={{fl}}',
    vmid获取教程:'登录后访问https://api.bilibili.com/x/web-interface/nav,搜索mid就是,cookie需要 bili_jct,DedeUserID,SESSDATA参数',
    searchUrl:'/x/web-interface/search/type?keyword=**&page=fypage&search_type=media_bangumi&search_type=media_ft',
    searchable:1,
    filterable:1,
    quickSearch:0,
    headers:{
        'User-Agent':'PC_UA',
        "Referer": "https://www.bilibili.com",
        "Cookie":"b_nut=1754358399; buvid3=0F2F49F9-DB89-BB64-8C82-0FC19C89700C99838infoc; bsource=search_baidu; _uuid=D75882107-8DA4-5CEB-610BF-1C947B575F6F00241infoc; buvid4=708DFED9-5C46-1145-2E55-C666A6DCD00D00431-125080509-2JaJVUbLMmiKSv6f1hrFWOzvO5HPB0qiGQ88G7/gWinLq9zArOyfN4Sxbea0Elu2; bmg_af_switch=1; bmg_src_def_domain=i0.hdslb.com; buvid_fp=a648a8f1a55caf7d8a9f1cf0a7012532; rpdid=0zbfvUmrTi|gvd1C9k3|4EB|3w1UJ6Qk; b_lsid=3F6610F34_19B627D262F; home_feed_column=4; browser_resolution=1100-2444; theme-tip-show=SHOWED; theme-avatar-tip-show=SHOWED; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjcxNDM0NjAsImlhdCI6MTc2Njg4NDIwMCwicGx0IjotMX0.Mq61VKWaA2PwrfGmjz5wdxxTq4gAEl8OCW1aC1vcyAg; bili_ticket_expires=1767143400; CURRENT_FNVAL=16; CURRENT_QUALITY=0; sid=pp8jodon"
    },
    tab_order:['bilibili'],//线路顺序,按里面的顺序优先，没写的依次排后面
    timeout:5000,
    class_name:'番剧&国创&电影&电视剧&纪录片&综艺&全部&追番&追剧&时间表',
    class_url:'1&4&2&5&3&7&全部&追番&追剧&时间表',
    filter:{"全部":[{"key":"tid","name":"分类","value":[{"n":"番剧","v":"1"},{"n":"国创","v":"4"},{"n":"电影","v":"2"},{"n":"电视剧","v":"5"},{"n":"记录片","v":"3"},{"n":"综艺","v":"7"}]},{"key":"order","name":"排序","value":[{"n":"播放数量","v":"2"},{"n":"更新时间","v":"0"},{"n":"最高评分","v":"4"},{"n":"弹幕数量","v":"1"},{"n":"追看人数","v":"3"},{"n":"开播时间","v":"5"},{"n":"上映时间","v":"6"}]},{"key":"season_status","name":"付费","value":[{"n":"全部","v":"-1"},{"n":"免费","v":"1"},{"n":"付费","v":"2%2C6"},{"n":"大会员","v":"4%2C6"}]}],"时间表":[{"key":"tid","name":"分类","value":[{"n":"番剧","v":"1"},{"n":"国创","v":"4"}]}]},
    play_parse:true,
    // play_json:[{re:'*', json:{jx:1, parse:0,header:JSON.stringify({"user-agent":"PC_UA"})}}],
    pagecount:{"1":1,"2":1,"3":1,"4":1,"5":1,"7":1,"时间表":1},
     lazy: $js.toString(() => {
        try {
            let api = "" + input.split("?")[0];
            console.log(api);
            let response = fetch(api, {
                method: 'get',
                headers: {
                    'User-Agent': 'okhttp/3.14.9',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });
            let bata = JSON.parse(response);
            if (bata.url.includes("qiyi")) {
                input = {
                    parse: 0,
                    url: bata.url,
                    jx: 0,
                    danmaku: "" + input.split("?")[0]
                };
            } else {
                input = {
                    parse: 0,
                    url: input.split("?")[0],
                    jx: 1,
                    danmaku: "" + input.split("?")[0]
                };
            }
        } catch {
            input = {
                parse: 0,
                url: input.split("?")[0],
                jx: 1,
                danmaku: "" + input.split("?")[0]
            };
        }
    }),
    limit:5,
    推荐:'js:let d=[];function get_result(url){let videos=[];let html=request(url);let jo=JSON.parse(html);if(jo["code"]===0){let vodList=jo.result?jo.result.list:jo.data.list;vodList.forEach(function(vod){let aid=(vod["season_id"]+"").trim();let title=vod["title"].trim();let img=vod["cover"].trim();let remark=vod.new_ep?vod["new_ep"]["index_show"]:vod["index_show"];if(!title.includes("预告")){videos.push({vod_id:aid,vod_name:title,vod_pic:img,vod_remarks:remark})}})}return videos}function get_rank(tid,pg){return get_result("https://api.bilibili.com/pgc/web/rank/list?season_type="+tid+"&pagesize=20&page="+pg+"&day=3")}function get_rank2(tid,pg){return get_result("https://api.bilibili.com/pgc/season/rank/web/list?season_type="+tid+"&pagesize=20&page="+pg+"&day=3")}function home_video(){let videos=get_rank(1).slice(0,5);[4,2,5,3,7].forEach(function(i){videos=videos.concat(get_rank2(i).slice(0,5))});return videos}VODS=home_video();',
    一级:'js:let d=[];let vmid=input.split("vmid=")[1].split("&")[0];function get_result(url){let videos=[];let html=request(url);let jo=JSON.parse(html);if(jo["code"]===0){let vodList=jo.result?jo.result.list:jo.data.list;vodList.forEach(function(vod){let aid=(vod["season_id"]+"").trim();let title=vod["title"].trim();let img=vod["cover"].trim();let remark=vod.new_ep?vod["new_ep"]["index_show"]:vod["index_show"];if(!title.includes("预告") && !remark.includes("预告")){videos.push({vod_id:aid,vod_name:title,vod_pic:img,vod_remarks:remark})}})}return videos}function get_rank(tid,pg){return get_result("https://api.bilibili.com/pgc/web/rank/list?season_type="+tid+"&pagesize=20&page="+pg+"&day=3")}function get_rank2(tid,pg){return get_result("https://api.bilibili.com/pgc/season/rank/web/list?season_type="+tid+"&pagesize=20&page="+pg+"&day=3")}function get_zhui(pg,mode){let url="https://api.bilibili.com/x/space/bangumi/follow/list?type="+mode+"&follow_status=0&pn="+pg+"&ps=10&vmid="+vmid;return get_result(url)}function get_all(tid,pg,order,season_status){let url="https://api.bilibili.com/pgc/season/index/result?order="+order+"&pagesize=20&type=1&season_type="+tid+"&page="+pg+"&season_status="+season_status;return get_result(url)}function get_timeline(tid,pg){let videos=[];let url="https://api.bilibili.com/pgc/web/timeline/v2?season_type="+tid+"&day_before=2&day_after=4";let html=request(url);let jo=JSON.parse(html);if(jo["code"]===0){let videos1=[];let vodList=jo.result.latest;vodList.forEach(function(vod){let aid=(vod["season_id"]+"").trim();let title=vod["title"].trim();let img=vod["cover"].trim();let remark=vod["pub_index"]+"　"+vod["follows"].replace("系列","");if(!title.includes("预告") && !remark.includes("预告")){videos1.push({vod_id:aid,vod_name:title,vod_pic:img,vod_remarks:remark})}});let videos2=[];for(let i=0;i<7;i++){let vodList=jo["result"]["timeline"][i]["episodes"];vodList.forEach(function(vod){if(vod["published"]+""==="0" && !vod["title"].includes("预告")){let aid=(vod["season_id"]+"").trim();let title=vod["title"].trim();let img=vod["cover"].trim();let date=vod["pub_ts"];let remark=date+"   "+vod["pub_index"];videos2.push({vod_id:aid,vod_name:title,vod_pic:img,vod_remarks:remark})}})}videos=videos2.concat(videos1)}return videos}function cate_filter(d,cookie){if(MY_CATE==="1"){return get_rank(MY_CATE,MY_PAGE)}else if(["2","3","4","5","7"].includes(MY_CATE)){return get_rank2(MY_CATE,MY_PAGE)}else if(MY_CATE==="全部"){let tid=MY_FL.tid||"1";let order=MY_FL.order||"2";let season_status=MY_FL.season_status||"-1";return get_all(tid,MY_PAGE,order,season_status)}else if(MY_CATE==="追番"){return get_zhui(MY_PAGE,1)}else if(MY_CATE==="追剧"){return get_zhui(MY_PAGE,2)}else if(MY_CATE==="时间表"){let tid=MY_FL.tid||"1";return get_timeline(tid,MY_PAGE)}else{return[]}}VODS=cate_filter();',
    二级:{
        is_json:true,
        title:".result.title;.result.share_sub_title",
        img:".result.cover",
        desc:".result.new_ep.desc;.result.publish.pub_time;.result.subtitle",
        content:".result.evaluate",
        tabs:"js:pdfa=jsp.pdfa;TABS=['B站']",
        lists:".result.episodes",
        list_text:'title',
        list_url:'cid',
    },
    二级:'js:function zh(num){let p="";if(Number(num)>1e8){p=(num/1e8).toFixed(2)+"亿"}else if(Number(num)>1e4){p=(num/1e4).toFixed(2)+"万"}else{p=num}return p}let html=request(input);let jo=JSON.parse(html).result;let id=jo["season_id"];let title=jo["title"];let pic=jo["cover"];let areas=jo["areas"][0]["name"];let typeName=jo["share_sub_title"];let date=jo["publish"]["pub_time"].substr(0,4);let dec=jo["evaluate"];let remark=jo["new_ep"]["desc"];let stat=jo["stat"];let status="弹幕: "+zh(stat["danmakus"])+"　点赞: "+zh(stat["likes"])+"　投币: "+zh(stat["coins"])+"　追番追剧: "+zh(stat["favorites"]);let score=jo.hasOwnProperty("rating")?"评分: "+jo["rating"]["score"]+"　"+jo["subtitle"]:"暂无评分"+"　"+jo["subtitle"];let vod={vod_id:id,vod_name:title,vod_pic:pic,type_name:typeName,vod_year:date,vod_area:areas,vod_remarks:remark,vod_actor:status,vod_director:score,vod_content:dec};let ja=jo["episodes"].filter(ep=>!ep.title.includes("预告") && !(ep.badge && ep.badge.includes("预告")));let playurls1=[];let playurls2=[];ja.forEach(function(tmpJo){let eid=tmpJo["id"];let cid=tmpJo["cid"];let link=tmpJo["link"];let part=tmpJo["title"].replace("#","-")+" "+tmpJo["long_title"]+"["+tmpJo["badge"]+"]";playurls1.push(part+"$"+eid+"_"+cid);playurls2.push(part+"$"+link)});let playUrl=playurls1.length>0?playurls1.join("#")+"$$$"+playurls2.join("#"):"";vod["vod_play_from"]="$$$bilibili";vod["vod_play_url"]=playUrl;VOD=vod;',
    搜索:'js:let encodedKeyword = encodeURIComponent(KEY);let url1 = "https://api.bilibili.com/x/web-interface/search/type?search_type=media_bangumi&keyword=" + encodedKeyword + "&page=" + MY_PAGE;let url2 = "https://api.bilibili.com/x/web-interface/search/type?search_type=media_ft&keyword=" + encodedKeyword + "&page=" + MY_PAGE;let html1 = request(url1);let html2 = request(url2);let jo1 = JSON.parse(html1);let jo2 = JSON.parse(html2);let videos = [];function cleanHtml(text) {if (!text) return "";return text.replace(/<[^>]+>/g, "").replace(/&quot;/g, \'"\').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");}if (jo1["code"] === 0 && jo1["data"]["numResults"] > 0) {let result1 = jo1["data"]["result"];for (let i = 0; i < result1.length; i++) {let vod = result1[i];let aid = (vod["season_id"] + "").trim();let title = cleanHtml(vod["title"]).trim();let img = vod["cover"].trim();let remark = cleanHtml(vod["index_show"]).trim();if (!title.includes("预告") && !remark.includes("预告")) {videos.push({vod_id: aid,vod_name: title,vod_pic: img,vod_remarks: remark});}}}if (jo2["code"] === 0 && jo2["data"]["numResults"] > 0) {let result2 = jo2["data"]["result"];for (let i = 0; i < result2.length; i++) {let vod = result2[i];let aid = (vod["season_id"] + "").trim();let title = cleanHtml(vod["title"]).trim();let img = vod["cover"].trim();let remark = cleanHtml(vod["index_show"]).trim();if (!title.includes("预告") && !remark.includes("预告")) {videos.push({vod_id: aid,vod_name: title,vod_pic: img,vod_remarks: remark});}}}VODS = videos;'
}