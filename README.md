# CrawBao

Ứng dụng desktop Python để crawl báo và lưu dữ liệu local bằng SQLite.

## Stack

- Python 3.11+
- PySide6
- SQLite
- requests
- BeautifulSoup4
- Playwright

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## Ghi chú

- Không bắt buộc cài browser của Playwright nếu chỉ crawl `menu`, `category` hoặc `article` tĩnh.
- Khi bật `Crawl comment`, app sẽ cần `Playwright + Chromium`.
- Dữ liệu SQLite được lưu tại `data/crawbao.db`.

## Cấu trúc chính

- `app/ui`: giao diện desktop PySide6
- `app/db`: schema SQLite và repository
- `app/models`: model dữ liệu
- `app/services`: điều phối luồng crawl
- `app/crawlers`: crawler cho từng nguồn
- `app/utils`: hàm xử lý HTML, URL, ngày giờ

## Trạng thái hiện tại

- Đã bổ sung crawler `VNExpress` cho:
  - menu category/sub-category
  - category nhiều trang qua `next-page`
  - chi tiết bài viết
  - ảnh trong bài
  - comment tùy chọn bằng Playwright
- Đã mở rộng SQLite an toàn, có migration cho bảng `articles`.
- UI đã có:
  - chọn nguồn
  - chọn loại crawl
  - nhập URL
  - chọn số trang tối đa
  - chọn số bài tối đa
  - bật/tắt crawl comment
  - bật/tắt crawl lại bài đã có
  - progress bar
  - log ngắn
  - nút dừng crawl

## Luồng sử dụng

### Crawl menu VNExpress

- Nguồn: `vnexpress`
- Loại crawl: `menu`
- URL sẽ tự dùng `https://vnexpress.net`

### Crawl category VNExpress

- Nguồn: `vnexpress`
- Loại crawl: `category`
- URL ví dụ: `https://vnexpress.net/thoi-su/chinh-tri`

### Crawl một bài viết

- Nguồn: `vnexpress`
- Loại crawl: `article`
- URL là link bài chi tiết `.html`

### Crawl theo từ khóa VNExpress

- Nguồn: `vnexpress`
- Chuyển sang tab `VNExpress theo từ khóa`
- Nhập từ khóa tìm kiếm, ví dụ: `kẹo Kera`

## Kiểm tra cú pháp

```bash
python -m compileall .
```

## Lưu ý

- Một số selector thực tế của báo có thể thay đổi theo thời gian.
- Phần comment phụ thuộc vào HTML/JavaScript thực tế của `VNExpress`, nên có thể cần tinh chỉnh thêm khi test thật.
