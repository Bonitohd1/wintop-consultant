# Phép thử của App Sale Wintop

Chạy hết bằng một lệnh (từ gốc kho): `python tests/chay_het.py`

Cần Python 3, Node.js, và `pip install playwright` rồi `playwright install chromium`. Mỗi phép thử tự dựng máy chủ tĩnh tạm và **chặn mọi lời gọi tới `api.wintop.vn`** (trả giả): không ghi gì vào hệ thống thật. Quan trọng: App Sale gốc ghi THẬT vào máy chủ khi bấm "xong tư vấn" — đừng thử trên bản gốc.

| File | Kiểm gì |
|---|---|
| `test_cau_dong_y_va_tang_truong.py` | Câu xin đồng ý có lý do + chăm sóc, nhận định chỉ so chuẩn WHO, tìm bé theo SĐT |
| `test_man_quet.py` | Màn quét BIO-SCAN chạy theo tiến độ (vạch quét đi xuống theo %, hoàn tất, chống bấm đúp, rời tab giữa chừng, giảm chuyển động) |

Ảnh chụp sinh ra ở `tests/_anh/` (không đưa lên Git).
