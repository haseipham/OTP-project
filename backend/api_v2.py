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
# Import database functions
from database.db_manager import (
    add_new_user,
    verify_user_credentials,
    get_user_secret,
    get_user_id,
    user_exists,
    log_otp_attempt
)


# Tạo Flask Blueprint cho API v2
otp_bp_v2 = Blueprint('otp_v2', __name__, url_prefix='/api/v2')

# Thêm endpoints mới
@otp_bp_v2.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400

    username = data['username']
    password = data['password']
    email = data.get('email', '')
    phone = data.get('phone', '')

        # Kiểm tra user đã tồn tại chưa
    if user_exists(username):
        return jsonify({"error": "User already exists"}), 400

    success, result = add_new_user(username, password, email, phone)
        
    if not success:
        return jsonify({"error": result}), 400

    secret = get_user_secret(username)

    if not secret:
        return jsonify({"error": "Failed to generate OTP secret"}), 500
    

    save_secret(secret, user=username, digits=6, period=30)
        # Tạo URI để hiển thị QR code
    totp_uri, hotp_uri = format_otpauth_uri(
        secret, 
        account=username, 
        issuer="MyWebApp", 
        digits=6, 
        period=30
    )

    return jsonify({
        "message": "User created successfully",
        "otp_secret": secret,
        "otp_uri": totp_uri,
        "user": username
    }), 201

@otp_bp_v2.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400

    username = data['username']
    password = data['password']

    if not verify_user_credentials(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "message": "OTP required",
        "user": username
    }), 200


#endpoint cũ
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

@otp_bp_v2.route('/qr_code/<string:user>', methods=['GET'])
def get_qr_code_for_user(user):
    """
    Tạo QR code image cho một user.
    Endpoint: GET /api/v2/qr_code/<username>
    """
    try:
        cfg = load_secret(user)
    except FileNotFoundError:
        return jsonify({"error": f"User '{user}' not found."}), 404

    secret = cfg["secret"]
    digits = cfg.get("digits", 6)
    period = cfg.get("period", 30)
    issuer = request.args.get('issuer', 'MyWebApp')
    
    totp_uri, _ = format_otpauth_uri(secret, user, issuer, digits=digits, period=period)
    
    try:
        import qrcode
        import io
        import base64
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            "qr_code": f"data:image/png;base64,{img_str}",
            "user": user
        })
        
    except ImportError:
        return jsonify({"error": "QR code library not available"}), 500
    except Exception as e:
        return jsonify({"error": f"Error generating QR code: {str(e)}"}), 500

@otp_bp_v2.route('/demo_qr', methods=['POST'])
def generate_demo_qr():
    """
    Generate QR code for demo purposes.
    Endpoint: POST /api/v2/demo_qr
    Body: {"secret": "JBSWY3DPEHPK3PXP", "issuer": "Demo App", "account": "user@example.com"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON data required"}), 400
    
    secret = data.get('secret', 'JBSWY3DPEHPK3PXP')
    issuer = data.get('issuer', 'Demo App')
    account = data.get('account', 'user@example.com')
    
    # Create otpauth URI
    totp_uri = f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}"
    
    try:
        import qrcode
        import io
        import base64
        
        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            "qr_code": f"data:image/png;base64,{img_str}",
            "uri": totp_uri,
            "secret": secret,
            "issuer": issuer,
            "account": account
        })
        
    except ImportError:
        return jsonify({"error": "QR code library not available"}), 500
    except Exception as e:
        return jsonify({"error": f"Error generating QR code: {str(e)}"}), 500

@otp_bp_v2.route('/demo_totp', methods=['POST'])
def generate_demo_totp():
    """
    Generate TOTP code for demo purposes using the core algorithm.
    Endpoint: POST /api/v2/demo_totp
    Body: {"secret": "JBSWY3DPEHPK3PXP"}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON data required"}), 400
    
    secret = data.get('secret', 'JBSWY3DPEHPK3PXP')
    
    try:
        from core.otp_core import totp
        import time
        
        # Generate TOTP using the core algorithm
        timestamp = int(time.time())
        code, remaining = totp(secret, timestamp=timestamp, timestep=30, digits=6)
        
        return jsonify({
            "otp_code": code,
            "remaining": remaining,
            "secret": secret,
            "timestamp": timestamp
        })
        
    except Exception as e:
        return jsonify({"error": f"Error generating TOTP: {str(e)}"}), 500