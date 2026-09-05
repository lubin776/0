// app.js - 前端交互逻辑

const PROXY_BASE = "/api/proxy?url=";

function log(msg, type = "info") {
  const el = document.getElementById("log");
  const span = document.createElement("span");
  span.className = type;
  const time = new Date().toLocaleTimeString();
  span.textContent = `[${time}] ${msg}\n`;
  el.appendChild(span);
  el.scrollTop = el.scrollHeight;
}

function clearAll() {
  document.getElementById("urlInput").value = "";
  document.getElementById("log").innerHTML = "";
  document.getElementById("output").value = "";
  document.getElementById("resultCard").style.display = "none";
}

// 预设标签点击
document.querySelectorAll(".preset-tag").forEach(tag => {
  tag.addEventListener("click", () => {
    document.getElementById("urlInput").value = tag.dataset.url;
  });
});

async function fetchWithProxy(url) {
  const resp = await fetch(PROXY_BASE + encodeURIComponent(url));
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const arrayBuffer = await resp.arrayBuffer();
  let bytes = new Uint8Array(arrayBuffer);

  // 尝试 gzip 解压
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    try {
      const ds = new DecompressionStream("gzip");
      const decompressed = await new Response(bytes).body.pipeThrough(ds).getReader().read();
      if (decompressed.value) bytes = decompressed.value;
    } catch {}
  }

  return bytes;
}

async function parseOne(url) {
  log(`▶ 正在解析: ${url}`, "info");
  try {
    const rawBytes = await fetchWithProxy(url);
    log(`  ✓ 下载成功 (${rawBytes.length} 字节)`, "ok");

    const rawText = new TextDecoder("utf-8").decode(rawBytes);
    let result = window.TVBoxParser.findResult(rawText, rawBytes);

    // 尝试 gzip 再解一次（如果解密后还是 gzip）
    if (!window.TVBoxParser.isJson(result)) {
      try {
        const bytes = str2bytes(result);
        if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
          const ds = new DecompressionStream("gzip");
          const dec = await new Response(bytes).body.pipeThrough(ds).getReader().read();
          if (dec.value) result = new TextDecoder().decode(dec.value);
        }
      } catch {}
    }

    result = window.TVBoxParser.filterJson(result);
    result = window.TVBoxParser.absolutizeJson(result, url);

    document.getElementById("output").value = result;
    document.getElementById("resultCard").style.display = "block";
    log(`  ✓ 解析完成 (${result.length} 字符)`, "ok");
    return result;
  } catch (e) {
    log(`  ✗ 失败: ${e.message}`, "err");
    throw e;
  }
}

async function startParse() {
  const input = document.getElementById("urlInput").value.trim();
  if (!input) { alert("请先输入接口 URL"); return; }

  const urls = input.split("\n").map(u => u.trim()).filter(Boolean);
  log(`━━━ 开始批量解析，共 ${urls.length} 个 ━━━`, "info");

  for (const url of urls) {
    try { await parseOne(url); }
    catch {}
    await new Promise(r => setTimeout(r, 500));
  }
  log("━━━ 全部完成 ━━━", "info");
}

function copyResult() {
  const out = document.getElementById("output");
  out.select();
  document.execCommand("copy");
  alert("已复制到剪贴板");
}

function downloadResult() {
  const text = document.getElementById("output").value;
  const blob = new Blob([text], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `tvbox_${Date.now()}.json`;
  a.click();
}

function str2bytes(s) { return new Uint8Array(s.split("").map(c => c.charCodeAt(0) & 0xFF)); }
