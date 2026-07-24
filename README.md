# Mini Apartment Management System

Hệ thống quản lý căn hộ cho thuê (người thuê, phòng, hợp đồng, thanh toán tiền thuê) xây dựng bằng **Python/Flask**.

## Mô tả

Ứng dụng web hỗ trợ quản lý hoạt động cho thuê căn hộ: theo dõi thông tin người thuê, tình trạng phòng, hợp đồng và các khoản thanh toán tiền thuê hàng tháng. Có trang quản trị riêng cho admin và cơ chế nhắc việc tự động chạy nền.

## Tính năng chính

- **Quản lý người thuê (Tenant):** thêm/sửa/xoá thông tin người thuê, gắn với phòng đang thuê.
- **Quản lý phòng (Room):** theo dõi tình trạng phòng (còn trống/đã thuê), thông tin căn hộ.
- **Quản lý thanh toán:** ghi nhận và theo dõi các khoản thanh toán tiền thuê theo kỳ.
- **Đăng nhập & phân quyền:** xác thực người dùng bằng Flask-Login.
- **Trang quản trị (Admin panel):** quản lý dữ liệu trực tiếp qua Flask-Admin.
- **Tác vụ định kỳ chạy nền:** dùng Flask-APScheduler để tự động hoá các công việc lặp lại (ví dụ: nhắc thanh toán/kiểm tra hạn hợp đồng).
- **Lưu trữ ảnh:** tích hợp Cloudinary để lưu ảnh (ví dụ ảnh phòng/người thuê).
- **Form & validate dữ liệu:** dùng WTForms cho các form nhập liệu.

> Ghi chú: các mục trên được suy ra từ stack công nghệ trong `requirements.txt`. Vui lòng chỉnh sửa lại cho khớp chính xác với tính năng thực tế trước khi publish.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Backend | Python, Flask 3.1 |
| ORM & Database | Flask-SQLAlchemy, PyMySQL (MySQL) |
| Xác thực | Flask-Login |
| Quản trị | Flask-Admin |
| Tác vụ nền | Flask-APScheduler (APScheduler) |
| Form | Flask-WTF / WTForms |
| Lưu trữ ảnh | Cloudinary |

## Cấu trúc dự án

```
Mini-Apartment-Management-System/
├── aapp/                # Mã nguồn ứng dụng Flask (routes, models, templates...)
├── requirements.txt     # Danh sách thư viện Python
└── .gitignore
```

## Cài đặt và chạy

### Yêu cầu

- Python 3.10+
- MySQL

### Các bước

```bash
git clone https://github.com/thuttat/Mini-Apartment-Management-System.git
cd Mini-Apartment-Management-System

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Tạo file `.env` (hoặc cấu hình biến môi trường) với các thông tin kết nối, ví dụ:

```
DATABASE_URL=mysql+pymysql://<user>:<password>@localhost/<db_name>
SECRET_KEY=<your_secret_key>
CLOUDINARY_URL=<your_cloudinary_url>
```

Chạy ứng dụng:

```bash
python aapp/app.py   
```

## Demo


## Tác giả

Trịnh Thị Anh Thư — [github.com/thuttat](https://github.com/thuttat)
Lê Hoàng Bảo Trân - [github.com/TranLe05](https://github.com/TranLe05)
Nguyễn Triệu Duy - [github.com/duynguyenntd](https://github.com/duynguyenntd)
