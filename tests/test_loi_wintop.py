"""Phép thử Wintop 13/10/2026 — các lỗi do agent rà tìm ra (đều tái hiện được trên bản trước khi sửa):
 màn Thống kê treo (biến daily che hàm) · Back (nút +, menu, Trợ lý) · CSV lộ tên/SĐT khi KHÔNG đồng ý · SĐT sai · 2 bé cùng SĐT+tên bị gộp
 · số đo vô lý · ngày đo trước ngày sinh · múi giờ 0–7h · tuần sinh non nhập nhầm · lưu thất bại báo thành công
 · thước đo theo WHO thật · thừa cân không bị gợi ý sữa tăng cân · kháng đông / tiểu đường ở trẻ / dị ứng đậu nành / bệnh thận
 · lời nhắc bắt buộc phải HIỆN trên màn kết quả · mẹ sau sinh không còn chữ thai kỳ · dữ liệu localStorage sai kiểu.
Chạy trên bản sao cục bộ, MỌI request ra ngoài bị chặn (api.wintop.vn trả giả) — KHÔNG ghi vào máy chủ thật.
Dùng: python tests/test_loi_wintop.py [đường-dẫn-index.html]   (chạy trên bản cũ phải ĐỎ)"""
import sys, os, json, threading, http.server, socketserver, functools, shutil, tempfile
from playwright.sync_api import sync_playwright

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html')
d = tempfile.mkdtemp(); shutil.copy(SRC, os.path.join(d, 'index.html'))
for extra in ('sw.js', 'manifest.json', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'):
    sp = os.path.join(os.path.dirname(SRC), extra)
    if os.path.exists(sp): shutil.copy(sp, os.path.join(d, extra))


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{port}/index.html'
res = []


def check(n, ok, det=''):
    res.append(bool(ok)); print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else '  ' + str(det)))


def route(r):
    u = r.request.url
    if u.startswith('http://127.0.0.1'): return r.continue_()
    if 'api.wintop.vn' in u:
        cors = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*'}
        if r.request.method == 'OPTIONS': return r.fulfill(status=204, headers=cors)
        return r.fulfill(status=200, content_type='application/json', body='{}', headers=cors)
    return r.abort()


ISOM = "(a)=>{const d=new Date();d.setMonth(d.getMonth()-a);return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}"


def fresh(ctx, errs, clock=None):
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.route('**/*', route)
    if clock: pg.clock.set_fixed_time(clock)
    pg.goto(URL); pg.wait_for_timeout(1500)
    pg.evaluate("""()=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';document.querySelectorAll('.overlay,.modal,#tour,#tourbd').forEach(e=>e.remove());
      localStorage.setItem('wt_seen_guide','1');localStorage.removeItem(BB_KEY);localStorage.removeItem(MEA_KEY);S.tab='home';render();
      window.__t=[];var __o=toast;toast=function(m){__t.push(String(m));__o(m)};window.confirm=function(){return true}}""")
    pg.wait_for_timeout(300)
    return pg


def last_toast(pg):
    return pg.evaluate("__t.length?__t[__t.length-1]:''")


def rec(pg, obj, m, needs=None, hist=None, gender='Nam', extra=None, consent=False):
    """Đặt state rồi tính cls + rec + vẽ màn kết quả; trả dict."""
    return pg.evaluate("""([obj,m,needs,hist,g,ex,cons])=>{S.user={name:'',obj:obj,gender:g,birth:'',deliv:'',hist:hist||['Không có'],cur:''};if(ex)Object.assign(S.user,ex);S.buyer={name:'',phone:'',addr:'',rel:''};
      S.m=m;S.needs=needs||[];S.consent=cons;S.cls=classify();S.rec=buildRec();S.step=4;S.tab='tuvan';S.scanState='done';render();
      var v=document.getElementById('view');return {cls:S.cls,rec:S.rec,t:v.innerText,order:/orderFromRec/.test(v.innerHTML),sci:sciAdvice()}}""",
                       [obj, m, needs, hist, gender, extra, consent])


