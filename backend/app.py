"""
FLASK APP MAIN ENTRY POINT - OTP BACKEND SERVER
==================================================

Đây là file chính để khởi chạy OTP Backend API Server.
File này thiết lập Flask app, cấu hình CORS, và đăng ký tất cả API routes.

CÁC TÍNH NĂNG CHÍNH
- Flask web server với debug mode
- CORS enabled cho frontend integration
- Tự động import routes từ backend/routes.py
- Trang chủ với hướng dẫn API endpoints
"""

from flask import Flask
from flask_cors import CORS
import sys
import os

# Giải quyết vấn đề import khi chạy từ thư mục backend
# sys.path.insert(0, path) thêm path vào đầu danh sách tìm kiếm modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# KHỞI TẠO FLASK APP
# Flask app là core của web server, xử lý tất cả HTTP requests
app = Flask(__name__)

# BẬT CORS (Cross-Origin Resource Sharing)
# Cho phép frontend (chạy trên domain/port khác) gọi API đến backend
# Nếu không có CORS, browser sẽ chặn requests từ frontend đến backend
CORS(app)

# IMPORT VÀ ĐĂNG KÝ ROUTES
# Blueprint giúp tổ chức code thành modules độc lập
from backend.routes import otp_bp  # Import OTP API routes blueprint

# Đăng ký blueprint với app, tất cả routes sẽ có prefix mặc định
app.register_blueprint(otp_bp)

# ROOT ENDPOINT - TRANG CHỦ API
# Trả về thông tin cơ bản và danh sách endpoints available
@app.route('/')
def index():
    """
    TRANG CHỦ API - HIỂN THỊ TẤT CẢ ENDPOINTS
    
    Truy cập: http://localhost:5000
    
    Đây là trang documentation tự động, giúp người dùng biết các endpoints có sẵn
    """
    return {
        "message": "OTP Backend API is running",
        "endpoints": {
            "load_secret": "GET /load_secret",
            "totp": "GET /totp", 
            "hotp": "GET /hotp?counter=<number>",
            "otpauth_uri": "GET /otpauth_uri",
            "generate_secret": "POST /generate_secret",
            "verify_totp": "POST /verify_totp",
            "verify_hotp": "POST /verify_hotp"
        }
    }


# KHỞI CHẠY SERVER
# Chỉ chạy khi file được execute trực tiếp (không phải import)
if __name__ == '__main__':
    """
    CHẠY FLASK DEVELOPMENT SERVER
    
    Cấu hình:
    - debug=True: Bật debug mode, tự động reload khi code thay đổi
    - host='0.0.0.0': Lắng nghe trên tất cả network interfaces
    - port=5000: Chạy trên port 5000
    
    Các host có thể truy cập:
    - http://localhost:5000
    - http://127.0.0.1:5000 
    - http://192.168.1.21:5000 (IP local network)
    """
    app.run(debug=True, host='0.0.0.0', port=5000)