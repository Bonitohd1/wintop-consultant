# -*- coding: utf-8 -*-
"""Chạy MỌI phép thử của kho này bằng một lệnh:

    python tests/chay_het.py            # chạy hết
    python tests/chay_het.py quet       # chỉ các file thử có chữ "quet" trong tên

Gồm 2 kiểm tra nhanh + các file tests/test_*.py (mỗi file tự dựng máy chủ tĩnh tạm, CHẶN mọi lời gọi ra ngoài, nên không ghi gì
vào hệ thống thật). Cần: Python 3, `pip install playwright` + `playwright install chromium`, và Node.js (cho kiểm cú pháp).

VÌ SAO có file này: các phép thử từng nằm trong thư mục tạm của từng phiên làm việc nên mất khi dọn; sửa một chỗ rồi không còn
chỗ để chạy lại (CLAUDE.md 0.1: phải CHẠY mới tin). Muốn thêm phép thử: tạo tests/test_<tên>.py, in dòng "TỔNG a / b" và thoát mã 0 khi đạt.
"""
import os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAX_KB = 1000   # trần cỡ index.html: chặn lỗi cũ "5,4 MB vì ảnh nhúng base64 → màn mở đầu đứng im" quay lại
sys.stdout.reconfigure(encoding='utf-8')
only = sys.argv[1].lower() if len(sys.argv) > 1 else ''
results = []


def report(name, ok, detail=''):
    results.append(ok)
    print(('✅ ' if ok else '❌ ') + name + (('  — ' + detail) if detail else ''), flush=True)


# 1) cỡ index.html
if not only:
    kb = os.path.getsize(os.path.join(ROOT, 'index.html')) / 1024
    report(f'index.html ≤ {MAX_KB} KB', kb <= MAX_KB, f'{kb:.0f} KB')

# 2) cú pháp mọi <script> nội tuyến (bắt lỗi "dòng cuối bị thiếu dấu ngoặc" trước khi lên Vercel)
if not only:
    js = r"""const fs=require('fs');const h=fs.readFileSync(process.argv[1],'utf8');
const m=[...h.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
let bad=0;m.forEach((s,i)=>{try{new Function(s)}catch(e){bad++;console.log('script '+i+': '+e.message)}});
console.log(m.length+' script, '+bad+' lỗi');process.exit(bad?1:0)"""
    p = subprocess.run(['node', '-e', js, os.path.join(ROOT, 'index.html')], capture_output=True, text=True, encoding='utf-8')
    report('Cú pháp JS trong index.html', p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else '')

# 3) các file thử
for f in sorted(os.listdir(HERE)):
    if not (f.startswith('test_') and f.endswith('.py')) or (only and only not in f.lower()):
        continue
    t0 = time.time()
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, os.path.join(HERE, f)], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    out = p.stdout + p.stderr
    m = re.findall(r'TỔNG (\d+) / (\d+)', out)
    tong = f'{m[-1][0]}/{m[-1][1]} phép' if m else 'không có dòng TỔNG'
    ok = p.returncode == 0 and bool(m)
    report(f'{f}', ok, f'{tong}, {time.time() - t0:.0f}s')
    if not ok:
        print('\n'.join('      ' + l for l in out.strip().splitlines()[-25:]), flush=True)

print()
print(f'TỔNG KẾT: {sum(results)}/{len(results)} mục đạt')
sys.exit(0 if results and all(results) else 1)
