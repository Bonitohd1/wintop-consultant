/* Wintop Consultant — Service Worker (online-first + cache offline) */
var CACHE = "wintop-v13";
var CORE = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", function(e){ self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(CORE).catch(function(){}); })); });
self.addEventListener("activate", function(e){ e.waitUntil(caches.keys().then(function(ks){ return Promise.all(ks.map(function(k){ if(k!==CACHE) return caches.delete(k); })); })); self.clients.claim(); });
self.addEventListener("fetch", function(e){
  if(e.request.method!=="GET") return;
  e.respondWith(
    fetch(e.request).then(function(res){
      var cp=res.clone(); caches.open(CACHE).then(function(c){ c.put(e.request, cp).catch(function(){}); });
      return res;
    }).catch(function(){ return caches.match(e.request).then(function(m){ return m || caches.match("./index.html"); }); })
  );
});
