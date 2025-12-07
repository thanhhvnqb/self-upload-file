# Self Upload File

Hệ thống quản lý tệp tin cá nhân (Self Hosted File Management), được xây dựng trên nền tảng Django và Docker. Dự án cho phép người dùng tự lưu trữ, quản lý và chia sẻ tệp tin của mình một cách dễ dàng và bảo mật.

## 🚀 Tính năng nổi bật

- **Quản lý tệp tin**:
  - Upload nhiều tệp tin cùng lúc.
  - Tạo, đổi tên, xóa thư mục và tệp tin.
  - Tải xuống tệp tin lẻ hoặc tải toàn bộ thư mục dưới dạng file nén (ZIP).
- **Hệ thống người dùng**:
  - Đăng nhập, đăng xuất an toàn.
  - Mỗi người dùng có không gian lưu trữ riêng biệt.
- **Giao diện**:
  - Giao diện thân thiện, dễ sử dụng.
  - Hỗ trợ ngôn ngữ Tiếng Việt mặc định.
- **Hệ thống**:
  - Hỗ trợ Docker và Docker Compose cho việc triển khai nhanh chóng.
  - Tích hợp sẵn Ngrok để public ra internet (nếu cần).

## 🛠 Yêu cầu hệ thống

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

## ⚙️ Cài đặt và Chạy ứng dụng

Dự án hỗ trợ chạy trên cả môi trường Development và Production thông qua Docker Compose.

### 1. Môi trường phát triển (Development)

Sử dụng file `docker-compose.dev.yml` hoặc `docker-compose.yml` (mặc định cho dev).

```bash
# Build và chạy container
docker-compose up -d --build

# Hoặc nếu muốn dùng file cấu hình dev riêng biệt
docker-compose -f docker-compose.dev.yml up -d --build
```

Truy cập ứng dụng tại: `http://localhost:8000`

### 2. Môi trường sản phẩm (Production)

Sử dụng file `docker-compose.prod.yml`.

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 3. Tạo tài khoản Admin

Sau khi container đã chạy, bạn cần tạo tài khoản Superuser để quản trị hệ thống:

```bash
docker-compose exec web python manage.py createsuperuser
```

Làm theo hướng dẫn trên màn hình để nhập username, email và password.

## 📂 Cấu trúc thư mục

- `config/`: Chứa các thiết lập cấu hình của Django Project (`settings.py`, `urls.py`, ...).
- `core/`: App chính chứa logic của ứng dụng (Models, Views, Forms).
- `templates/`: Chứa các file giao diện HTML.
- `static/`: Chứa các file tĩnh (CSS, JS, Images).
- `media/`: Thư mục chứa dữ liệu người dùng upload lên (được mount volume ra ngoài container).
- `Dockerfile` & `docker-compose*.yml`: Các file cấu hình cho Docker.

## 🌐 Public ra Internet với Ngrok

Dự án có tích hợp sẵn service `ngrok` trong `docker-compose.yml` để bạn có thể chia sẻ localhost ra internet.
Để sử dụng, hãy chắc chắn bạn đã cấu hình `NGROK_AUTHTOKEN` và `NGROK_DOMAIN` trong file `.env`.

---
