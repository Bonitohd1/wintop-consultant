"""Phép thử phản hồi khách 09/10 cho App Sale Wintop. Chạy trên BẢN SAO cục bộ, MỌI lời gọi api.wintop.vn bị chặn và trả giả (KHÔNG ghi vào máy chủ thật).
Dùng: python test_wintop_fb.py <đường-dẫn-index.html>    (REV=old: chạy trên bản cũ để thấy phép thử đỏ)"""
import sys, os, json, threading, http.server, socketserver, functools, shutil, tempfile
from playwright.sync_api import sync_playwright

_ANH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_anh'); os.makedirs(_ANH, exist_ok=True)
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html')
d = tempfile.mkdtemp(); shutil.copy(SRC, os.path.join(d, 'index.html'))
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{port}/index.html'
res = []
def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)))

CALLS = []
MODE = {'v': 'ok'}
KIDS = [{'id': 'srv-in', 'name': 'In', 'dob': '2021-01-10', 'gender': 'M', 'preterm_weeks': None, 'consent_v': 'v2', 'measures': [
            {'id': 'm1', 'date': '2026-09-01', 'weight': 21.5, 'height': 116, 'source': 'consult', 'measured_by': 'do'}]},
        {'id': 'srv-na', 'name': 'Na', 'dob': '2024-02-20', 'gender': 'F', 'preterm_weeks': None, 'consent_v': 'v2', 'measures': []}]

