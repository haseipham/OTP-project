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
from flask import Flask, render_template, request
from flask_cors import CORS
import sys
import os

# Giải quyết vấn đề import khi chạy từ thư mục backend
# sys.path.insert(0, path) thêm path vào đầu danh sách tìm kiếm modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# KHỞI TẠO FLASK APP
# Flask app là core của web server, xử lý tất cả HTTP requests
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend'),
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend')
            
            )
app.secret_key = 'otp_demo_secret_key'
# BẬT CORS (Cross-Origin Resource Sharing)
# Cho phép frontend (chạy trên domain/port khác) gọi API đến backend
# Nếu không có CORS, browser sẽ chặn requests từ frontend đến backend
CORS(app)

# IMPORT VÀ ĐĂNG KÝ ROUTES
# Blueprint giúp tổ chức code thành modules độc lập
from backend.routes import otp_bp      # API cũ (single-user)
from backend.api_v2 import otp_bp_v2   # API mới (multi-user)

# Đăng ký blueprint với app, tất cả routes sẽ có prefix mặc định
app.register_blueprint(otp_bp)
app.register_blueprint(otp_bp_v2)

# ROOT ENDPOINT - TRANG CHỦ API
# Trả về thông tin cơ bản và danh sách endpoints available
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    TRANG CHỦ - HIỂN THỊ GIAO DIỆN WEB
    
    Truy cập: http://localhost:5000
    """
    return render_template('Register.html')

@app.route('/Login.html')
def login():
    return render_template('Login.html')

@app.route('/Register.html')
def register():
    return render_template('Register.html')

@app.route('/input_otp.html')
def input_otp():
    return render_template('input_otp.html')

@app.route('/demo_otp.html')
def demo_otp():
    return render_template('demo_otp.html')

@app.route('/congratulations.html')
def congratulations():
    return render_template('congratulations.html')

# Static file routes
@app.route('/input_otp.css')
def input_otp_css():
    return app.send_static_file('input_otp.css')

@app.route('/input_otp.js')
def input_otp_js():
    return app.send_static_file('input_otp.js')

@app.route('/styles_otp.css')
def styles_otp_css():
    return app.send_static_file('styles_otp.css')

@app.route('/script_otp.js')
def script_otp_js():
    return app.send_static_file('script_otp.js')

@app.route('/demo_script.js')
def demo_script_js():
    return app.send_static_file('demo_script.js')


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