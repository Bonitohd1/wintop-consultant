/* Wintop Consultant — Service Worker (online-first + cache offline) */
var CACHE = "wintop-v50";
var CORE = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", function(e){ self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(CORE).catch(function(){}); })); });
self.addEventListener("activate", function(e){ e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.map(function(k){ if(k!==CACHE) return caches.delete(k); })); })); self.clients.claim(); });
self.addEventListener("fetch", function(e){
  if(e.request.method!=="GET") return;
  // Âm thanh / video (bài nghe đào tạo) KHÔNG đi qua SW: trình duyệt gửi yêu cầu từng đoạn (Range) — Safari/iPhone
  // phát lỗi khi SW trả lời thay; và file vài MB không nên nhét vào bộ nhớ đệm của máy PG.
  var d=e.request.destination;
  if(d==="audio"||d==="video"||e.request.headers.has("range")) return;
  /* network-first CÓ TIMEOUT 4 giây: mạng treo thì dùng bản đã lưu (trước: chờ tới khi mạng báo lỗi). Chỉ lưu phản hồi 200. */
  e.respondWith(new Promise(function(resolve){
    var done=false;
    /* Chỉ TRANG (navigate) mới được thay bằng index.html khi mất mạng. Ảnh / script / tệp khác mà trả index.html thì thành ảnh hỏng. */
    var isNav=(e.request.mode==="navigate");
    var fromCache=function(){ return caches.match(e.request).then(function(m){ return m || (isNav?caches.match("./index.html"):undefined); }); };
    var timer=setTimeout(function(){ fromCache().then(function(m){ if(m&&!done){ done=true; resolve(m); } }); }, 4000);
    fetch(e.request).then(function(res){
      clearTimeout(timer);
      if(res&&res.ok){ var cp=res.clone(); caches.open(CACHE).then(function(c){ c.put(e.request, cp).catch(function(){}); }); }
      if(!done){ done=true; resolve(res); }
    }).catch(function(){
      clearTimeout(timer);
      fromCache().then(function(m){ if(!done){ done=true; resolve(m||Response.error()); } });
    });
  }));
});
