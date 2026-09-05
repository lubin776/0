// parser.js - 完整解密逻辑，对照 Python 试跑2.py

function collapseWhitespace(text) {
  if (!text) return "";
  if (!/\s/.test(text)) return text;
  return text.replace(/\s+/g, " ").trim();
}

function isJson(text) {
  if (!text) return false;
  const t = text.trim();
  return t.startsWith("{") || t.startsWith("[");
}

function filterJson(text) {
  try {
    const obj = JSON.parse(text);
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) return text;
    const keep = new Set(["video","sites","lives","parses","rules","spider","wallpaper","livePlayHeaders","md5","name","homeSite","homeLogo","homeBg","homeSearch","homeRec","searchable"]);
    const filtered = {};
    for (const k of Object.keys(obj)) if (keep.has(k)) filtered[k] = obj[k];
    return Object.keys(filtered).length ? JSON.stringify(filtered, null, 2) : JSON.stringify(obj, null, 2);
  } catch { return text; }
}

function absolutizeJson(text, baseUrl) {
  if (!baseUrl) return text;
  try {
    const obj = JSON.parse(text);
    const base = baseUrl.replace(/\/[^/]*$/, "/");
    const topFields = ["spider","wallpaper","homeLogo","homeBg","homeSite"];
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      for (const f of topFields) if (obj[f] && !/^https?:\/\//.test(obj[f])) obj[f] = base + obj[f];
      if (Array.isArray(obj.sites)) {
        for (const s of obj.sites) {
          if (s.ext && !/^https?:\/\//.test(s.ext)) s.ext = base + s.ext;
          if (s.jar && !/^https?:\/\//.test(s.jar)) s.jar = base + s.jar;
        }
      }
    }
    return JSON.stringify(obj, null, 2);
  } catch { return text; }
}

// ===== 字节/字符串辅助 =====
function hex2bin(hex) {
  let s = "";
  for (let i = 0; i < hex.length; i += 2) s += String.fromCharCode(parseInt(hex.slice(i, i+2), 16));
  return s;
}
function hex2bytes(hex) {
  const arr = [];
  for (let i = 0; i < hex.length; i += 2) arr.push(parseInt(hex.slice(i, i+2), 16));
  return new Uint8Array(arr);
}
function str2bytes(s) { return new Uint8Array([...s].map(c => c.charCodeAt(0) & 0xFF)); }
function bytes2str(bytes) { return new TextDecoder("utf-8").decode(bytes); }
function padRight(s, ch, len) { return s.length >= len ? s.slice(0, len) : s + ch.repeat(len - s.length); }

// ===== 2423 解密 =====
function tryDecrypt2423Hex(stripped) {
  const idx2423 = stripped.indexOf("2423");
  const idx2324 = stripped.indexOf("2324");
  const keyHex = stripped.slice(idx2423 + 4, idx2324);
  let keyRaw;
  try { keyRaw = hex2bin(keyHex); } catch { keyRaw = keyHex; }
  const keyStr = padRight(keyRaw, "\0", 16);
  const dataStart = idx2324 + 4;
  const contentRstrip = stripped.replace(/\s+$/, "");
  const tsHex = contentRstrip.slice(-26);
  let tsBytes;
  try { tsBytes = hex2bytes(tsHex); } catch { tsBytes = str2bytes(tsHex); }
  const ivStr = padRight(bytes2str(tsBytes), "\0", 16);
  const keyBytes = str2bytes(keyStr.slice(0, 16));
  const ivBytes = str2bytes(ivStr.slice(0, 16));
  const dataHex = stripped.slice(dataStart, stripped.length - 26);
  const cipherBytes = hex2bytes(dataHex);
  return window.AES128.decryptCBC(cipherBytes, keyBytes, ivBytes);
}

function tryDecrypt2423Plain(stripped) {
  const idx2324 = stripped.indexOf("2324");
  const pDoll = stripped.indexOf("$#");
  const pSharp = stripped.indexOf("#$");
  let dataHex = stripped.slice(idx2324 + 4, pDoll).replace(/[^0-9a-fA-F]/gi, "");
  if (dataHex.length % 2) dataHex = dataHex.slice(0, -1);
  const key = padRight(stripped.slice(pDoll + 2, pSharp), "\0", 16);
  const iv = padRight(stripped.slice(-13), "\0", 16);
  const keyBytes = str2bytes(key.slice(0, 16));
  const ivBytes = str2bytes(iv.slice(0, 16));
  const cipherBytes = hex2bytes(dataHex);
  return window.AES128.decryptCBC(cipherBytes, keyBytes, ivBytes);
}

// ===== 递归解密（核心）=====
function findResult(rawText, rawBytes, depth) {
  if ((depth || 0) > 5) return rawText || "";

  let content = rawText || "";
  if (!content && rawBytes) content = bytes2str(rawBytes);

  // 1. 已经是 JSON
  if (isJson(content)) return content;

  // 2. 图片壳 **
  if (rawBytes) {
    const marker = new TextEncoder().encode("**");
    let starIdx = -1;
    for (let i = 8; i < rawBytes.length - 1; i++) {
      if (rawBytes[i] === marker[0] && rawBytes[i+1] === marker[1]) { starIdx = i; break; }
    }
    if (starIdx >= 8) {
      let b64Start = starIdx + 2;
      let b64Bytes = [];
      for (let i = b64Start; i < rawBytes.length; i++) {
        const c = rawBytes[i];
        if ((c >= 65 && c <= 90) || (c >= 97 && c <= 122) || (c >= 48 && c <= 57) || c === 43 || c === 47 || c === 61) b64Bytes.push(c);
        else if (c === 9 || c === 10 || c === 13 || c === 32) continue;
        else break;
      }
      try {
        const b64 = bytes2str(new Uint8Array(b64Bytes));
        const dec = atob(b64);
        return findResult(dec, null, (depth||0) + 1);
      } catch {}
    }
  }

  // 3. 2423 壳
  const stripped = collapseWhitespace(content).trim();
  const hasDelim = stripped.includes("$#") && stripped.includes("#$");
  const has2423 = stripped.startsWith("2423") && stripped.includes("2324");

  if (stripped.startsWith("2423") && (hasDelim || has2423)) {
    try {
      const dec = tryDecrypt2423Hex(stripped);
      return findResult(bytes2str(dec), dec, (depth||0) + 1);
    } catch {}
    try {
      const dec = tryDecrypt2423Plain(stripped);
      return findResult(bytes2str(dec), dec, (depth||0) + 1);
    } catch {}
  }

  // 4. 纯 base64
  const clean = stripped.replace(/\s/g, "");
  if (/^[A-Za-z0-9+/=]+$/.test(clean) && clean.length > 50) {
    try {
      const dec = atob(clean);
      if (isJson(dec)) return dec;
      return findResult(dec, null, (depth||0) + 1);
    } catch {}
  }

  return content;
}

window.TVBoxParser = { findResult, filterJson, absolutizeJson, isJson };
