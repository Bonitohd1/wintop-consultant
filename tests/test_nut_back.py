"""Phép thử Wintop 13/10/2026: nút Back của điện thoại/Zalo không được THOÁT app.
Chị Thúy báo: bấm "Xem" PDF ở mục Tài liệu rồi "ko back lại dc". Đo thật bằng WebKit trên bản cũ: Back -> trang về about:blank (thoát hẳn app).
Dùng: python tests/test_nut_back.py [thư-mục-wintop-consultant]   (chạy trên bản cũ phải ĐỎ)
Chặn mọi lời gọi ra ngoài (kể cả pdf.js) nên không ghi gì lên máy chủ thật; khung PDF hiện thông báo "cần mạng" nhưng vẫn là lớp phủ có nút Quay lại.
"""
import sys, os, shutil, tempfile, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = tempfile.mkdtemp()
for it in os.listdir(SRC):
    if it in ('.git', 'tests', 'node_modules') or it.startswith('index.backup'):
        continue
    sp = os.path.join(SRC, it)
    (shutil.copytree if os.path.isdir(sp) else shutil.copy)(sp, os.path.join(d, it))


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/'
res = []


def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)))


def fresh(ctx, errs):
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
    pg.goto(URL); pg.wait_for_timeout(2500)
    return pg


with sync_playwright() as p:
    for eng in ('chromium', 'webkit'):
        b = getattr(p, eng).launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 760}, is_mobile=True, has_touch=True)
        errs = []
        T = lambda s: f'[{eng}] ' + s
        pg = fresh(ctx, errs)
        pg.evaluate("setTab('docs')"); pg.wait_for_timeout(500)
        pg.locator("button:has-text('Xem')").first.click(); pg.wait_for_timeout(600)
        check(T('bấm Xem: lớp phủ trình đọc PDF mở'), pg.evaluate("document.getElementById('ovl').innerHTML.length>0"))
        btn = pg.evaluate("(()=>{const b=document.querySelector('#ovl button');const r=b.getBoundingClientRect();return [r.x,r.y,r.width,r.height]})()")
        check(T('nút Quay lại nằm trong màn hình'), 0 <= btn[0] and btn[0] + btn[2] <= 390 and 0 <= btn[1] and btn[1] + btn[3] <= 760, btn)
        check(T('có nút "✕ Đóng" luôn thấy ở góc dưới'), pg.evaluate("[...document.querySelectorAll('#ovl button')].some(b=>b.textContent.indexOf('Đóng')>=0)"))
        check(T('trang không tràn ngang'), pg.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        pg.go_back(); pg.wait_for_timeout(500)
        check(T('Back khi đang đọc PDF: đóng lớp phủ, KHÔNG thoát app'), pg.url.startswith(URL) and pg.evaluate("document.getElementById('ovl').innerHTML.length")==0 and pg.evaluate("S.tab")=='docs', pg.url)
        pg.go_back(); pg.wait_for_timeout(600)
        check(T('Back lần nữa: về Trang chủ, vẫn trong app'), pg.url.startswith(URL) and pg.evaluate("S.tab")=='home', (pg.url, pg.evaluate("S.tab")))

        pg2 = fresh(ctx, errs)
        pg2.evaluate("setTab('docs')"); pg2.wait_for_timeout(500)
        pg2.locator("button:has-text('Xem')").first.click(); pg2.wait_for_timeout(500)
        pg2.locator("#ovl button", has_text='Quay lại').first.click(); pg2.wait_for_timeout(500)
        check(T('nút "‹ Quay lại" đóng được, vẫn ở Tài liệu'), pg2.evaluate("document.getElementById('ovl').innerHTML.length")==0 and pg2.evaluate("S.tab")=='docs' and pg2.url.startswith(URL))
        pg2.go_back(); pg2.wait_for_timeout(500)
        check(T('sau khi đóng bằng nút, Back vẫn về Trang chủ (không kẹt mục lịch sử thừa)'), pg2.url.startswith(URL) and pg2.evaluate("S.tab")=='home', (pg2.url, pg2.evaluate("S.tab")))

        pg3 = fresh(ctx, errs)
        pg3.evaluate("setTab('tuvan')"); pg3.evaluate("setTab('sanpham')"); pg3.wait_for_timeout(300)
        pg3.go_back(); pg3.wait_for_timeout(400)
        check(T('Tư vấn -> Sản phẩm rồi Back: về Tư vấn'), pg3.evaluate("S.tab")=='tuvan', pg3.evaluate("S.tab"))
        check(T('không lỗi JS'), not errs, errs)
        b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if all(res) else 1)
