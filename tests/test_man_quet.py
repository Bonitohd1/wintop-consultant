"""Phép thử màn quét BIO-SCAN của Wintop (10/10/2026). Dùng: python test_wintop_scan.py <thư-mục-wintop-consultant> (BẢN CŨ phải đỏ).
Mọi lời gọi api.wintop.vn bị chặn và trả giả — KHÔNG ghi gì vào máy chủ thật."""
import sys, os, json, threading, http.server, socketserver, functools, shutil, tempfile, time
from playwright.sync_api import sync_playwright

_ANH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_anh'); os.makedirs(_ANH, exist_ok=True)
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = tempfile.mkdtemp()
for it in os.listdir(SRC):
    if it in ('.git', 'tests'):
        continue
    sp = os.path.join(SRC, it)
    (shutil.copytree if os.path.isdir(sp) else shutil.copy)(sp, os.path.join(d, it))


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{srv.server_address[1]}/index.html'
res = []


def check(n, ok, det=''):
    res.append(bool(ok))
    print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)))


PROBE = """()=>{const pc=document.getElementById('scanpct'),bar=document.getElementById('scanbar'),ln=document.querySelector('.scan-line'),fl=document.querySelector('.scan-fill'),mg=document.getElementById('scanmsg'),pn=document.querySelector('.scan-panel');
 const sx=bar&&/scaleX\\(([\\d.]+)\\)/.exec(bar.style.transform||''),ty=ln&&/translateY\\(([\\d.-]+)px\\)/.exec(ln.style.transform||''),sy=fl&&/scaleY\\(([\\d.]+)\\)/.exec(fl.style.transform||'');
 return {st:S.scanState,run:!!S._scanRun,pct:pc?pc.textContent:null,bar:sx?parseFloat(sx[1]):null,line:ty?parseFloat(ty[1]):null,fill:sy?parseFloat(sy[1]):null,msg:mg?mg.textContent:null,done:pn?pn.classList.contains('done'):false,step:S.step}}"""


