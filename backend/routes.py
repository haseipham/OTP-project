"""
OTP BACKEND API ROUTES - FLASK BLUEPRINT

Đây là file chứa tất cả API endpoints cho hệ thống OTP (TOTP/HOTP).
Mỗi hàm dưới đây là một endpoint REST API có thể gọi từ client.

CÁCH SỬ DỤNG:
- Server chạy tại: http://localhost:5000
- Gọi API bằng: curl, Postman, hoặc trình duyệt
- Luôn bắt đầu bằng /generate_secret trước

VÍ DỤ:
curl -X POST http://localhost:5000/generate_secret -H "Content-Type: application/json" -d "{}"
curl http://localhost:5000/totp
"""

from flask import Blueprint, jsonify, request
import time
import sys
import os

# Thêm thư mục gốc vào Python path để import core modules
# Giúp Python tìm thấy thư mục core bên ngoài thư mục backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import các hàm từ core module
from core.otp_core import (
    generate_base32_secret,  # Tạo secret key ngẫu nhiên
    save_secret,             # Lưu secret vào file
    load_secret,             # Đọc secret từ file  
    hotp,                    # Tạo mã HOTP (counter-based)
    totp,                    # Tạo mã TOTP (time-based)
    format_otpauth_uri,      # Tạo URI cho QR code
    verify_totp,             # Xác minh mã TOTP
    verify_hotp,             # Xác minh mã HOTP
    generate_ed25519_keypair, # Tạo keypair SSH (bonus feature)
    try_cryptography_keypair, # tạo keypair
)

# Tạo Flask Blueprint để quản lý các routes OTP
# Blueprint giống như một bộ router con trong Flask
otp_bp = Blueprint('otp', __name__)


import logging  # Optional: Có thể dùng print thay vì logging

@otp_bp.route('/generate_secret', methods=['POST'])
def generate_secret():
    """
    TẠO SECRET KEY 

      curl -X POST http://localhost:5000/generate_secret -H "Content-Type: application/json" -d "{}"

    Hoặc với params: 
      curl -X POST http://localhost:5000/generate_secret -H "Content-Type: application/json" -d '{"digits": 8, "period": 60, "try_keypair": true, "verbose": true}'
    """
    data = request.get_json() or {}
    digits = data.get('digits', 6)
    period = data.get('period', 30)
    try_keypair = data.get('try_keypair', False)
    verbose = data.get('verbose', False)
    
    try:
        # Bước 1: Tạo và lưu secret
        secret = _create_and_save_secret(digits, period)
        
        # Bước 2: Tạo keypair nếu yêu cầu
        keypair_ok = _generate_keypair_if_requested(try_keypair, verbose)
        
        # Log thành công (optional)
        print(f"[INFO] Generated secret: {secret[:8]}... with digits={digits}, period={period}")
        
        return jsonify({
            "secret": secret,
            "success": True,
            "keypair_generated": keypair_ok
        })
    
    except Exception as e:
        # Log lỗi (optional)
        print(f"[ERROR] Failed to generate secret: {e}")
        return jsonify({
            "secret": None,
            "success": False,
            "keypair_generated": False,
            "error": str(e)
        }), 500


def _create_and_save_secret(digits: int, period: int) -> str:
    """Tạo secret Base32 ngẫu nhiên và lưu vào file JSON."""
    secret = generate_base32_secret()
    save_secret(secret, digits=digits, period=period)
    return secret


def _generate_keypair_if_requested(try_keypair: bool, verbose: bool) -> bool:
    """Tạo Ed25519 keypair nếu yêu cầu, fallback sang cryptography."""
    if not try_keypair:
        return False
    keypair_ok = generate_ed25519_keypair(verbose=verbose)
    if not keypair_ok:
        keypair_ok = try_cryptography_keypair(verbose=verbose)
    return keypair_ok


@otp_bp.route('/load_secret', methods=['GET'])
def load_secret_route():
    """
    ĐỌC SECRET KEY ĐÃ LƯU

      curl http://localhost:5000/load_secret
    
    """
    try:
        cfg = load_secret()
        return jsonify(cfg)
    except FileNotFoundError:
        return jsonify({"error": "Secret file not found"}), 404


@otp_bp.route('/totp', methods=['GET'])
def get_totp():
    """
    LẤY MÃ TOTP HIỆN TẠI (Time-based OTP)
    
      curl http://localhost:5000/totp
      curl "http://localhost:5000/totp?digits=6&period=30"
    
    Tham số trong link:
      digits: Số chữ số (mặc định: 6)
      period: Chu kỳ thời gian (giây, mặc định: 30)
    """
    cfg = load_secret()
    secret = cfg["secret"]
    digits = int(request.args.get('digits', cfg.get("digits", 6)))
    period = int(request.args.get('period', cfg.get("period", 30)))
    
    timestamp = int(time.time())
    code, remaining = totp(secret, timestamp=timestamp, timestep=period, digits=digits)
    return jsonify({"code": code, "remaining": remaining})


