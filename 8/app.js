// app.js

function log(msg, type) {
  const el = document.getElementById("log");
  const line = document.createElement("div");
  line.className = "log-line log-" + (type || "info");
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${msg}`;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function dbg(msg) { log(msg, "info"); }

function setUrl(url) {
  document.getElementById("url").value = url;
}

async function parse() {
  const url = document.getElementById("url").value.trim();
  if (!url) { log("请输入接口 URL", "err"); return; }

  document.getElementById("resultCard").style.display = "none";
  document.getElementById("output").value = "";
  log(`开始解析: ${url}`);

  try {
    // 通过 CF Worker 代理请求
    const proxyUrl = `/api/proxy?url=${encodeURIComponent(url)}`;
    log(`请求代理: ${proxyUrl}`);
    const resp = await fetch(proxyUrl);

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }

    const contentType = resp.headers.get("content-type") || "";
    let result;

    if (contentType.includes("application/json")) {
      result = await resp.text();
      log("  收到 JSON 响应，直接解析", "ok");
    } else {
      // 可能是二进制（gzip / 加密）
      const arrayBuffer = await resp.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);
      log(`  收到二进制数据: ${bytes.length} 字节`);

      // 尝试 gzip 解压
      if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
        log("  检测到 gzip 压缩，解压中...");
        try {
          const ds = new DecompressionStream("gzip");
          const decompressed = await new Response(bytes).body.pipeThrough(ds).getReader().read();
          if (decompressed.value) {
            const decBytes = decompressed.value;
            let text = new TextDecoder().decode(decBytes);
            // 递归解密
            text = window.TVBoxParser.findResult(text, decBytes);
            result = text;
            log("  gzip 解压+解密完成", "ok");
          } else {
            throw new Error("gzip 解压失败");
          }
        } catch (e) {
          log(`  gzip 解压失败: ${e.message}`, "err");
          result = new TextDecoder().decode(bytes);
        }
      } else {
        // 直接走解密逻辑
        result = window.TVBoxParser.findResult("", bytes);
      }
    }

    // 过滤 + 绝对化 URL
    result = window.TVBoxParser.filterJson(result);
    result = window.TVBoxParser.absolutizeJson(result, url);

    document.getElementById("output").value = result;
    document.getElementById("resultCard").style.display = "block";
    log(`✓ 解析完成 (${result.length} 字符)`, "ok");

    // 尝试预览
    try {
      const obj = JSON.parse(result);
      if (obj.sites) log(`  sites 数量: ${obj.sites.length}`, "info");
      if (obj.lives) log(`  lives 数量: ${obj.lives.length}`, "info");
    } catch {}

  } catch (err) {
    log(`✗ 解析失败: ${err.message}`, "err");
    console.error(err);
  }
}

function copyResult() {
  const output = document.getElementById("output");
  output.select();
  document.execCommand("copy");
  log("结果已复制到剪贴板", "ok");
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