def new_page(b, reduced=False, size=(390, 844), settle=2500):
    ctx = b.new_context(viewport={'width': size[0], 'height': size[1]}, is_mobile=True, has_touch=True, reduced_motion='reduce' if reduced else 'no-preference')
    pg = ctx.new_page()
    pg.errs = []
    pg.on('pageerror', lambda e: pg.errs.append(str(e)[:200]))
    pg.route('https://api.wintop.vn/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.route('**/fonts.googleapis.com/**', lambda r: r.abort()); pg.route('**/fonts.gstatic.com/**', lambda r: r.abort())
    pg.goto(URL); pg.evaluate("()=>{window.startTour=function(){};window.tourStep=function(){};}"); pg.wait_for_timeout(settle)
    pg.evaluate("""()=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';document.querySelectorAll('.overlay,.modal,#tour,#tourbd').forEach(e=>e.remove());localStorage.setItem('wt_seen_guide','1');
      window.__fc=0;var _f=window.finishConsult;window.finishConsult=function(){window.__fc++;try{return _f.apply(this,arguments);}catch(e){window.__fcerr=String(e);}};
      S.tab='tuvan';S.consent=true;S.buyer={name:'Test',phone:'0912345678',addr:'',rel:''};S.user.obj='tre_1_10';S.user.gender='Nam';S.user.name='In';S.user.dob='2021-01-10';S.m={age:4.7,w:18,h:108};S.cls=classify();S.needs=['Tăng cân'];S.step=3;render();}""")
    pg.wait_for_timeout(300)
    return ctx, pg


with sync_playwright() as p:
    b = p.chromium.launch()
    for size in [(390, 844), (360, 640)]:
        w, h = size
        T = lambda s: f'[{w}x{h}] ' + s
        ctx, pg = new_page(b, size=size)
        btn = pg.locator('button:has-text("Xem kết quả")')
        btn.click(); pg.evaluate('startScan();startScan()')   # bấm ĐÚP (nút đã biến mất sau lần 1, nên gọi thẳng hàm)
        samples = []; t0 = time.time(); shots = {1.0: 0, 2.2: 0}
        while time.time() - t0 < 6.5:
            s = pg.evaluate(PROBE); s['t'] = round(time.time() - t0, 2); samples.append(s)
            for k in shots:
                if w == 390 and not shots[k] and s['t'] >= k:
                    pg.screenshot(path=os.path.join(_ANH, f'wscan_{k}.png')); shots[k] = 1
            if s['done'] and 'col' not in shots:
                pg.wait_for_timeout(380)   # chờ hiệu ứng đổi màu 0,3 giây chạy xong (lúc vừa 'done' còn đang chuyển)
                shots['col'] = pg.evaluate("document.getElementById('scanpct')?getComputedStyle(document.getElementById('scanpct')).color:'(đã sang kết quả)'")
            if w == 390 and s['done'] and not shots.get('ok'):
                pg.screenshot(path=os.path.join(_ANH, 'wscan_ok.png')); shots['ok'] = 1
            pg.wait_for_timeout(60)
        run = [s for s in samples if s['pct'] is not None]
        pcts = [int(s['pct'].replace('%', '')) for s in run]
        check(T('% tăng đều, không giật lùi'), pcts and all(b2 >= a for a, b2 in zip(pcts, pcts[1:])), pcts[:30])
        check(T('% từ ~0 tới 100'), pcts and pcts[0] <= 3 and pcts[-1] == 100, (pcts[:3], pcts[-3:]))
        check(T('nhiều mức trung gian (mượt)'), len(set(pcts)) >= 25, len(set(pcts)))
        bars = [s['bar'] for s in run if s['bar'] is not None]
        check(T('thanh tiến độ chạy 0 → 1 đều'), bars and bars[0] <= 0.05 and bars[-1] >= 0.99 and all(b2 >= a - 1e-6 for a, b2 in zip(bars, bars[1:])), (bars[:3], bars[-3:]))
        lines = [s['line'] for s in run if s['line'] is not None]
        check(T('vạch quét đi XUỐNG theo tiến độ (không lặp vòng): tăng dần từ đầu tới chân'), lines and lines[0] <= 20 and lines[-1] >= 250 and all(b2 >= a - 0.5 for a, b2 in zip(lines, lines[1:])), (lines[:3], lines[-3:]))
        fills = [s['fill'] for s in run if s['fill'] is not None]
        check(T('vùng đã quét ngả màu dần (0 → 1)'), fills and fills[0] <= 0.05 and fills[-1] >= 0.99, (fills[:3], fills[-3:]))
        msgs = []
        for s in run:
            if s['msg'] and (not msgs or msgs[-1] != s['msg']) and s['msg']:
                msgs.append(s['msg'])
        check(T('chữ trạng thái đi qua đủ 4 chặng rồi "Hoàn tất"'), any('Đọc số đo' in m for m in msgs) and any('vi chất' in m for m in msgs) and any('WHO' in m for m in msgs) and any('Tổng hợp' in m for m in msgs) and any('Hoàn tất' in m for m in msgs), msgs)
        check(T('hoàn tất: khung đổi xanh (class done) trước khi sang kết quả'), any(s['done'] for s in samples))
        check(T('hoàn tất: số % đổi sang xanh lá (không bị style inline đè)'), shots.get('col') == 'rgb(142, 230, 160)', shots.get('col'))
        last = samples[-1]
        check(T('sau đó sang kết quả (scanState = done) và không còn khoá'), last['st'] == 'done' and not last['run'], last)
        check(T('bấm đúp: finishConsult chỉ chạy MỘT lần'), pg.evaluate('window.__fc') == 1, pg.evaluate('window.__fc'))
        check(T('không lỗi trong finishConsult / trang'), not pg.errs and not pg.evaluate('window.__fcerr'), (pg.errs, pg.evaluate('window.__fcerr')))
        sw = pg.evaluate("document.documentElement.scrollWidth")
        check(T('không tràn ngang'), sw <= w, sw)
        ctx.close()

    # ---- bấm sang tab khác giữa chừng rồi quay lại (chờ 6s cho các bộ hẹn giờ lúc mở app chạy xong — chúng tự đưa về tab Trang chủ, bản cũ cũng vậy) ----
    ctx, pg = new_page(b, settle=6000)
    pg.locator('button:has-text("Xem kết quả")').click(); pg.wait_for_timeout(900)
    pg.evaluate("S.tab='home';render()"); pg.wait_for_timeout(500); pg.evaluate("S.tab='tuvan';render()"); pg.wait_for_timeout(300)
    mid = pg.evaluate(PROBE)
    check('[rời tab giữa chừng] quay lại vẫn thấy tiến độ chạy tiếp (thanh + % đã vẽ lại ở màn mới)', mid['pct'] not in (None, '0%') and (mid['bar'] or 0) > 0.05, mid)
    pg.wait_for_function("S.scanState==='done'", timeout=8000); pg.wait_for_timeout(300)
    check('[rời tab giữa chừng] kết thúc đúng 1 lần, không lỗi', pg.evaluate('window.__fc') == 1 and not pg.errs, (pg.evaluate('window.__fc'), pg.errs))
    # quét lần thứ 2 sau khi xong (khoá phải nhả)
    pg.evaluate("S.step=3;render()"); pg.wait_for_timeout(200)
    pg.locator('button:has-text("Xem kết quả")').click(); pg.wait_for_timeout(500)
    check('[quét lần 2] khoá đã nhả, quét chạy lại được', pg.evaluate(PROBE)['st'] == 'scanning')
    pg.wait_for_function("S.scanState==='done'", timeout=8000)
    check('[quét lần 2] xong, finishConsult = 2 lần tổng cộng', pg.evaluate('window.__fc') == 2, pg.evaluate('window.__fc'))
    ctx.close()

    # ---- giảm chuyển động ----
    ctx, pg = new_page(b, reduced=True)
    t0 = time.time(); pg.locator('button:has-text("Xem kết quả")').click(); pg.wait_for_function("S.scanState==='done'", timeout=8000); dt = time.time() - t0
    check('[giảm chuyển động] quét xong < 3 giây và sang kết quả', dt < 3.0, round(dt, 2))
    check('[giảm chuyển động] không lỗi JS', not pg.errs, pg.errs)
    ctx.close()
    b.close()
print('TỔNG', sum(res), '/', len(res))
srv.shutdown()
sys.exit(0 if all(res) else 1)
