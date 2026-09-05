// app.js - 前端交互

function log(msg, type) {
  const el = document.getElementById("log");
  const line = document.createElement("div");
  line.className = "log-line log-" + (type || "info");
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${msg}`;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function setUrl(url) {
  document.getElementById("url").value = url;
  parse();
}

async function parse() {
  const url = document.getElementById("url").value.trim();
  if (!url) { log("请输入接口 URL", "err"); return; }

  document.getElementById("resultCard").style.display = "none";
  document.getElementById("output").value = "";
  document.getElementById("log").innerHTML = "";
  log(`开始解析: ${url}`);

  try {
    const proxyUrl = `/api/proxy?url=${encodeURIComponent(url)}`;
    log(`请求代理: ${proxyUrl}`);
    const resp = await fetch(proxyUrl);

    const triedUAs = resp.headers.get("X-Tried-UAs");
    if (triedUAs) log(`代理尝试 UA: ${triedUAs}`, "info");

    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      throw new Error(`HTTP ${resp.status} ${errText}`);
    }

    const contentType = resp.headers.get("content-type") || "";
    let result;

    if (contentType.includes("application/json") && !contentType.includes("octet-stream")) {
      result = await resp.text();
      log("收到 JSON 文本，进入解密流程", "ok");
      result = window.TVBoxParser.findResult(result, null);
    } else {
      const arrayBuffer = await resp.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      log(`收到二进制数据: ${bytes.length} 字节`);

      // gzip 检测
      if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
        log("检测到 gzip，解压中...");
        try {
          const ds = new DecompressionStream("gzip");
          const decompressed = await new Response(bytes).body.pipeThrough(ds).getReader().read();
          if (decompressed.value) {
            const decBytes = decompressed.value;
            result = window.TVBoxParser.findResult("", new Uint8Array(decBytes));
            log("gzip 解压 + 解密完成", "ok");
          } else throw new Error("gzip 解压为空");
        } catch (e) {
          log(`gzip 失败: ${e.message}，尝试直接解密`, "err");
          result = window.TVBoxParser.findResult("", bytes);
        }
      } else {
        result = window.TVBoxParser.findResult("", bytes);
      }
    }

    // 过滤 + URL 绝对化
    result = window.TVBoxParser.filterJson(result);
    result = window.TVBoxParser.absolutizeJson(result, url);

    document.getElementById("output").value = result;
    document.getElementById("resultCard").style.display = "block";
    log(`✓ 解析完成 (${result.length} 字符)`, "ok");

    try {
      const obj = JSON.parse(result);
      if (obj.sites) log(`  sites: ${obj.sites.length} 个`, "info");
      if (obj.lives) log(`  lives: ${obj.lives.length} 个`, "info");
      if (!obj.sites && !obj.lives) log("  ⚠ 未识别为标准 TVBox 配置，可能是明文或解析不完整", "err");
    } catch { log("  ⚠ 输出非合法 JSON", "err"); }

  } catch (err) {
    log(`✗ 解析失败: ${err.message}`, "err");
    console.error(err);
  }
}

function copyResult() {
  const output = document.getElementById("output");
  output.select();
  document.execCommand("copy");
  log("已复制到剪贴板", "ok");
}

function downloadResult() {
  const text = document.getElementById("output").value;
  if (!text) { log("没有内容可下载", "err"); return; }
  const blob = new Blob([text], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "tvbox_config.json";
  a.click();
  log("文件已下载", "ok");
}

// 回车触发
document.getElementById("url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") parse();
});
