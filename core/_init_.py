"""
otp_generator package
=====================

Công cụ tạo và xác minh OTP (HOTP/TOTP) theo chuẩn RFC 4226 & RFC 6238,
kèm tiện ích tạo cặp khóa Ed25519.

__author__: Desold
__time__: 08/09/2025
──────────────────────────────────────────────
Giải thuật cốt lõi
──────────────────────────────────────────────
- HOTP (HMAC-based One-Time Password):
  code = Truncate(HMAC-SHA1(key=secret, msg=counter)) mod 10^digits
  → Counter tăng dần (dùng cho token event-based).

- TOTP (Time-based One-Time Password):
  HOTP với counter = floor((timestamp - T0) / timestep)
  → Mặc định timestep = 30 giây (mã thay đổi 30s/lần).
  → RFC 6238 khuyến nghị 6 chữ số, SHA-1, 30s.

- Dynamic Truncation:
  Lấy 4 byte từ HMAC dựa vào offset (last byte & 0x0F).
  Đảm bảo code sinh ra pseudo-random và bảo mật.

──────────────────────────────────────────────
Hướng dẫn dành cho các nhóm dev
──────────────────────────────────────────────

1. Backend Developers
   - Import trực tiếp hàm `totp` hoặc `hotp` để xác minh user login 2FA.
   - Ví dụ:
        from otp_generator import load_secret, totp
        code, remaining = totp(load_secret())
        if user_input == code: login_ok = True

2. Frontend Developers
   - Tạo QR code từ otpauth URI để user scan bằng Google Authenticator.
   - Ví dụ:
        from otp_generator import format_otpauth_uri, load_secret
        uri, _ = format_otpauth_uri(load_secret(), "alice@example", "otp-demo")
        # Dùng thư viện qrcode để render QR cho URI này.

3. API Developers
   - Wrap hàm core thành REST/gRPC service.
   - Ví dụ FastAPI:
        @app.get("/totp")
        def get_totp():
            code, remain = totp(load_secret())
            return {"code": code, "valid_for": remain}

4. Database Administrators
   - Chỉ cần lưu secret (Base32) trong SQLite hoặc file.
   - Không lưu mã OTP động (chúng chỉ có hiệu lực vài chục giây).
   - Có thể dùng:
        from otp_generator import save_secret, load_secret

──────────────────────────────────────────────
Ví dụ sử dụng nhanh
──────────────────────────────────────────────
>>> from otp_generator import generate_base32_secret, save_secret, totp
>>> secret = generate_base32_secret()
>>> save_secret(secret)
>>> code, remaining = totp(secret)
>>> print("Mã TOTP:", code, "còn hiệu lực", remaining, "giây")
"""
# Can be imported as: from otp_generator import <func>
from otp_generator import (
    generate_base32_secret,
    save_secret,
    load_secret,
    hotp,
    totp,
    format_otpauth_uri,
    main,
)