with sync_playwright() as p:
    for eng in ('chromium', 'webkit'):
        b = getattr(p, eng).launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, timezone_id='Asia/Ho_Chi_Minh')
        errs = []
        T = lambda s: f'[{eng}] ' + s

        # ===== màn Thống kê treo =====
        pg = fresh(ctx, errs)
        pg.evaluate("setTab('profile')"); pg.wait_for_timeout(200)
        n0 = len(errs)
        pg.evaluate("setTab('stats')"); pg.wait_for_timeout(500)
        check(T('Thống kê: mở được (không "daily is not a function"), nội dung hiện, loader không kẹt'),
              len(errs) == n0 and 'Khách tuần này' in pg.evaluate("document.getElementById('view').innerText") and not pg.evaluate("document.getElementById('loader').classList.contains('show')"), (errs[n0:], ))
        pg.evaluate("setTab('tuvan');setTab('home')");
        check(T('đổi tab không bật loader giả 280ms'), not pg.evaluate("document.getElementById('loader').classList.contains('show')"))
        pg.close()

        # ===== Back =====
        for name, opener, closed in [('nút "+" (Tư vấn khách mới)', "newConsult()", None), ('menu', "openDrawer()", "(()=>{const d=document.getElementById('drawer');return !(d.firstChild&&d.firstChild.classList.contains('open'))})()"),
                                     ('Trợ lý', "openAsst()", "document.getElementById('asst').innerHTML.length===0")]:
            pg = fresh(ctx, errs)
            pg.evaluate(opener); pg.wait_for_timeout(700)
            pg.go_back(); pg.wait_for_timeout(700)
            ok = pg.url.startswith(URL) and pg.evaluate("S.tab") == 'home' and (closed is None or pg.evaluate(closed))
            check(T(f'Back sau {name}: KHÔNG thoát app, về Trang chủ / đóng lớp phủ'), ok, (pg.url, pg.evaluate("S.tab") if pg.url.startswith(URL) else None))
            pg.close()

        # ===== đồng ý / CSV / SĐT / trùng bé =====
        pg = fresh(ctx, errs)
        pg.evaluate("S.consent=true;S.buyer={name:'An',phone:'0912345678',addr:'x',rel:'Mẹ'};S.user.name='Bo';setConsent(false)")
        check(T('chọn KHÔNG đồng ý: xoá tên / SĐT đã gõ'), pg.evaluate("S.buyer.name===''&&S.buyer.phone===''&&S.user.name===''"))
        csv = pg.evaluate("""()=>{var cap={};HTMLAnchorElement.prototype.click=function(){cap.href=this.href;cap.dl=this.download};S.consent=false;S.buyer={name:'AnLo',phone:'0912345678',addr:'DiaChiLo',rel:'Me'};S.user.name='BoLo';S.user.hist=['Không có'];S.user.obj='adult';S.rec={prods:[]};S.cls={};exportCSV();return {txt:decodeURIComponent((cap.href||'').split(',').slice(1).join(',')),dl:cap.dl}}""")
        check(T('Xuất CSV khi KHÔNG đồng ý: không có tên / SĐT / địa chỉ, tên tệp không chứa SĐT'), all(x not in csv['txt'] for x in ('AnLo', '0912345678', 'DiaChiLo', 'BoLo')) and '0912345678' not in (csv['dl'] or ''), csv)
        for ph, ok_ in [('12345', False), ('abc', False), ('0912 345 67', False), ('0912 345 678', True)]:
            st = pg.evaluate("""([ph])=>{S.step=1;S.consent=true;S.buyer={name:'An',phone:ph,addr:'',rel:''};S.user={name:'',obj:'adult',gender:'Nam',birth:'',deliv:'',hist:[],cur:''};window.__t=[];next1();return S.step}""", [ph])
            check(T(f'SĐT "{ph}": {"qua" if ok_ else "bị chặn kèm lời báo"}'), (st == 2) == ok_ and (ok_ or 'SĐT' in last_toast(pg)), (st, last_toast(pg)))
        pg.evaluate("""([d1])=>{saveBabies([{id:'B1',ten:'Bé',ngaySinh:d1,gioiTinh:'Trai',phone:'0912345678',cv:CONSENT_V}]);}""", [pg.evaluate(ISOM, 30)])
        st = pg.evaluate("""([d2])=>{S.step=1;S.consent=true;S.buyer={name:'An',phone:'0912345678',addr:'',rel:''};S.user={name:'',obj:'tre_1_10',gender:'Nữ',birth:'',deliv:'',hist:[],cur:'',dob:d2};window.__t=[];next1();return S.step}""", [pg.evaluate(ISOM, 8)])
        check(T('2 bé cùng SĐT + cùng tên (trống), khác ngày sinh: bị chặn ở bước 1, báo cách phân biệt'), st == 1 and 'KHÁC TÊN' in last_toast(pg), (st, last_toast(pg)))
        pg.close()

        # ===== số đo vô lý, tuổi =====
        pg = fresh(ctx, errs)
        for lbl, obj, m, key in [('cân 500kg (bé 8 tháng)', 'tre_0_12', {'months': 8, 'w': 500, 'h': 70}, '150 kg'), ('cao 400cm (bé 8 tháng)', 'tre_0_12', {'months': 8, 'w': 8, 'h': 400}, '30–220'),
                                 ('cân 500kg (bé 6 tuổi)', 'tre_1_10', {'age': 6, 'w': 500, 'h': 110}, '150 kg'), ('người lớn cao 500', 'adult', {'w': 60, 'h': 500}, '100–250'),
                                 ('người lớn cân 5kg', 'adult', {'w': 5, 'h': 170}, '20–300'), ('mẹ bầu cân trước thai 5kg', 'pregnant', {'pw': 5, 'h': 160}, '30–200')]:
            msg = pg.evaluate("([o,m])=>{S.user={name:'',obj:o,gender:'Nam',birth:'',deliv:'',hist:['Không có'],cur:''};S.m=m;return validClose()}", [obj, m])
            check(T(f'{lbl}: bị chặn, có lời báo'), bool(msg) and key in msg, msg)
        ok = pg.evaluate("()=>{S.user={name:'',obj:'tre_0_12',gender:'Nam',birth:'',deliv:'',hist:['Không có'],cur:''};S.m={months:8,w:8.5,h:70};return validClose()}")
        check(T('số đo hợp lý vẫn qua'), ok is None, ok)
        pg.close()

        # ===== múi giờ 03:00 VN, ngày đo trước ngày sinh, sinh non nhập nhầm, lưu thất bại =====
        pg = fresh(ctx, errs, '2026-10-13T03:00:00+07:00')
        today = pg.evaluate("nowISO()")
        pg.evaluate("([t])=>{S.bf={ten:'Bo',ngaySinh:t,gioiTinh:'Trai'};S.growth.addingBaby=true;submitBaby()}", [today])
        check(T('03:00 giờ VN: lưu được bé sinh HÔM NAY'), pg.evaluate("babies().length") == 1, last_toast(pg))
        bid = pg.evaluate("babies()[0]&&babies()[0].id")
        pg.evaluate("([id,t])=>{S.growth.baby=id;S.gf={ngayDo:t,canNang:'3.4',chieuCao:'50'};submitMeasure()}", [bid, today])
        check(T('03:00 giờ VN: lưu được số đo HÔM NAY'), pg.evaluate("measures().length") == 1, last_toast(pg))
        pg.close()
        pg = fresh(ctx, errs)
        pg.evaluate("([d])=>{S.bf={ten:'Mi',ngaySinh:d,gioiTinh:'Trai'};S.growth.addingBaby=true;submitBaby()}", [pg.evaluate(ISOM, 6)])
        bid = pg.evaluate("babies()[0].id")
        pg.evaluate("([id,d])=>{S.growth.baby=id;S.gf={ngayDo:d,canNang:'6',chieuCao:'60'};submitMeasure()}", [bid, pg.evaluate(ISOM, 7)])
        check(T('ngày đo TRƯỚC ngày sinh: bị chặn, báo rõ'), pg.evaluate("measures().length") == 0 and 'trước ngày sinh' in last_toast(pg), last_toast(pg))
        pg.evaluate("""()=>{S.user={name:'',obj:'tre_0_12',gender:'Nam',birth:'',deliv:'',hist:[],cur:''};var i=document.createElement('input');i.value='32';setPreterm(i);window.__pi=i.value}""")
        check(T('"tuần sinh sớm" 32 (nhầm tuổi thai): bị từ chối + giải thích'), pg.evaluate("pretermWeeks()") == 0 and 'TUẦN SINH SỚM' in last_toast(pg), last_toast(pg))
        pg.evaluate("(()=>{const o=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(String(k).indexOf('nt_')===0)throw new DOMException('quota','QuotaExceededError');return o.call(this,k,v)};return 1})()")
        pg.evaluate("localStorage.removeItem('nt_babies')") if False else None
        n_before = pg.evaluate("babies().length")
        pg.evaluate("([d])=>{S.growth.editBaby=null;S.bf={ten:'Ti',ngaySinh:d,gioiTinh:'Trai'};S.growth.addingBaby=true;submitBaby()}", [pg.evaluate(ISOM, 5)])
        check(T('bộ nhớ đầy: báo "CHƯA được lưu", không báo thành công'), 'CHƯA được lưu' in last_toast(pg), last_toast(pg))
        pg.close()

        # ===== thước đo WHO =====
        pg = fresh(ctx, errs)
        r = rec(pg, 'tre_0_12', {'months': 12, 'w': 6.8, 'h': 70})
        check(T('bé trai 12 tháng 6,8kg: "Suy dinh dưỡng nặng" (WHO Z −3,2), và KHÔNG còn dòng "chuẩn ước lượng … R&D"'), r['cls']['label'] == 'Suy dinh dưỡng nặng' and 'R&D' not in r['t'] and 'ước lượng' not in r['t'], r['cls'])
        r = rec(pg, 'tre_1_10', {'age': 5, 'w': 18.5, 'h': 100})
        check(T('bé 5 tuổi BMI 18,5 (WHO béo phì): không còn "Bình thường"'), r['cls']['label'] == 'Béo phì' and r['cls']['status'] == 'high', r['cls'])
        r = rec(pg, 'tre_1_10', {'age': 5, 'w': 14.8, 'h': 100})
        check(T('bé 5 tuổi BMI 14,8 (WHO bình thường): không còn "Gầy"'), r['cls']['label'] == 'Bình thường', r['cls'])
        sweep = pg.evaluate("""(()=>{var bad=[],n=0;for(var g of ['Nam','Nữ'])for(var mo=0;mo<=12;mo++)for(var w=2.5;w<=14;w+=0.25){S.user={name:'',obj:'tre_0_12',gender:g,hist:[],preterm:''};S.m={months:mo,w:w};var c=classify(),r=whoCls('w',mo,w),zc=zClass(r.z,'w').lb;n++;
          var ok=(c.label===zc)||(c.label==='Suy dinh dưỡng nặng'&&zc==='Nhẹ cân nặng')||(c.label==='Hơi thấp (vẫn trong chuẩn WHO)'&&zc==='Bình thường')||(c.label==='Cân nặng cao hơn chuẩn'&&zc==='Cao hơn chuẩn');if(!ok)bad.push([g,mo,w,c.label,zc])}return {n:n,nb:bad.length,bad:bad.slice(0,3)}})()""")
        check(T(f'quét {sweep["n"]} ca: nhãn tư vấn LUÔN khớp nhãn biểu đồ WHO'), sweep['nb'] == 0, sweep)
        r = rec(pg, 'tre_0_12', {'months': 2, 'w': 4.4, 'h': 55}, extra={'preterm': '8'})
        check(T('sinh non 8 tuần, 2 tháng 4,4kg: thước đo dùng TUỔI HIỆU CHỈNH (không còn "Nguy cơ nhẹ cân" theo tuổi thật)'), r['cls']['status'] == 'normal', r['cls'])

        # ===== gợi ý an toàn =====
        r = rec(pg, 'adult', {'w': 95, 'h': 165}, ['Tăng cân / tăng cơ'])
        check(T('người lớn BMI 34,9 chọn "Tăng cân": KHÔNG gợi ý sữa tăng cân, KHÔNG nút lên đơn'), r['rec']['prods'] == [] and not r['order'], r['rec'])
        r = rec(pg, 'adult', {'w': 78, 'h': 170})
        check(T('người lớn BMI 27: KHÔNG gợi ý Sure Gold / Gain Pro'), not set(r['rec']['prods']) & {'suregold', 'gainpro', 'ba'}, r['rec']['prods'])
        r = rec(pg, 'adult', {'w': 95, 'h': 165}, ['Loãng xương'])
        check(T('người lớn thừa cân nhưng chọn Loãng xương: vẫn Canxi Nano (nhu cầu thật)'), r['rec']['prods'] == ['canxinano'], r['rec']['prods'])
        r = rec(pg, 'tre_1_10', {'age': 7, 'w': 34, 'h': 120}, ['Tăng cân'])
        check(T('bé 7 tuổi béo phì chọn "Tăng cân": KHÔNG gợi ý BA'), 'ba' not in r['rec']['prods'], r['rec']['prods'])
        r = rec(pg, 'tre_1_10', {'age': 4, 'w': 11, 'h': 100})
        check(T('bé nhẹ cân thật (z<−2) vẫn gợi ý BA + Colostrum (không hồi quy)'), r['rec']['prods'][:1] == ['ba'], r['rec']['prods'])
        r = rec(pg, 'tre_1_10', {'age': 4, 'w': 16, 'h': 100}, [], ['Tiểu đường'])
        check(T('trẻ tiểu đường: dừng, không gợi ý sản phẩm, không nút lên đơn'), r['rec']['freeze'] and not r['order'] and 'tiểu đường' in r['t'].lower(), r['rec'].get('title'))
        r = rec(pg, 'adult', {'w': 60, 'h': 165}, [], ['Dị ứng đậu nành / hạt / cá'])
        check(T('dị ứng đậu nành / hạt / cá: dừng, "hỏi bác sĩ", không nút lên đơn'), r['rec']['freeze'] and 'bác sĩ' in r['t'] and not r['order'], r['rec'].get('title'))
        r = rec(pg, 'adult', {'w': 60, 'h': 165}, [], ['Bệnh thận / sỏi thận'])
        check(T('bệnh thận / sỏi thận: dừng, không nút lên đơn'), r['rec']['freeze'] and not r['order'], r['rec'].get('title'))
        r = rec(pg, 'pregnant', {'pw': 55, 'h': 160}, [], ['Đang dùng thuốc kháng đông'], 'Nữ')
        check(T('mẹ bầu dùng thuốc kháng đông (Mama có K2/MK7): lời cảnh báo HIỆN trên màn kết quả'), 'kháng đông' in r['t'] and 'Lưu ý quan trọng' in r['t'] and 'Vitamin K' in r['t'], r['t'][:100])
        r = rec(pg, 'adult', {'w': 45, 'h': 170}, [], ['Đang dùng thuốc kháng đông'])
        check(T('người lớn gầy + kháng đông: cảnh báo vitamin K cho MỌI sản phẩm gợi ý (không chỉ Sure Gold)'), 'Vitamin K' in r['t'] and 'Lưu ý quan trọng' in r['t'], r['t'][:100])
        r = rec(pg, 'tre_1_10', {'age': 1.5, 'w': 11, 'h': 80})
        check(T('trẻ dưới 24 tháng: khuyến cáo NĐ 100 BẮT BUỘC hiện trên màn (trước: nằm trong dữ liệu, không in ra)'), 'Khuyến cáo BẮT BUỘC' in r['t'] and 'Sữa mẹ là thức ăn tốt nhất' in r['t'], r['t'][:100])
        r = rec(pg, 'tre_0_12', {'months': 8, 'w': 4.5, 'h': 60})
        check(T('bé 8 tháng 4,5kg (suy dinh dưỡng nặng): lời "BẮT BUỘC đi khám" hiện trên màn'), 'đi khám' in r['t'] and 'Lưu ý quan trọng' in r['t'], r['t'][:100])
        r = rec(pg, 'pregnant', {'w': 60, 'h': 160}, ['Hay ốm / mệt mỏi'], ['Không có'], 'Nữ', {'postpartum': True})
        check(T('mẹ SAU SINH: lời tư vấn khoa học không còn "thai nhi / thai kỳ / mang thai"'), not any(w in r['sci'] for w in ('thai nhi', 'thai kỳ', 'mang thai')), r['sci'][:160])

        # ===== lsGet sai kiểu =====
        bad = pg.evaluate("""(()=>{localStorage.setItem('wt_notifs','null');localStorage.setItem('nt_babies','5');localStorage.setItem('wt_x','"x"');localStorage.setItem('wt_y','{"a":1}');
          return [Array.isArray(lsGet('wt_notifs',[])),Array.isArray(lsGet('nt_babies',[])),lsGet('wt_x',{}).a===undefined&&typeof lsGet('wt_x',{})==='object',lsGet('wt_y',{}).a===1]})()""")
        check(T('lsGet: dữ liệu sai kiểu (null / số / chuỗi) trả về mặc định; đúng kiểu giữ nguyên'), all(bad), bad)
        # WebKit của Playwright báo 'Returned response is null' khi giả máy chủ cho fetch có preflight (lỗi của công cụ test, Chromium sạch)
        errs[:] = [e for e in errs if 'Returned response is null' not in e and 'wintop/catalog' not in e and 'Response served by service worker is an error' not in e]   # catalog bị harness chặn -> SW trả lỗi mạng (đã bắt .catch); trước 13/10 SW trả index.html che lỗi
        check(T('không lỗi JS'), not errs, errs)
        pg.close()
        b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if all(res) else 1)
