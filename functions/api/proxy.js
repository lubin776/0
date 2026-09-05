// Cloudflare Pages Functions - 代理层

const TVBOX_UAS = [
  { ua: "okhttp/3.15", xrw: "com.iptvbox" },
  { ua: "okhttp/4.9.3", xrw: "com.iptvbox" },
  { ua: "TVBox/1.0.0", xrw: "com.iptvbox" },
  { ua: "com.github.tvbox", xrw: "com.iptvbox" },
  { ua: "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)", xrw: "com.iptvbox" },
  { ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", xrw: "" },
];

function pickUA() {
  return TVBOX_UAS[Math.floor(Math.random() * TVBOX_UAS.length)];
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

  // 中文域名 punycode 转换
  let finalTarget = target;
  try {
    const parsed = new URL(target);
    if (/[^\x00-\x7F]/.test(parsed.hostname)) {
      finalTarget = target.replace(parsed.hostname, punycodeEncode(parsed.hostname));
    }
  } catch {}

  const { ua, xrw } = pickUA();
  const headers = new Headers({
    "User-Agent": ua,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
  });
  if (xrw) headers.set("X-Requested-With", xrw);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);

  try {
    const resp = await fetch(finalTarget, {
      headers,
      signal: controller.signal,
      redirect: "follow",
    });
    clearTimeout(timer);

    if (!resp.ok) {
      return new Response(JSON.stringify({ error: `HTTP ${resp.status}` }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }

    const body = await resp.arrayBuffer();
    return new Response(body, {
      headers: {
        "Content-Type": "application/octet-stream",
        "X-TVBox-UA": ua,
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (e) {
    clearTimeout(timer);
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}

// 简易 punycode 编码（ASCII 部分直接返回，中文用 IDNA 思路）
function punycodeEncode(domain) {
  // Cloudflare Workers 环境有 punycode 可用
  try {
    // @ts-ignore
    if (typeof punycode !== "undefined") return punycode.toASCII(domain);
  } catch {}
  // 兜底：直接返回（大部分现代 fetch 能处理）
  return domain;
}
