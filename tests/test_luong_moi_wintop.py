"""Phép thử Wintop 21/11/2026 — chống hồi quy cho các luồng mới 07–11/11 (QA WT-03) + ô SĐT người mua (QA WT-01):
  sdt   ô SĐT: bàn phím số, DÁN "0912 345 678" / "0912.345.678" / "+84 …" thành số gọn, gõ thì không nhảy con trỏ,
        rời ô / bấm Tiếp tục thì SĐT lưu vào phiên là số gọn (trước 21/11: lưu nguyên dấu cách / dấu chấm)
  csv   2 file CSV (phiên tư vấn + quản trị) vẫn mở đầu bằng dấu BOM sau khi đổi ký tự ẩn thành "\uFEFF" (QA WT-02)
  bau   ee2212b: mẹ ĐANG mang thai BMI trước thai ≥ 25 -> KHÔNG tư vấn sữa bầu, hướng dẫn hỏi bác sĩ sản khoa;
        BMI 23–24,9 là "Bình thường" (trước đó bị gán "Thừa cân"); mẹ sau sinh không bị chặn; màn ghi "25.0" thì xếp theo ngưỡng
        ≥ 25 (64 kg / 160 cm từng ra 24,999… -> "Bình thường" + vẫn gợi ý sữa bầu — vá 21/11 bằng bmi1 làm tròn 1 số)
  hoso  a102f4d: hồ sơ khách của Trợ lý lưu BỀN (qua cả tải lại trang), dải "Đang tư vấn", nút "Khách mới", gửi ho_so_be lên trợ lý
  nhap  8445a33: phiên tư vấn dở được lưu nháp, mở lại app có thẻ "Tiếp tục / Bỏ"; chốt xong thì bỏ nháp
(da01922 "HSCB 2 trang" là commit của kho tuvan.nutritie, không thuộc kho này.)
Chạy trên bản sao cục bộ, MỌI request ra ngoài bị chặn (api.wintop.vn trả giả) — KHÔNG ghi vào máy chủ thật.
Dùng: python tests/test_luong_moi_wintop.py [đường-dẫn-index.html]     PHAN=sdt|csv|bau|hoso|nhap để chạy riêng một phần.
Kiểm ngược: chạy trên index.html đã gỡ (revert) commit tương ứng -> phần đó phải ĐỎ."""
import sys, os, json, threading, http.server, socketserver, functools, shutil, tempfile
from playwright.sync_api import sync_playwright

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html')
PHAN = set(x for x in os.environ.get('PHAN', 'sdt,csv,bau,hoso,nhap').split(',') if x)
d = tempfile.mkdtemp(); shutil.copy(SRC, os.path.join(d, 'index.html'))
for extra in ('sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'):
    sp = os.path.join(os.path.dirname(SRC), extra)
    if os.path.exists(sp): shutil.copy(sp, os.path.join(d, extra))
if os.path.isdir(os.path.join(os.path.dirname(SRC), 'fonts')):   # SW v51+ nạp sẵn font; thiếu thì máy chủ tạm in lỗi 404 rác
    shutil.copytree(os.path.join(os.path.dirname(SRC), 'fonts'), os.path.join(d, 'fonts'))


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{port}/index.html'
res = []


def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)[:300]))


def route(r):
    u = r.request.url
    if u.startswith('http://127.0.0.1'): return r.continue_()
    if 'api.wintop.vn' in u:
        cors = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'}
        if r.request.method == 'OPTIONS': return r.fulfill(status=204, headers=cors)
        return r.fulfill(status=200, content_type='application/json', body='{}', headers=cors)
    return r.abort()


def open_page(ctx, errs, wipe=True):
    """wipe=True: máy mới (xoá nháp + hồ sơ trợ lý). wipe=False: GIỮ localStorage — giả Zalo tải lại trang / mở lại app."""
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.route('**/*', route)
    pg.goto(URL); pg.wait_for_timeout(1500)
    pg.evaluate("""(wipe)=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';document.querySelectorAll('.overlay,.modal,#tour,#tourbd').forEach(e=>e.remove());
      localStorage.setItem('wt_seen_guide','1');if(wipe){['wt_draft_v1','wt_asst_ho','wt_asst_v1'].forEach(k=>localStorage.removeItem(k));}
      S.tab='home';render();window.__t=[];var __o=toast;toast=function(m){__t.push(String(m));__o(m)};window.confirm=function(){return true}}""", wipe)
    pg.wait_for_timeout(300)
    return pg