@otp_bp.route('/hotp', methods=['GET'])
def get_hotp():
    """
    LẤY MÃ HOTP (HMAC-based OTP)
    
      curl "http://localhost:5000/hotp?counter=1"
      curl "http://localhost:5000/hotp?counter=5&digits=6"
    
    Tham số trong link:
      counter: BẮT BUỘC - số thứ tự của mã
      digits: Số chữ số (mặc định: 6)
    
    """
    cfg = load_secret()
    secret = cfg["secret"]
    counter = request.args.get('counter')
    if counter is None:
        return jsonify({"error": "Counter is required"}), 400
    counter = int(counter)
    digits = int(request.args.get('digits', cfg.get("digits", 6)))
    
    code = hotp(secret, counter, digits)
    return jsonify({"code": code})


@otp_bp.route('/otpauth_uri', methods=['GET'])
def get_otpauth_uri():
    """
    LẤY URI ĐỂ TẠO QR CODE CHO AUTHENTICATOR APPS
    
      curl "http://localhost:5000/otpauth_uri?account=user@gmail.com&issuer=MyApp"
    
    Các tham số trong link:
      account: Tên tài khoản (mặc định: "user@example")
      issuer: Tên ứng dụng (mặc định: "otp-tool") 
      digits: Số chữ số (mặc định: 6)
      period: Chu kỳ TOTP (giây, mặc định: 30)
    
    Copy URI vào https://qrcode-generator.com để tạo QR code
    Quét QR bằng Google Authenticator/Microsoft Authenticator
    """
    cfg = load_secret()
    secret = cfg["secret"]
    digits = int(request.args.get('digits', cfg.get("digits", 6)))
    period = int(request.args.get('period', cfg.get("period", 30)))
    account = request.args.get('account', "user@example")
    issuer = request.args.get('issuer', "otp-tool")
    
    totp_uri, hotp_uri = format_otpauth_uri(secret, account, issuer, digits=digits, period=period)
    return jsonify({"totp_uri": totp_uri, "hotp_uri": hotp_uri})


@otp_bp.route('/verify_totp', methods=['POST'])
def verify_totp_route():
    """
    XÁC MINH MÃ TOTP
    
      curl -X POST http://localhost:5000/verify_totp -H "Content-Type: application/json" -d "{\"code\": \"123456\"}"
    
    Input (JSON body):
      {
        "code": "123456",     # Mã OTP cần xác minh
        "digits": 6,          # Số chữ số
        "period": 30,         # Chu kỳ thời gian
        "window": 1           # Cho phép sai lệch 1 chu kỳ
      }
    
    Output:
      {"valid": true}  hoặc  {"valid": false}
    
    """
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "Code is required"}), 400
    
    cfg = load_secret()
    secret = cfg["secret"]
    code = data["code"]
    digits = data.get('digits', cfg.get("digits", 6))
    period = data.get('period', cfg.get("period", 30))
    window = data.get('window', 1)
    
    valid = verify_totp(secret, code, timestep=period, digits=digits, window=window)
    return jsonify({"valid": valid})


@otp_bp.route('/verify_hotp', methods=['POST'])
def verify_hotp_route():
    """
    XÁC MINH MÃ HOTP
    
      curl -X POST http://localhost:5000/verify_hotp -H "Content-Type: application/json" -d "{\"code\": \"123456\", \"counter\": 1}"
    
    Input :
      {
        "code": "123456",     # BẮT BUỘC - mã OTP cần xác minh
        "counter": 1,         # BẮT BUỘC - counter hiện tại
        "digits": 6,          # Số chữ số
        "look_ahead": 1       # Cho phép counter vượt trước
      }
    
    Output:
      {"valid": true, "new_counter": 2}  # Nếu thành công
      {"valid": false}                   # Nếu thất bại
    
    Look_ahead=1 nghĩa là chấp nhận counter hiện tại hoặc counter+1
    new_counter là counter tiếp theo nên dùng
    """
    data = request.get_json()   
    if not data or "code" not in data or "counter" not in data:
        return jsonify({"error": "Code and counter are required"}), 400
    
    cfg = load_secret()
    secret = cfg["secret"]
    code = data["code"]
    counter = data["counter"]
    digits = data.get('digits', cfg.get("digits", 6))
    look_ahead = data.get('look_ahead', 1)
    
    valid, new_counter = verify_hotp(secret, code, counter, digits=digits, look_ahead=look_ahead)
    if valid:
        return jsonify({"valid": valid, "new_counter": new_counter})
    else:
        return jsonify({"valid": valid})