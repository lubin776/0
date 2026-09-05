// 在 parse() 的 fetch 成功后加上：
const triedUAs = resp.headers.get("X-Tried-UAs");
if (triedUAs) log(`使用的 UA: ${triedUAs}`, "info");
