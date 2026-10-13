"""Phép thử service worker Wintop (13/10/2026): ảnh / tệp phụ KHÔNG BAO GIỜ được thay bằng index.html.
 TỪNG SAI (soi trên web thật): ảnh tải chậm / hỏng nhận về index.html (592 KB, content-type html) -> ảnh vỡ trên điện thoại PG.
 · ảnh mạng treo > 4 giây, chưa có trong bộ nhớ đệm -> phải CHỜ và nhận ĐÚNG ảnh, không phải HTML
 · ảnh mất kết nối, chưa lưu -> lỗi mạng (TypeError), không phải HTML
 · mở trang khi mất mạng -> vẫn ra index.html đã lưu (đúng mục đích offline)
Dùng: python tests/test_sw_wintop.py [thư mục chứa sw.js]   (bản cũ phải ĐỎ)"""
import sys, os, threading, http.server, socketserver, functools, shutil, tempfile, time, struct, zlib
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWSRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, 'sw.js')
d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'assets'))
shutil.copy(SWSRC, os.path.join(d, 'sw.js'))
open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write('<!doctype html><title>t</title><body>TRANG-GOC<script>navigator.serviceWorker.register("sw.js")</script>')
for f in ('manifest.json', 'icon-192.png', 'icon-512.png'):
    shutil.copy(os.path.join(REPO, f), os.path.join(d, f))


def png():
    raw = b'\x00\xff\x00\x00\xff'
    c = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + c(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + c(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + c(b'IEND', b'')


PNG = png()


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith('/assets/slow.png'):
            time.sleep(5.5)
            self.send_response(200); self.send_header('Content-Type', 'image/png'); self.send_header('Content-Length', str(len(PNG))); self.end_headers(); self.wfile.write(PNG); return
        if self.path.startswith('/assets/dead.png'):
            self.connection.close(); return
        return super().do_GET()


class S(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True; allow_reuse_address = True


srv = S(('127.0.0.1', 0), functools.partial(H, directory=d)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{port}'
res = []


def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)[:250]))


with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); pg = ctx.new_page()
    pg.goto(BASE + '/index.html')
    pg.evaluate("navigator.serviceWorker.ready.then(()=>1)"); pg.wait_for_timeout(800)
    pg.reload(); pg.wait_for_timeout(1200)
    check('service worker đã nhận quyền điều khiển trang', pg.evaluate("!!navigator.serviceWorker.controller"))
    js = """async (u)=>{ try{ const r=await fetch(u,{cache:'no-store'}); const t=r.headers.get('content-type')||''; const n=(await r.blob()).size; return {ok:r.ok,ct:t,n}; }catch(e){ return {err:String(e).slice(0,60)} } }"""
    t0 = time.time(); r = pg.evaluate(js, '/assets/slow.png'); dt = time.time() - t0
    check('ảnh mạng treo 5,5 giây: chờ rồi nhận ĐÚNG ảnh (không phải index.html)', r.get('ct', '').startswith('image/png') and r.get('n') == len(PNG), (r, round(dt, 1)))
    r = pg.evaluate(js, '/assets/dead.png')
    check('ảnh mất kết nối, chưa lưu: báo lỗi mạng, KHÔNG trả HTML', 'err' in r or not r.get('ct', '').startswith('text/html'), r)
    ctx.set_offline(True)
    r = pg.evaluate("""async()=>{ try{ const r=await fetch('/index.html',{cache:'no-store'}); return {ok:r.ok, t:(await r.text()).includes('TRANG-GOC')} }catch(e){ return {err:String(e)} } }""")
    check('mất mạng: tệp index.html đã lưu vẫn trả được (offline vẫn dùng được app)', r.get('ok') and r.get('t'), r)
    pg2 = ctx.new_page()
    try:
        pg2.goto(BASE + '/index.html'); ok = 'TRANG-GOC' in pg2.content()
    except Exception as e:
        ok = False
    check('mất mạng: MỞ TRANG vẫn ra bản đã lưu', ok)
    b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if all(res) else 1)
