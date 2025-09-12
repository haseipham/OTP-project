"""
OTP BACKEND API ROUTES - VERSION 2 (MULTI-USER)

File này chứa các API endpoints hỗ trợ đa người dùng.
Mỗi endpoint yêu cầu `username` trong URL.

Ví dụ:
- POST /api/v2/init/alice
- GET /api/v2/totp/alice
- POST /api/v2/verify_totp/alice
"""

from flask import Blueprint, jsonify, request
import time
import sys
import os

# Thêm thư mục gốc vào Python path để import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.otp_core import (
    generate_base32_secret,
    save_secret,
    load_secret,
    hotp,
    totp,
    format_otpauth_uri,
    verify_totp,
    verify_hotp,
)

# Tạo Flask Blueprint cho API v2
otp_bp_v2 = Blueprint('otp_v2', __name__, url_prefix='/api/v2')

@otp_bp_v2.route('/init/<string:user>', methods=['POST'])
def init_user(user):
    """
    Tạo secret key cho một user cụ thể.
    Endpoint: POST /api/v2/init/<username>
    """
    data = request.get_json() or {}
    digits = data.get('digits', 6)
    period = data.get('period', 30)
    issuer = data.get('issuer', 'MyWebApp')
    
    secret = generate_base32_secret()
    save_secret(secret, user=user, digits=digits, period=period)
    
    # Tạo URI để client có thể hiển thị QR code
    totp_uri, _ = format_otpauth_uri(
        secret,
        account=user,
        issuer=issuer,
        digits=digits,
        period=period
    )
    
    return jsonify({
        "message": f"Secret created for user '{user}'",
        "secret": secret,
        "totp_uri": totp_uri
    })

@otp_bp_v2.route('/totp/<string:user>', methods=['GET'])
def get_totp_for_user(user):
    """
    Lấy mã TOTP hiện tại cho một user.
    Endpoint: GET /api/v2/totp/<username>
    """
    try:
        cfg = load_secret(user)
    except FileNotFoundError:
        return jsonify({"error": f"User '{user}' not found. Please initialize first."}), 404

    secret = cfg["secret"]
    digits = cfg.get("digits", 6)
    period = cfg.get("period", 30)
    
    timestamp = int(time.time())
    code, remaining = totp(secret, timestamp=timestamp, timestep=period, digits=digits)
    
    return jsonify({
        "code": code,
        "remaining": remaining,
        "period": period,
        "user": user
    })

@otp_bp_v2.route('/verify_totp/<string:user>', methods=['POST'])
def verify_totp_for_user(user):
    """
    Xác minh mã TOTP cho một user.
    Endpoint: POST /api/v2/verify_totp/<username>
    Body: { "code": "123456" }
    """
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "OTP code is required in JSON body"}), 400

    try:
        cfg = load_secret(user)
    except FileNotFoundError:
        return jsonify({"error": f"User '{user}' not found."}), 404

    secret = cfg["secret"]
    period = cfg.get("period", 30)
    digits = cfg.get("digits", 6)
    
    is_valid = verify_totp(
        secret_b32=secret,
        code=data["code"],
        user=user,
        timestep=period,
        digits=digits,
        window=1 # Cho phép sai lệch 1 khoảng thời gian (30s)
    )
    
    return jsonify({"valid": is_valid})

@otp_bp_v2.route('/otpauth_uri/<string:user>', methods=['GET'])
def get_otpauth_uri_for_user(user):
    """
    Lấy URI để tạo QR code cho một user.
    Endpoint: GET /api/v2/otpauth_uri/<username>
    """
    try:
        cfg = load_secret(user)
    except FileNotFoundError:
        return jsonify({"error": f"User '{user}' not found."}), 404

    secret = cfg["secret"]
    digits = cfg.get("digits", 6)
    period = cfg.get("period", 30)
    issuer = request.args.get('issuer', 'MyWebApp')
    
    totp_uri, hotp_uri = format_otpauth_uri(secret, user, issuer, digits=digits, period=period)
    return jsonify({"totp_uri": totp_uri, "hotp_uri": hotp_uri, "user": user})