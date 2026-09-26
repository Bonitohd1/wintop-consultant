/* Wintop Consultant — Service Worker (online-first + cache offline) */
var CACHE = "wintop-v39";
var CORE = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", function(e){ self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(CORE).catch(function(){}); })); });
self.addEventListener("activate", function(e){ e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.map(function(k){ if(k!==CACHE) return caches.delete(k); })); })); self.clients.claim(); });
self.addEventListener("fetch", function(e){
  if(e.request.method!=="GET") return;
  // Âm thanh / video (bài nghe đào tạo) KHÔNG đi qua SW: trình duyệt gửi yêu cầu từng đoạn (Range) — Safari/iPhone
  // phát lỗi khi SW trả lời thay; và file vài MB không nên nhét vào bộ nhớ đệm của máy PG.
  var d=e.request.destination;
  if(d==="audio"||d==="video"||e.request.headers.has("range")) return;
  e.respondWith(
    fetch(e.request).then(function(res){
      var cp=res.clone(); caches.open(CACHE).then(function(c){ c.put(e.request, cp).catch(function(){}); });
      return res;
    }).catch(function(){ return caches.match(e.request).then(function(m){ return m || caches.match("./index.html"); }); })
  );
});
