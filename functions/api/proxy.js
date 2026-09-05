// functions/api/proxy.js - 强化伪装版

const UA_POOL = [
  "okhttp/3.15",
  "okhttp/4.9.3",
  "TVBox/1.0.0",
  "com.github.tvbox",
  "CatVod/1.0.0",
  "Mozilla/5.0 (Linux; Android 9; Pixel 3 XL Build/PQ3A.190801.002) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/88.0.4324.181 Mobile Safari/537.36",
  "Dalvik/2.1.0 (Linux; U; Android 9; MI 9 Build/PKQ1.190118.001)",
];

function pickUA() { return UA_POOL[Math.floor(Math.random() * UA_POOL.length)]; }

// 判断响应是不是"拦截页/首页"(HTML)
function isHtmlPage(text) {
  if (!text) return false;
  const t = text.trim().toLowerCase();
  return t.startsWith("<!doctype") || t.startsWith("<html") || t.includes("<head>");
}

// 中文域名 → punycode
function toPunycode(host) {
  if (!host) return host;
  if (/[^\x00-\x7F]/.test(host)) {
    try {
      // Cloudflare Workers 全局有 punycode，但稳妥起见手动处理
      return host.split(".").map(seg => {
        if (/[^\x00-\x7F]/.test(seg)) {
          // 用 TextEncoder + encodeURIComponent 转 punycode
          return "xn--" + encodeURIComponent(seg).replace(/%/g, "").toLowerCase();
        }
        return seg;
      }).join(".");
    } catch { return host; }
  }
  return host;
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const target = url.searchParams.get("url");

  if (!target) {
    return new Response(JSON.stringify({ error: "Missing ?url=" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 规范化 URL（补 scheme）
  let finalUrl = target;
  if (!/^https?:\/\//i.test(finalUrl)) finalUrl = "http://" + finalUrl;

  // punycode 处理中文域名
  try {
    const parsed = new URL(finalUrl);
    const newHost = toPunycode(parsed.hostname);
    if (newHost !== parsed.hostname) {
      parsed.hostname = newHost;
      finalUrl = parsed.toString();
    }
  } catch {}

  // 最多重试 3 个 UA
  const triedUAs = [];
  for (let attempt = 0; attempt < 3; attempt++) {
    const ua = pickUA();
    triedUAs.push(ua);

    const headers = new Headers({
      "User-Agent": ua,
      "X-Requested-With": "com.iptvbox",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Encoding": "gzip, deflate",
      "Connection": "keep-alive",
      "Referer": finalUrl,
    });

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);

    try {
      const resp = await fetch(finalUrl, {
        method: "GET",
        headers,
        signal: controller.signal,
        redirect: "follow",
      });
      clearTimeout(timer);

      if (!resp.ok) {
        // 5xx 才重试，4xx 直接返回
        if (resp.status >= 500 && attempt < 2) continue;
        return new Response(JSON.stringify({ error: `HTTP ${resp.status}`, ua }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        });
      }

      let body;
      const contentType = resp.headers.get("content-type") || "";

      // 处理 gzip：Cloudflare 通常会自动解压，但保险起见
      if (resp.body && contentType.includes("gzip")) {
        try {
          const ds = new DecompressionStream("gzip");
          const dec = await new Response(resp.body).pipeThrough(ds).arrayBuffer();
          body = dec;
        } catch {
          body = await resp.arrayBuffer();
        }
      } else {
        body = await resp.arrayBuffer();
      }

      // 检测是否为拦截页（返回了 HTML 首页）
      const text = new TextDecoder("utf-8").decode(new Uint8Array(body.slice(0, 1024)));
      if (isHtmlPage(text) && attempt < 2) {
        // 换 UA 重试
        continue;
      }

      return new Response(body, {
        headers: {
          "Content-Type": contentType.includes("json") ? "application/json" : "application/octet-stream",
          "Access-Control-Allow-Origin": "*",
          "X-Tried-UAs": JSON.stringify(triedUAs),
        },
      });

    } catch (e) {
      clearTimeout(timer);
      if (attempt < 2) continue; // 超时/网络错误重试
      return new Response(JSON.stringify({ error: e.message, ua }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  }

  return new Response(JSON.stringify({ error: "All UA attempts returned HTML (likely blocked)", triedUAs }), {
    status: 403,
    headers: { "Content-Type": "application/json" },
  });
}
