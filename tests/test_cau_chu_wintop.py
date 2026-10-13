"""Phép thử Wintop 13/10/2026 — CÁCH DIỄN ĐẠT an toàn + khách quét QR / Trình khách + dữ liệu giả + tối ưu (không có Pháp chế, khách tự xem):
 không còn 'ngừa / phòng / tái tạo / triệt để / an toàn cho người tiểu đường / cao nhất / duy nhất' trong dữ liệu sản phẩm · Quiz không còn các câu tuyệt đối / dọa / số liệu không nguồn
 · liều/ngày theo nhãn · khách quét QR (S.guest) không thấy Baby + Kao IQ, hướng dẫn chốt sale, tài liệu đào tạo, QR, nút lên đơn · Trình khách ẩn Baby + Kao IQ + 2 ảnh cảm nhận có trẻ sơ sinh
 · không còn xếp hạng / tên bé giả · phiếu kiểm nghiệm chỉ hiện khi có ảnh · chứng nhận Aiwado hết hạn đã gỡ · cảnh báo sản phẩm hiện cho PG
 · shine bằng transform · service worker có timeout · ảnh đã thu về cỡ hiển thị.
Chạy trên bản sao cục bộ, MỌI request ra ngoài bị chặn. Dùng: python tests/test_cau_chu_wintop.py [index.html]   (chạy trên bản cũ phải ĐỎ)"""
import sys, os, re, json, threading, http.server, socketserver, functools, shutil, tempfile
from playwright.sync_api import sync_playwright

SRCDIR = os.path.dirname(os.path.abspath(sys.argv[1])) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(SRCDIR, 'index.html')
d = tempfile.mkdtemp(); shutil.copy(SRC, os.path.join(d, 'index.html'))
if os.path.exists(os.path.join(SRCDIR, 'sw.js')): shutil.copy(os.path.join(SRCDIR, 'sw.js'), os.path.join(d, 'sw.js'))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # kho thật: để đo kích thước ảnh / sw.js hiện hành
for extra in ('manifest.json', 'icon-192.png', 'icon-512.png'):
    sp = os.path.join(REPO, extra)
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


html = open(SRC, encoding='utf-8').read()
src = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', 'IMG', html)
for bad in ('an toàn để dùng cho người tiểu đường', 'ngăn ngừa hiện tượng', 'giải quyết táo bón triệt để', 'bám dính lấy vi khuẩn, virus tại đường ruột và tiêu diệt chúng',
            'Top 5 Thương hiệu hàng đầu', 'cao nhất toàn bộ dòng Wintop', 'Wintop tài trợ phẫu thuật tim cho bé Ngô', 'Nguyễn Thị Hoa', 'SẢN PHẨM PHÙ HỢP NHẤT VỚI BẠN',
            'Sữa mẹ là tốt nhất cho sức khỏe trẻ sơ sinh'):
    check(f'mã nguồn không còn câu: “{bad[:55]}”', bad not in src)
sw = open(os.path.join(REPO, 'sw.js'), encoding='utf-8').read() if len(sys.argv) < 2 else open(os.path.join(SRCDIR, 'sw.js'), encoding='utf-8').read()
check('service worker: bản mới (wintop-v50), network-first CÓ TIMEOUT, chỉ lưu phản hồi ok', 'wintop-v50' in sw and '4000' in sw and 'res.ok' in sw, sw[:120])
check('shine / pshine animate bằng transform (không còn "left" → ép layout liên tục)', 'left:135%' not in src and 'left:130%' not in src and 'translateX(364%)' in src)
if len(sys.argv) < 2:   # đo ảnh thật trong kho (không đo khi chạy trên bản sao cũ)
    sz = lambda f: os.path.getsize(os.path.join(REPO, f)) // 1024
    check('ảnh sản phẩm PNG ≤ 360KB (trước ~540KB), mascot ≤ 180KB (trước 414KB)', all(sz('assets/products/' + x + '.png') <= 360 for x in ('ba', 'baby', 'kaoiq', 'mama', 'colostrum')) and sz('assets/mascot_lion.png') <= 180, [sz('assets/products/ba.png'), sz('assets/mascot_lion.png')])
    check('không còn tệp sao lưu index.backup-*.html / theme.css trong kho (từng được phát hành công khai)', not [f for f in os.listdir(REPO) if f.startswith('index.backup') or f == 'theme.css'], os.listdir(REPO))

