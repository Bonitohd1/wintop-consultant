"""Phép thử Wintop 13/10/2026 (đợt 3) — lỗi bị NUỐT / hiện sai trạng thái ở các màn phụ:
 · Đơn của tôi: đơn chưa về máy chủ KHÔNG được ghi "Đã ghi nhận" (TỪNG SAI: mọi đơn luôn xanh), có khung "N đơn chưa về hệ thống" + nút đồng bộ,
   máy chủ trả 500 thì đơn vẫn "Chờ đồng bộ", trả 200 thì đổi thành "Đã đồng bộ" ngay trên màn
 · NPP cấp dưới + Đơn cấp dưới đặt lên: lỗi 401/500 phải hiện LỖI + nút Thử lại, KHÔNG được hiện "Chưa có …" như lúc thật sự rỗng
 · Lỗi 422 (detail là mảng) không hiện "[object Object]"
 · Giới tính không đặt sẵn "Nam": bỏ qua là không đi tiếp được (bé gái bị tính theo chuẩn WHO bé trai)
 · Bóng thoại mascot không tràn khỏi mép màn 320px
Mọi request ra ngoài bị chặn; api.wintop.vn là bản giả (có header CORS cho WebKit).
Dùng: python tests/test_man_phu_wintop.py [index.html]   (chạy trên bản cũ phải ĐỎ)"""
import sys, os, json, threading, http.server, socketserver, functools, shutil, tempfile
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(REPO, 'index.html')
d = tempfile.mkdtemp(); shutil.copy(SRC, os.path.join(d, 'index.html'))
for extra in ('manifest.json', 'icon-192.png', 'icon-512.png'):
    if os.path.exists(os.path.join(REPO, extra)): shutil.copy(os.path.join(REPO, extra), os.path.join(d, extra))


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{port}/index.html'
res = []
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'}


def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)[:300]))


API = {}   # đoạn đường dẫn -> (status, body)


def route(r):
    u = r.request.url
    if u.startswith('http://127.0.0.1'): return r.continue_()
    if 'api.wintop.vn' in u:
        if r.request.method == 'OPTIONS': return r.fulfill(status=204, headers=CORS)
        for k, (st, body) in API.items():
            if k in u: return r.fulfill(status=st, content_type='application/json', body=json.dumps(body), headers=CORS)
        return r.fulfill(status=200, content_type='application/json', body='{}', headers=CORS)
    return r.abort()


ORDER = {'sku': 'ba', 'name': 'Wintop BA', 'qty': 12, 'unitLabel': 'thùng', 'unitCount': 1, 'price': 0, 'amount': 0, 'area': 'HN', 'pg': 'PG A', 'at': 1700000000000, 'sent': False}