def last_toast(pg):
    return pg.evaluate("__t.length?__t[__t.length-1]:''")


def paste(pg, sel, text):
    """Giả DÁN: đặt chữ rồi bắn sự kiện input kiểu insertFromPaste (đúng sự kiện trình duyệt bắn khi dán)."""
    return pg.evaluate("""([sel,t])=>{const i=document.querySelector(sel);i.focus();i.value=t;
      i.dispatchEvent(new InputEvent('input',{inputType:'insertFromPaste',data:t,bubbles:true}));return [i.value,i.selectionStart]}""", [sel, text])


def rec(pg, obj, m, hist=None, gender='Nữ', extra=None):
    return pg.evaluate("""([obj,m,hist,g,ex])=>{S.user={name:'',obj:obj,gender:g,birth:'',deliv:'',hist:hist||['Không có'],cur:''};if(ex)Object.assign(S.user,ex);
      S.buyer={name:'',phone:'',addr:'',rel:''};S.m=m;S.needs=[];S.consent=false;S.cls=classify();S.rec=buildRec();S.step=4;S.tab='tuvan';S.scanState='done';render();
      var v=document.getElementById('view');return {cls:S.cls,rec:S.rec,t:v.innerText,order:/orderFromRec/.test(v.innerHTML)}}""", [obj, m, hist, gender, extra])


PH1 = "#view input[type=tel]"   # ô SĐT người mua ở bước 1 (bước 1 chỉ có MỘT ô tel)

