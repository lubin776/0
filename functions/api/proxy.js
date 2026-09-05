// Cloudflare Pages Functions - API 代理
// 处理 TVBox 接口请求，伪装 UA 和请求头

const TVBOX_UAS = [
  { ua: "okhttp/3.15", xrw: "com.iptvbox" },
  { ua: "okhttp/4.9.3", xrw: "com.iptvbox" },
  { ua: "TVBox/1.0.0", xrw: "com.iptvbox" },
  { ua: "com.github.tvbox", xrw: "com.iptvbox" },
  { ua: "Dalvik/2.1.0 (Linux; U; Android 9; Pixel 3 XL Build/PQ3A.190801.002)", xrw: "com.iptvbox" },
  { ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", xrw: "" },
];

function getRandomUA() {
  return TVBOX_UAS[Math.floor(Math.random() * TVBOX_UAS.length)];
}

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const targetUrl = url.searchParams.get("url");

  if (!targetUrl) {
    return new Response(JSON.stringify({ error: "Missing 'url' parameter" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 处理中文域名 punycode 转换
  let finalUrl = targetUrl;
  try {
    const parsed = new URL(targetUrl);
    if (parsed.hostname && /[^\x00-\x7F]/.test(parsed.hostname)) {
      // Cloudflare Workers 环境用 punycode
      const { toASCII } = await import("punycode");
      parsed.hostname = toASCII(parsed.hostname);
      finalUrl = parsed.toString();
    }
  } catch (e) {
    // 如果 URL 解析失败，尝试直接请求
  }

  const { ua, xrw } = getRandomUA();
  const headers = new Headers();
  headers.set("User-Agent", ua);
  if (xrw) headers.set("X-Requested-With", xrw);
  headers.set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8");
  headers.set("Connection", "keep-alive");

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 20000);

    const resp = await fetch(finalUrl, {
      method: "GET",
      headers,
      signal: controller.signal,
      redirect: "follow",
    });

    clearTimeout(timeoutId);

    // 如果返回 HTML（可能是拦截页面），尝试换 UA 重试一次
    const contentType = resp.headers.get("content-type") || "";
    if (contentType.includes("text/html") && resp.status === 200) {
      const text = await resp.text();
      if (text.trim().startsWith("<!DOCTYPE") || text.trim().startsWith("<html")) {
        // 返回原始响应，让前端处理
        return new Response(text, {
          status: 200,
          headers: { "Content-Type": "text/html" },
        });
      }
      return new Response(text, {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    // 直接流式返回
    return new Response(resp.body, {
      status: resp.status,
      headers: {
        "Content-Type": contentType || "application/octet-stream",
        "Access-Control-Allow-Origin": "*",
      },
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