with sync_playwright() as p:
    for eng in ('chromium', 'webkit'):
        b = getattr(p, eng).launch()
        T = lambda s: f'[{eng}] ' + s
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        errs = []
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:200])); pg.route('**/*', route)
        pg.goto(URL); pg.wait_for_timeout(1500)
        pg.evaluate("""()=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';localStorage.setItem('wt_seen_guide','1');localStorage.setItem('wt_tenant','NPP-TEST');window.confirm=function(){return true}}""")
        view = lambda: pg.evaluate("document.getElementById('view').innerText")
        ovl = lambda: pg.evaluate("(document.getElementById('ovl')||{}).innerText||''")

        # ---- Đơn của tôi
        API.clear(); API['/orders'] = (500, {'detail': 'Lỗi máy chủ'}); API['order'] = (500, {'detail': 'Lỗi máy chủ'})
        pg.evaluate("(o)=>{localStorage.setItem('wt_order_queue',JSON.stringify([o,Object.assign({},o,{id:'daSent',sent:true,sentAt:1})]));tabTo('orders');render()}", ORDER)
        pg.wait_for_timeout(300)
        v = view()
        check(T('đơn chưa đồng bộ hiện "Chờ đồng bộ" + khung "1 đơn chưa về hệ thống" + nút Đồng bộ; đơn đã gửi hiện "Đã đồng bộ"'),
              'Chờ đồng bộ' in v and '1 đơn chưa về hệ thống' in v and 'Đồng bộ đơn' in v and 'Đã đồng bộ' in v, v[:300])
        check(T('KHÔNG còn nhãn "Đã ghi nhận" cho đơn chưa về máy chủ'), 'Đã ghi nhận' not in v, v[:200])
        pg.evaluate("flushOrders(false)"); pg.wait_for_timeout(1200)
        v = view()
        q = pg.evaluate("JSON.parse(localStorage.getItem('wt_order_queue')).map(o=>!!o.sent)")
        check(T('máy chủ trả 500: đơn vẫn chờ đồng bộ (không bị đánh dấu đã gửi), khung cảnh báo còn'), q == [False, True] and '1 đơn chưa về hệ thống' in v, (q, v[:200]))
        API.clear(); API['order'] = (200, {'ok': True}); API['/orders'] = (200, {'ok': True})
        pg.evaluate("flushOrders(false)"); pg.wait_for_timeout(1500)
        v = view()
        q = pg.evaluate("JSON.parse(localStorage.getItem('wt_order_queue')).map(o=>!!o.sent)")
        check(T('máy chủ trả 200: màn Đơn tự đổi thành "Đã đồng bộ", khung cảnh báo biến mất'), q == [True, True] and 'chưa về hệ thống' not in v and v.count('Đã đồng bộ') == 2, (q, v[:250]))

        # ---- NPP cấp dưới
        API.clear(); API['/npp/children'] = (500, {'detail': 'boom'})
        pg.evaluate("tabTo('home');render();openChildren()"); pg.wait_for_timeout(900)
        o = ovl()
        check(T('NPP cấp dưới: máy chủ 500 → báo "Không tải được" + Thử lại, KHÔNG hiện "Chưa có NPP cấp dưới"'), 'Không tải được' in o and 'Thử lại' in o and 'Chưa có NPP cấp dưới' not in o, o[:250])
        API.clear(); API['/npp/children'] = (401, {'detail': 'Thiếu mã NPP'})
        pg.evaluate("loadChildren()"); pg.wait_for_timeout(700)
        o = ovl()
        check(T('NPP cấp dưới: 401 → hiện đúng lời máy chủ, không hiện "Chưa có …"'), 'Thiếu mã NPP' in o and 'Chưa có NPP cấp dưới' not in o, o[:250])
        API.clear(); API['/npp/children'] = (200, {'items': []})
        pg.evaluate("loadChildren()"); pg.wait_for_timeout(700)
        check(T('NPP cấp dưới: 200 + danh sách rỗng → mới hiện "Chưa có NPP cấp dưới nào"'), 'Chưa có NPP cấp dưới nào' in ovl(), ovl()[:200])
        API.clear(); API['/npp/create-child'] = (422, {'detail': [{'loc': ['body', 'tenant'], 'msg': 'Mã không hợp lệ', 'type': 'x'}]})
        pg.evaluate("document.getElementById('ch_code').value='abc'; createChild()"); pg.wait_for_timeout(700)
        t = pg.evaluate("(document.getElementById('toast')||document.querySelector('.toast')||{}).innerText||''")
        check(T('tạo mã cấp dưới lỗi 422 (detail là mảng): hiện "Mã không hợp lệ", không hiện [object Object]'), 'Mã không hợp lệ' in t and 'object' not in t, t)
        pg.evaluate("closeOvl()"); pg.wait_for_timeout(600)

        # ---- Đơn cấp dưới đặt lên
        API.clear(); API['/npp/inbound-restock'] = (500, {'detail': 'boom'})
        pg.evaluate("openInbound()"); pg.wait_for_timeout(900)
        o = ovl()
        check(T('Đơn cấp dưới: máy chủ 500 → báo lỗi + Thử lại, KHÔNG hiện "Chưa có đơn nào từ cấp dưới"'), 'Không tải được' in o and 'Thử lại' in o and 'Chưa có đơn nào' not in o, o[:250])
        API.clear(); API['/npp/inbound-restock'] = (200, {'items': []})
        pg.evaluate("openInbound()"); pg.wait_for_timeout(700)
        check(T('Đơn cấp dưới: 200 + rỗng → mới hiện "Chưa có đơn nào từ cấp dưới"'), 'Chưa có đơn nào từ cấp dưới' in ovl(), ovl()[:200])
        pg.evaluate("closeOvl()"); pg.wait_for_timeout(600)

        # ---- Giới tính
        pg.evaluate("newConsult();tabTo('tuvan');render()"); pg.wait_for_timeout(300)
        g0 = pg.evaluate("S.user.gender")
        check(T('giới tính KHÔNG đặt sẵn "Nam" khi mở ca tư vấn mới'), g0 == '', g0)
        pg.evaluate("S.consent=false;S.user.obj='tre_1_10';S.user.dob='';next1()"); pg.wait_for_timeout(300)
        check(T('chưa chọn giới tính → không sang bước 2'), pg.evaluate("S.step") == 1, pg.evaluate("S.step"))
        pg.evaluate("S.user.gender='Nữ';next1()"); pg.wait_for_timeout(300)
        check(T('chọn giới tính xong → sang bước 2'), pg.evaluate("S.step") == 2, pg.evaluate("S.step"))

        # ---- Mascot ở 320px
        pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(200)
        pg.evaluate("tabTo('home');render()")
        pg.evaluate("""()=>{var q=document.getElementById('fabhi');fabHi();q.textContent='Chào bạn, em kiểm tồn kho giúp trước khi lên đơn nhé, cần gì cứ hỏi!'}""")
        pg.wait_for_timeout(500)
        L = pg.evaluate("(()=>{var r=document.getElementById('fabhi').getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),innerWidth]})()")
        check(T('bóng thoại mascot (câu dài) nằm trọn trong màn 320px'), L[0] >= 4 and L[1] <= L[2], L)
        errs[:] = [e for e in errs if 'Returned response is null' not in e and 'Response served by service worker is an error' not in e]   # catalog bị harness chặn -> SW trả lỗi mạng (đã bắt .catch); trước 13/10 SW trả index.html che lỗi
        check(T('không lỗi JS'), not errs, errs)
        pg.close(); b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if all(res) else 1)