with sync_playwright() as p:
    for eng in ('chromium', 'webkit'):
        b = getattr(p, eng).launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, timezone_id='Asia/Ho_Chi_Minh')
        errs = []
        T = lambda s: f'[{eng}] ' + s

        # ===================== sdt: ô SĐT người mua (QA WT-01) =====================
        if 'sdt' in PHAN:
          try:
            pg = open_page(ctx, errs)
            pg.evaluate("newConsult();setConsent(true)"); pg.wait_for_timeout(200)
            at = pg.evaluate("([s])=>{const i=document.querySelector(s);return [i.getAttribute('inputmode'),i.getAttribute('autocomplete')]}", [PH1])
            check(T('ô SĐT bước 1: bàn phím số (inputmode=numeric) + gợi ý SĐT (autocomplete=tel)'), at == ['numeric', 'tel'], at)
            for raw in ('0912 345 678', '0912.345.678', '0912-345-678', '+84 912 345 678', '84912345678'):
                v = paste(pg, PH1, raw)
                st = pg.evaluate("S.buyer.phone")
                check(T(f'DÁN "{raw}": ô thành 0912345678, con trỏ ở cuối, state cùng giá trị'), v[0] == '0912345678' and v[1] == 10 and st == '0912345678', (v, st))
            v = paste(pg, PH1, 'abc')
            check(T('DÁN chữ rác "abc": giữ nguyên để PG thấy mà sửa (không xoá trắng âm thầm)'), v[0] == 'abc', v)
            # GÕ bình thường: không chuẩn hoá giữa chừng (đổi value lúc gõ làm nhảy con trỏ)
            pg.evaluate("([s])=>{const i=document.querySelector(s);i.value='';i.dispatchEvent(new Event('input',{bubbles:true}))}", [PH1])
            pg.click(PH1); pg.keyboard.type('0912 345')
            v = pg.evaluate("([s])=>{const i=document.querySelector(s);return [i.value,i.selectionStart]}", [PH1])
            check(T('GÕ "0912 345": giữ nguyên từng ký tự, con trỏ không nhảy'), v == ['0912 345', 8], v)
            pg.evaluate("([s])=>{const i=document.querySelector(s);i.setSelectionRange(4,4)}", [PH1]); pg.keyboard.type('9')
            v = pg.evaluate("([s])=>{const i=document.querySelector(s);return [i.value,i.selectionStart]}", [PH1])
            check(T('GÕ chen giữa (vị trí 4): con trỏ đứng ngay sau chữ vừa gõ'), v == ['09129 345', 5], v)
            pg.evaluate("([s])=>{const i=document.querySelector(s);i.value='0912 345 678';i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}", [PH1])
            v = pg.evaluate("([s])=>[document.querySelector(s).value,S.buyer.phone]", [PH1])
            check(T('rời ô sau khi gõ "0912 345 678": ô + state thành 0912345678'), v == ['0912345678', '0912345678'], v)
            # bấm Tiếp tục khi state còn dấu chấm (VD trình duyệt tự điền không bắn change): next1 vẫn qua và LƯU số gọn
            st = pg.evaluate("""()=>{S.step=1;S.consent=true;S.buyer={name:'An',phone:'0912.345.678',addr:'',rel:''};S.user={name:'',obj:'adult',gender:'Nam',birth:'',deliv:'',hist:[],cur:''};window.__t=[];next1();return [S.step,S.buyer.phone]}""")
            check(T('Tiếp tục với "0912.345.678": sang bước 2, SĐT lưu vào phiên là 0912345678'), st == [2, '0912345678'], (st, last_toast(pg)))
            st = pg.evaluate("""()=>{S.step=1;S.consent=true;S.buyer={name:'An',phone:'0912 345 67',addr:'',rel:''};S.user={name:'',obj:'adult',gender:'Nam',birth:'',deliv:'',hist:[],cur:''};window.__t=[];next1();return [S.step,S.buyer.phone]}""")
            check(T('SĐT thiếu số "0912 345 67": vẫn bị chặn kèm lời báo'), st[0] == 1 and 'SĐT' in last_toast(pg), (st, last_toast(pg)))
            # ô SĐT ở màn Lên đơn + ô tìm bé theo SĐT: cùng luật
            pg.evaluate("setTab('makeorder')"); pg.wait_for_timeout(200)
            sel_o = "#view input[type=tel]"
            at = pg.evaluate("([s])=>{const i=document.querySelector(s);return i?[i.getAttribute('inputmode'),i.getAttribute('autocomplete')]:null}", [sel_o])
            v = paste(pg, sel_o, '0912 345 678') if at else None
            check(T('ô SĐT màn Lên đơn: bàn phím số + dán "0912 345 678" thành 0912345678'), at == ['numeric', 'tel'] and v and v[0] == '0912345678' and pg.evaluate("S.orderBuyer.phone") == '0912345678', (at, v))
            pg.evaluate("setTab('growth')"); pg.wait_for_timeout(300)
            v = paste(pg, '#gq', '0912.345.678') if pg.evaluate("!!document.getElementById('gq')") else None
            check(T('ô tìm bé theo SĐT: dán "0912.345.678" thành 0912345678'), v and v[0] == '0912345678' and pg.evaluate("S.growth.q") == '0912345678', v)
            pg.close()
          except Exception as e:   # phần cũ thiếu hàm -> ghi SAI rồi chạy tiếp phần sau (không vỡ cả tệp)
            check(T('phần sdt: chạy hết, không vỡ giữa chừng'), False, repr(e)[:200])

        # ===================== csv: dấu BOM của file CSV (QA WT-02) =====================
        if 'csv' in PHAN:
          try:
            pg = open_page(ctx, errs)
            a = pg.evaluate("""()=>{var cap={};HTMLAnchorElement.prototype.click=function(){cap.href=this.href};S.consent=true;S.buyer={name:'An',phone:'0912345678',addr:'',rel:''};
              S.user.name='Bo';S.user.hist=['Không có'];S.user.obj='adult';S.rec={prods:[]};S.cls={};exportCSV();return decodeURIComponent((cap.href||'').split(',').slice(1).join(','))}""")
            bb = pg.evaluate("""()=>{var cap=null,o=dlBlob;dlBlob=function(b){cap=b};try{adminExportCSV()}finally{dlBlob=o}return cap}""")
            check(T('Xuất CSV phiên + CSV quản trị: bắt đầu bằng dấu BOM (Excel đọc đúng tiếng Việt)'), a[:1] == '﻿' and isinstance(bb, str) and bb[:1] == '﻿', (a[:5], (bb or '')[:5]))
            pg.close()
          except Exception as e:
            check(T('phần csv: chạy hết, không vỡ giữa chừng'), False, repr(e)[:200])

        # ===================== bau: ee2212b =====================
        if 'bau' in PHAN:
          try:
            pg = open_page(ctx, errs)
            for pw, cat in ((64, 'Thừa cân'), (70, 'Thừa cân'), (80, 'Béo phì')):
                r = rec(pg, 'pregnant', {'pw': pw, 'h': 160, 'w': pw + 5, 'week': 20})
                bmi = pw / 1.6 ** 2
                check(T(f'mẹ bầu BMI trước thai {bmi:.1f} ({cat}): DỪNG, không gợi ý sữa bầu, không nút lên đơn, chỉ hỏi bác sĩ sản khoa'),
                      r['rec']['freeze'] and r['rec']['prods'] == [] and not r['order'] and 'KHÔNG tư vấn sữa bầu' in r['t'] and 'BÁC SĨ SẢN KHOA' in r['t'] and r['cls']['cat'] == cat,
                      (r['rec'].get('title'), r['rec']['prods'], r['cls'].get('cat')))
            w = pg.evaluate("(()=>{try{return buildSessionFull().warn||''}catch(e){return 'LOI '+e.message}})()")
            check(T('phiên gửi về hệ thống ghi rõ lý do dừng (BMI trước thai ≥ 25), không ghi nhầm "tiểu đường thai kỳ"'), 'BMI' in w and 'tiểu đường' not in w, w)
            r = rec(pg, 'pregnant', {'pw': 63, 'h': 160, 'w': 68, 'week': 20})   # BMI 24,6
            check(T('mẹ bầu BMI trước thai 24,6: "Bình thường", khuyến nghị tăng 11,5–16 kg, vẫn được tư vấn (không dừng)'),
                  r['cls']['cat'] == 'Bình thường' and r['cls']['totLo'] == 11.5 and not r['rec']['freeze'], (r['cls'].get('label'), r['cls'].get('metric'), r['rec'].get('title')))
            r = rec(pg, 'pregnant', {'pw': 55, 'h': 160, 'w': 60, 'week': 20})   # BMI 21,5
            check(T('mẹ bầu BMI 21,5: vẫn gợi ý Wintop Mama như cũ (không hồi quy)'), not r['rec']['freeze'] and 'mama' in r['rec']['prods'], r['rec']['prods'])
            r = rec(pg, 'adult', {'w': 64, 'h': 160}, gender='Nam')
            check(T('người lớn 64 kg / 160 cm: màn ghi "BMI = 25.0" thì nhãn cũng theo ngưỡng ≥ 25 (Béo phì độ 1), không tụt về "Thừa cân"'),
                  r['cls']['metric'] == 'BMI = 25.0' and r['cls']['label'] == 'Béo phì độ 1', (r['cls'].get('metric'), r['cls'].get('label')))
            r = rec(pg, 'pregnant', {'w': 70, 'h': 160}, extra={'postpartum': True})   # sau sinh BMI 27,3
            check(T('mẹ SAU SINH BMI 27,3: KHÔNG áp luật dừng của mẹ bầu'), 'BMI trước' not in (r['rec'].get('title') or '') and 'KHÔNG tư vấn sữa bầu' not in r['t'], r['rec'].get('title'))
            pg.close()
          except Exception as e:   # phần cũ thiếu hàm -> ghi SAI rồi chạy tiếp phần sau (không vỡ cả tệp)
            check(T('phần bau: chạy hết, không vỡ giữa chừng'), False, repr(e)[:200])

        # ===================== hoso: a102f4d =====================
        if 'hoso' in PHAN:
          try:
            pg = open_page(ctx, errs)
            # bắt thân lời gọi /assistant NGAY trong trang (WebKit của Playwright không đưa POST có preflight qua route)
            pg.evaluate("window.__ab=[];var __f=window.fetch;window.fetch=function(u,o){if(String(u).indexOf('/assistant')>=0)__ab.push(o&&o.body);return __f.apply(this,arguments)}")
            pg.evaluate("openAsst()"); pg.wait_for_timeout(300)
            pg.evaluate("asstSend('bé trai 18 tháng nặng 9kg biếng ăn quá')"); pg.wait_for_timeout(1500)
            ho = pg.evaluate("(()=>{try{return JSON.parse(localStorage.getItem('wt_asst_ho')||'null')}catch(e){return null}})()")
            check(T('câu PG gõ được rút thành hồ sơ khách (18 tháng, 9 kg, bé trai, biếng ăn) và LƯU vào máy'),
                  bool(ho) and ho.get('ageMo') == 18 and ho.get('kg') == 9 and ho.get('sex') == 'trai' and any('biếng ăn' in x for x in ho.get('needs', [])), ho)
            bar = pg.evaluate("(()=>{const b=document.getElementById('wtho');return b?b.innerText:''})()")
            check(T('dải "Đang tư vấn" hiện hồ sơ + nút Khách mới'), 'Đang tư vấn' in bar and '18 tháng' in bar and '9 kg' in bar and 'Khách mới' in bar, bar)
            sent = [json.loads(x) for x in pg.evaluate("__ab") if isinstance(x, str) and x.startswith('{')]
            ctx0 = (sent[-1].get('context') or {}) if sent else {}
            check(T('lời gọi trợ lý mang hồ sơ khách (context.ho_so_be) + lịch sử ≤ 8 lượt'), '18 tháng' in (ctx0.get('ho_so_be') or '') and isinstance(ctx0.get('lich_su'), list) and len(ctx0['lich_su']) <= 8, ctx0)
            pg.close()
            # tải lại trang (Zalo reload / mở lại app): hồ sơ còn nguyên
            pg = open_page(ctx, errs, wipe=False)
            pg.evaluate("openAsst()"); pg.wait_for_timeout(300)
            bar = pg.evaluate("(()=>{const b=document.getElementById('wtho');return b?b.innerText:''})()")
            hs = pg.evaluate("(()=>{try{return buildAsstContext().ho_so_be||''}catch(e){return ''}})()")
            check(T('mở lại app: dải "Đang tư vấn" vẫn còn, ngữ cảnh trợ lý vẫn mang hồ sơ (không "quên" khách)'), '18 tháng' in bar and '18 tháng' in hs, (bar, hs))
            # hồ sơ cũ hơn 3 giờ: nhắc hỏi có phải khách mới không
            pg.evaluate("closeAsst();asstHo.updatedAt=Date.now()-4*3600*1000;saveHo();openAsst()"); pg.wait_for_timeout(300)
            lastm = pg.evaluate("asstLog.length?asstLog[asstLog.length-1].t:''")
            check(T('hồ sơ cũ hơn 3 giờ: trợ lý nhắc "đang tư vấn cho … — nếu là khách mới bấm Khách mới"'), 'Khách mới' in lastm and '18 tháng' in lastm, lastm)
            # PG bấm Huỷ ở hộp hỏi lại: không xoá gì
            pg.evaluate("window.confirm=function(){return false}")
            pg.click("#wtho button"); pg.wait_for_timeout(300)
            check(T('Khách mới -> bấm Huỷ: hồ sơ còn nguyên'), pg.evaluate("!!localStorage.getItem('wt_asst_ho')&&!!document.getElementById('wtho')"))
            pg.evaluate("window.confirm=function(){return true}")
            pg.click("#wtho button"); pg.wait_for_timeout(300)
            st = pg.evaluate("[localStorage.getItem('wt_asst_ho'),!!document.getElementById('wtho'),asstLog.length,hoSoText()]")
            check(T('Khách mới -> Đồng ý: xoá hồ sơ khỏi máy, mất dải, hội thoại về lời chào'), st[0] is None and st[1] is False and st[2] == 1 and st[3] == '', st)
            pg.close()
          except Exception as e:   # phần cũ thiếu hàm -> ghi SAI rồi chạy tiếp phần sau (không vỡ cả tệp)
            check(T('phần hoso: chạy hết, không vỡ giữa chừng'), False, repr(e)[:200])

        # ===================== nhap: 8445a33 =====================
        if 'nhap' in PHAN:
          try:
            pg = open_page(ctx, errs)
            pg.evaluate("""()=>{newConsult();S.consent=true;S.buyer={name:'Chi Lan',phone:'0912345678',addr:'',rel:'Mẹ'};S.user={name:'',obj:'adult',gender:'Nữ',birth:'',deliv:'',hist:['Không có'],cur:''};next1()}""")
            pg.wait_for_timeout(200)
            dr = pg.evaluate("(()=>{try{return JSON.parse(localStorage.getItem('wt_draft_v1')||'null')}catch(e){return null}})()")
            check(T('đang tư vấn (bước 2): app tự lưu nháp vào máy'), bool(dr) and dr.get('step') == 2 and (dr.get('buyer') or {}).get('phone') == '0912345678', dr)
            pg.close()
            pg = open_page(ctx, errs, wipe=False)      # Zalo tải lại trang / Back thoát app rồi mở lại
            home = pg.evaluate("document.getElementById('view').innerText")
            check(T('mở lại app: Trang chủ có thẻ "Có phiên tư vấn đang dở", nói đang ở bước 2/4'), 'Có phiên tư vấn đang dở' in home and '2/4' in home, home[:200])
            pg.locator("#view button", has_text='Tiếp tục').first.click(); pg.wait_for_timeout(300)
            st = pg.evaluate("[S.tab,S.step,S.buyer.phone,S.user.obj]")
            check(T('bấm Tiếp tục: về đúng bước 2 với thông tin khách cũ'), st == ['tuvan', 2, '0912345678', 'adult'], st)
            # chốt xong: bỏ nháp, lượt vẽ sau không tạo lại nháp
            pg.evaluate("()=>{S.m={w:60,h:160};S.cls=classify();S.rec=buildRec();S.step=4;finishConsult();render()}"); pg.wait_for_timeout(300)
            check(T('chốt phiên xong: nháp bị xoá và KHÔNG sinh lại khi vẽ màn kết quả'), pg.evaluate("localStorage.getItem('wt_draft_v1')") is None)
            pg.evaluate("S.tab='home';render()")
            check(T('sau khi chốt: Trang chủ không còn thẻ phiên dở'), 'Có phiên tư vấn đang dở' not in pg.evaluate("document.getElementById('view').innerText"))
            pg.close()
            # nút Bỏ + khách KHÔNG đồng ý: nháp không giữ tên / SĐT
            pg = open_page(ctx, errs)
            pg.evaluate("""()=>{newConsult();S.consent=false;S.buyer={name:'An Lo',phone:'0987654321',addr:'DiaChiLo',rel:'Mẹ'};S.user={name:'Bo Lo',obj:'adult',gender:'Nam',birth:'',deliv:'',hist:['Không có'],cur:''};S.step=2;render()}""")
            raw = pg.evaluate("localStorage.getItem('wt_draft_v1')||''")
            check(T('khách KHÔNG đồng ý: nháp không chứa tên / SĐT / địa chỉ'), raw and all(x not in raw for x in ('An Lo', '0987654321', 'DiaChiLo', 'Bo Lo')), raw[:200])
            pg.evaluate("S.tab='home';render()")
            pg.locator("#view button", has_text='Bỏ').first.click(); pg.wait_for_timeout(300)
            check(T('bấm Bỏ: xoá nháp, thẻ biến mất'), pg.evaluate("localStorage.getItem('wt_draft_v1')") is None and 'Có phiên tư vấn đang dở' not in pg.evaluate("document.getElementById('view').innerText"))
            pg.close()
          except Exception as e:   # phần cũ thiếu hàm -> ghi SAI rồi chạy tiếp phần sau (không vỡ cả tệp)
            check(T('phần nhap: chạy hết, không vỡ giữa chừng'), False, repr(e)[:200])
        # 2 dòng đầu: lỗi của bộ thử WebKit khi giả máy chủ cho fetch có preflight (Chromium sạch); app đã .catch các lời gọi này
        errs[:] = [e for e in errs if 'Returned response is null' not in e and not ('api.wintop.vn' in e and 'access control checks' in e)
                   and 'wintop/catalog' not in e and 'Response served by service worker is an error' not in e]
        check(T('không lỗi JS'), not errs, errs)
        b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if res and all(res) else 1)