with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(390, 844), (320, 640)]:
        ctx = b.new_context(viewport={'width': w, 'height': h}, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        def api(route, req):
            CALLS.append((req.method, req.url[-40:]))
            if '/growth/lookup' in req.url:
                if MODE['v'] == '404': return route.fulfill(status=404, content_type='application/json', body='{"detail":"x"}')
                if MODE['v'] == '500': return route.fulfill(status=500, content_type='application/json', body='{"detail":"loi"}')
                return route.fulfill(status=200, content_type='application/json', body=json.dumps({'children': KIDS}))
            return route.fulfill(status=200, content_type='application/json', body='{}')
        pg.route('https://api.wintop.vn/**', api)
        pg.route('**/fonts.googleapis.com/**', lambda r: r.abort()); pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
        pg.goto(URL); pg.wait_for_timeout(2500)
        T = lambda s: f'[{w}x{h}] ' + s
        pg.evaluate("""()=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';document.querySelectorAll('.overlay,.modal,#tour').forEach(e=>e.remove())}""")
        # --- 1) câu xin đồng ý ---
        pg.evaluate("localStorage.setItem('wt_seen_guide','1'); S.tab='tuvan'; S.step=1; render()")
        pg.wait_for_timeout(400)
        txt = pg.evaluate("document.getElementById('view').innerText")
        check(T('câu xin đồng ý nêu lý do theo dõi biểu đồ tăng trưởng + đánh giá hiệu quả dinh dưỡng'),
              'theo dõi biểu đồ tăng trưởng' in txt and 'đánh giá hiệu quả của tình trạng dinh dưỡng' in txt, txt[:300])
        check(T('câu xin đồng ý có thêm mục đích "chăm sóc và nhắc lịch cân đo" (khách chốt 10/10)'), 'chăm sóc và nhắc lịch cân đo' in txt)
        check(T('câu xin đồng ý KHÔNG hứa "ưu đãi / khuyến mại" (NĐ 100 với sữa trẻ nhỏ)'), 'ưu đãi' not in txt.split('Anh/chị đồng ý')[0][-420:] and 'khuyến mại' not in txt.split('Anh/chị đồng ý')[0][-420:])
        check(T('mã phiên bản câu đồng ý đã đổi (v4)'), pg.evaluate("CONSENT_V") == 'v4-2026-10-10', pg.evaluate("CONSENT_V"))
        # --- 2) tab Tăng trưởng, chưa có bé: vẫn có ô tìm ---
        pg.evaluate("localStorage.removeItem('nt_babies');localStorage.removeItem('nt_measures'); S.tab='growth'; render()")
        pg.wait_for_timeout(300)
        check(T('chưa có bé nào: vẫn có ô tìm theo SĐT'), pg.evaluate("!!document.getElementById('gq')"))
        # --- 3) dữ liệu: 2 bé cùng SĐT + 1 bé SĐT khác ---
        pg.evaluate("""()=>{ saveBabies([{id:'B1',ten:'In',ngaySinh:'2021-01-10',gioiTinh:'Trai',phone:'0912345678'},{id:'B2',ten:'Na',ngaySinh:'2024-02-20',gioiTinh:'Gái',phone:'0912345678'},{id:'B3',ten:'Tí',ngaySinh:'2023-05-05',gioiTinh:'Trai',phone:'0987654321'}]);
          saveMeasures([{id:'M1',babyId:'B1',ngayDo:'2026-09-01',canNang:21.5,chieuCao:116,ng:'do'},{id:'M2',babyId:'B2',ngayDo:'2026-09-01',canNang:12.8,chieuCao:90,ng:'do'},{id:'M3',babyId:'B3',ngayDo:'2026-09-01',canNang:14,chieuCao:98,ng:'do'}]);
          S.growth.baby='B3'; S.tab='growth'; render(); }""")
        pg.wait_for_timeout(300)
        check(T('có ô tìm + nút Tìm; ô nhập cao >= 40px'), pg.evaluate("(()=>{const i=document.getElementById('gq');const b=i&&i.parentElement.querySelector('button');return !!i&&!!b&&i.getBoundingClientRect().height>=38&&b.getBoundingClientRect().height>=38})()"))
        # gõ SĐT sai
        CALLS.clear(); pg.fill('#gq', '12345'); pg.click('#gq ~ button')
        pg.wait_for_timeout(200)
        check(T('SĐT sai: báo rõ, không gọi máy chủ'), 'chưa đúng' in pg.evaluate("document.getElementById('gqres').innerText") and not any('/growth/lookup' in c[1] for c in CALLS), CALLS)
        # SĐT đúng, máy KHÔNG có mã NPP -> chỉ tìm trên máy, ra 2 bé
        pg.fill('#gq', '0912 345 678'); pg.click('#gq ~ button'); pg.wait_for_timeout(300)
        res_txt = pg.evaluate("document.getElementById('gqres').innerText")
        chips = pg.evaluate("[...document.querySelectorAll('#gqres .gchip')].map(e=>e.innerText.trim())")
        check(T('1 SĐT ra 2 bé (In, Na), có ghi chú máy chưa nhập mã NPP'), len(chips) == 2 and any('In' in c for c in chips) and 'mã kích hoạt NPP' in res_txt, (chips, res_txt))
        check(T('gõ SĐT KHÔNG làm ô nhập mất nội dung / không vẽ lại cả màn'), pg.input_value('#gq') == '0912 345 678')
        # chọn bé In -> biểu đồ của In
        pg.click('#gqres .gchip:has-text("In")'); pg.wait_for_timeout(500)
        name = pg.evaluate("(document.querySelector('.gr-name')||{}).innerText")
        check(T('chọn bé "In" -> hiện biểu đồ của In'), name == 'In' and pg.evaluate("!!document.querySelector('svg.gchart')"), name)
        check(T('sau khi chọn, ô tìm vẫn giữ SĐT và chip bé đang xem được tô sáng'), pg.input_value('#gq') == '0912 345 678' and pg.evaluate("[...document.querySelectorAll('#gqres .gchip.on')].map(e=>e.innerText).join('').includes('In')"))
        # nhận định chỉ so với chuẩn WHO
        gtxt = pg.evaluate("document.getElementById('view').innerText")
        check(T('nhận định chỉ nói so với chuẩn WHO, không còn "bạn cùng tuổi / hầu hết"'), 'chuẩn WHO' in gtxt and 'bạn cùng tuổi' not in gtxt and 'hầu hết' not in gtxt and 'trẻ cùng tuổi' not in gtxt, gtxt[:600])
        # --- 4) có mã NPP: hỏi máy chủ ---
        pg.evaluate("localStorage.setItem('wt_npp_token',JSON.stringify('TEST-TOKEN'))")
        CALLS.clear(); MODE['v'] = 'ok'
        pg.evaluate("S.growth.q='0900000001'; render()"); pg.wait_for_timeout(200)
        pg.click('#gq ~ button'); pg.wait_for_timeout(900)
        check(T('có mã NPP: gọi /growth/lookup đúng 1 lần (máy chủ giả)'), sum('/growth/lookup' in c[1] for c in CALLS) == 1, CALLS)
        chips = pg.evaluate("[...document.querySelectorAll('#gqres .gchip')].map(e=>e.innerText.trim())")
        check(T('bé lấy từ hệ thống hiện ra theo SĐT đó'), len(chips) == 2 and any('In' in c for c in chips), chips)
        MODE['v'] = '404'; pg.evaluate("S.growth.q='0900000002'; render()"); pg.click('#gq ~ button'); pg.wait_for_timeout(700)
        t4 = pg.evaluate("document.getElementById('gqres').innerText")
        check(T('máy chủ cũ (404): nói rõ "chưa bật lưu hồ sơ bé", không báo "chưa có bé"'), 'chưa bật lưu hồ sơ bé' in t4 and 'chưa có hồ sơ bé nào' not in t4, t4)
        MODE['v'] = '500'; pg.evaluate("S.growth.q='0900000003'; render()"); pg.click('#gq ~ button'); pg.wait_for_timeout(700)
        t5 = pg.evaluate("document.getElementById('gqres').innerText")
        check(T('máy chủ lỗi 500: báo "chưa tải được", KHÔNG báo "chưa có hồ sơ bé"'), 'Chưa tải được' in t5 and 'chưa có hồ sơ bé nào' not in t5, t5)
        MODE['v'] = 'empty'
        pg.evaluate("KIDS_BAK=1")
        # --- 5) không tràn ngang ---
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check(T('không tràn ngang'), sw <= w, sw)
        check(T('không lỗi JS'), not errs, errs)
        if w == 390: pg.screenshot(path=os.path.join(_ANH, 'fb_growth_search.png'))
        ctx.close()
    b.close()
print('TỔNG', sum(res), '/', len(res)); srv.shutdown(); sys.exit(0 if all(res) else 1)