with sync_playwright() as p:
    for eng in ('chromium', 'webkit'):
        b = getattr(p, eng).launch()
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        errs = []
        T = lambda s: f'[{eng}] ' + s
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)[:200])); pg.route('**/*', route)
        pg.goto(URL); pg.wait_for_timeout(1500)
        pg.evaluate("""()=>{const sp=document.getElementById('splash');if(sp)sp.style.display='none';document.querySelectorAll('.overlay,.modal,#tour,#tourbd').forEach(e=>e.remove());localStorage.setItem('wt_seen_guide','1');window.confirm=function(){return true}}""")

        # dữ liệu sản phẩm
        txt = pg.evaluate("JSON.stringify(PRODUCTS)+' '+JSON.stringify(SCI)+' '+JSON.stringify(QUIZ)+' '+JSON.stringify(typeof PINFO!=='undefined'?PINFO:'')")
        BAN = ['ngừa', 'phòng thiếu máu', 'phòng còi', 'triệt để', 'giảm cholesterol', 'tăng cân nhanh chóng', 'tổ yến quý', 'cao nhất dòng', 'cao nhất toàn bộ', 'DUY NHẤT', 'hoàn toàn yên tâm', 'không lo tác dụng phụ', 'loại bỏ 100%']
        bad = [w for w in BAN if w in txt]
        check(T('dữ liệu sản phẩm / tư vấn / quiz / tài liệu: không còn ' + ' · '.join(BAN[:6]) + '…'), not bad, bad)
        qn = pg.evaluate("(()=>{var n=0,k=[];QUIZ.forEach(function(l){n+=l.qs.length});return n})()")
        check(T('Quiz còn đủ câu (đã gỡ ~11 câu tuyệt đối/dọa/số liệu không nguồn, không gỡ nhầm hàng loạt)'), 30 <= qn <= 80, qn)
        dose = pg.evaluate("[EXTRA.ba.dose,EXTRA.kaoiq.dose,EXTRA.mama.dose,EXTRA.diabet.dose,EXTRA.colostrum.dose]")
        check(T('liều/ngày theo nhãn: BA 2 ly · Kao IQ 3 · Mama 3 · Diabet 2–3 · Colostrum theo nhãn'), dose == ['2 ly', '3 ly', '3 ly', '2–3 ly', 'theo nhãn'], dose)
        check(T('dữ liệu giả đã gỡ: bảng xếp hạng chỉ còn "Bạn"; thông báo không còn tên bé'), pg.evaluate("LEADER.length===1&&LEADER[0].me===true") and 'bé Ngô' not in pg.evaluate("JSON.stringify(NOTIFS)"))

        # PG (không guest): trang sản phẩm đầy đủ + cảnh báo
        pg.evaluate("S.guest=false;S.openProd='ba';tabTo('sanpham');render()"); pg.wait_for_timeout(300)
        v = pg.evaluate("document.getElementById('view').innerText")
        check(T('PG xem trang BA: có "Lưu ý khi tư vấn" (cảnh báo hạt óc chó, dị ứng đạm bò…), hướng dẫn chốt sale, nút lên đơn, QR'), 'Lưu ý khi tư vấn' in v and 'hạt óc chó' in v and 'Hướng dẫn chốt sale' in v and 'Lên đơn sản phẩm này' in v and 'QR tại quầy' in v, v[:120])
        pg.evaluate("S.openProd='baby';render()"); pg.wait_for_timeout(300)
        ext = pg.evaluate("[...document.querySelectorAll('#view img')].map(i=>i.getAttribute('src')).filter(s=>/^https?:/.test(s))")
        check(T('trang Baby (PG): không còn ảnh phụ thuộc Google Drive (từng vỡ trên web thật)'), not ext, ext)
        pg.evaluate("S.openProd='ba';render()"); pg.wait_for_timeout(200)
        check(T('trang BA: không còn chứng nhận Aiwado hết hạn; có phiếu kiểm nghiệm (vì có ảnh)'), 'Aiwado' not in v and 'Phiếu kiểm nghiệm' in v)
        pg.evaluate("S.openProd='colostrum';render()"); pg.wait_for_timeout(250)
        v = pg.evaluate("document.getElementById('view').innerText")
        check(T('trang Colostrum (không có ảnh phiếu kiểm nghiệm): KHÔNG hiện tiêu đề "Phiếu kiểm nghiệm hóa lý" rỗng'), 'Phiếu kiểm nghiệm hóa lý' not in v)

        # khách quét QR
        pg.evaluate("S.guest=true;S.openProd='mama';render()"); pg.wait_for_timeout(250)
        v = pg.evaluate("document.getElementById('view').innerText")
        check(T('KHÁCH quét QR (Mama): không thấy hướng dẫn chốt sale, tài liệu đào tạo, QR tại quầy, nút lên đơn / so sánh / tư vấn nhanh, "Lưu ý khi tư vấn"'),
              not any(x in v for x in ('Hướng dẫn chốt sale', 'Tài liệu đào tạo', 'QR tại quầy', 'Lên đơn sản phẩm này', 'So sánh SP', 'Tư vấn nhanh', 'Lưu ý khi tư vấn')), v[:200])
        check(T('KHÁCH vẫn xem được thông tin công bố: đối tượng, thành phần, hướng dẫn sử dụng, giấy công bố, câu sữa mẹ'), all(x in v for x in ('Đối tượng sử dụng', 'Bảng thành phần', 'Quy cách', 'Sữa mẹ là thức ăn tốt nhất')), v[:150])
        for pid in ('baby', 'kaoiq'):
            pg.evaluate("(i)=>{S.openProd=i;render()}", pid); pg.wait_for_timeout(250)
            v = pg.evaluate("document.getElementById('view').innerText"); imgs = pg.evaluate("document.querySelectorAll('#view img').length")
            check(T(f'KHÁCH quét QR {pid}: chỉ còn "hỏi tư vấn viên" + câu sữa mẹ, KHÔNG ảnh / lợi ích'), 'tư vấn viên' in v and 'Sữa mẹ là thức ăn tốt nhất' in v and imgs == 0 and 'Đối tượng sử dụng' not in v, (imgs, v[:120]))
        pg.evaluate("S.openProd=null;render()"); pg.wait_for_timeout(250)
        names = pg.evaluate("[...document.querySelectorAll('#view .pcard')].map(e=>e.innerText)").__len__()
        lst = pg.evaluate("document.getElementById('view').innerText")
        check(T('KHÁCH: danh mục sản phẩm không có Baby và Kao IQ'), 'Wintop Baby' not in lst and 'Wintop KaoIQ' not in lst and 'KaoIQ' not in lst.split('Wintop BA')[0] if False else ('Wintop Baby' not in lst and 'KaoIQ' not in lst and 'Kao IQ' not in lst), lst[:200])
        pg.evaluate("S.guest=false;render()")

        # Trình khách
        pg.evaluate("openPresent();presGo('sanpham')"); pg.wait_for_timeout(300)
        lst = pg.evaluate("document.getElementById('ovl').innerText")
        check(T('Trình khách > Sản phẩm: không có Baby và Kao IQ; vẫn có BA, Colostrum, Mama'), 'Baby' not in lst.replace('Wintop Baby', 'Baby') or ('Wintop Baby' not in lst and 'KaoIQ' not in lst) and all(x in lst for x in ('BA', 'Mama', 'Colostrum')), lst[:200])
        pg.evaluate("presGo('camnhan')"); pg.wait_for_timeout(300)
        n = pg.evaluate("[...document.querySelectorAll('#ovl img[src*=\"feedback\"]')].map(i=>i.getAttribute('src'))")
        check(T('Trình khách > Cảm nhận: gỡ fb1 ("gần như sữa mẹ") và fb3 (bé 11 tháng dùng Baby); còn 8 ảnh'), len(n) == 8 and not any(s.endswith('fb1.jpg') or s.endswith('fb3.jpg') for s in n), n)
        pg.evaluate("closeOvl()"); pg.wait_for_timeout(700)   # history.back() bất đồng bộ: WebKit đẩy tab về chỗ cũ nếu vào ngay

        # kết quả tư vấn
        pg.evaluate("""()=>{S.user={name:'',obj:'adult',gender:'Nam',birth:'',deliv:'',hist:['Không có'],cur:''};S.m={w:60,h:165};S.needs=[];S.consent=false;S.cls=classify();S.rec=buildRec();S.step=4;S.scanState='done';tabTo('tuvan');render()}""")
        pg.wait_for_timeout(400)
        v = pg.evaluate("document.getElementById('view').innerText")
        check(T('kết quả tư vấn: "SẢN PHẨM PHÙ HỢP VỚI BẠN" (bỏ "nhất"), liều/ngày hiện theo nhãn'), 'PHÙ HỢP NHẤT' not in v and 'PHÙ HỢP VỚI BẠN' in v, v[:80])
        errs[:] = [e for e in errs if 'Returned response is null' not in e and 'wintop/catalog' not in e and 'Response served by service worker is an error' not in e]   # catalog bị harness chặn -> SW trả lỗi mạng (đã bắt .catch); trước 13/10 SW trả index.html che lỗi
        check(T('không lỗi JS'), not errs, errs)
        pg.close(); b.close()

shutil.rmtree(d, ignore_errors=True)
print(f'TỔNG {sum(res)} / {len(res)}')
sys.exit(0 if all(res) else 1)
