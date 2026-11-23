// Language School Shorts · 서비스 워커
// 전략: "네트워크 먼저" — 인터넷이 되면 항상 서버의 최신 파일을 쓰고(그래서 업데이트가 바로 적용돼요),
// 안 되면 마지막으로 받아 둔 파일로 실행해요(오프라인 지원).
const CACHE = "ls-shorts";
const CORE = ["./", "index.html", "manifest.webmanifest", "data/version.json", "data/cards.json", "data/extras.json",
              "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "icons/favicon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const font = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!sameOrigin && !font) return;

  e.respondWith(
    fetch(req)
      .then(res => {
        if (res.ok || res.type === "opaque"){
          const copy = res.clone();
          // ?v=버전 이 붙은 주소도 같은 칸에 저장해서 오래된 사본이 쌓이지 않게 함
          const key = sameOrigin ? new Request(url.origin + url.pathname) : req;
          caches.open(CACHE).then(c => c.put(key, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req, {ignoreSearch: true})
        .then(hit => hit || (req.mode === "navigate" ? caches.match("index.html") : Response.error())))
  );
});
