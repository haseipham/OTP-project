#!/usr/bin/env python3
"""
otp_core.py — Core library cho TOTP / HOTP + helper tạo keypair Ed25519.

Mục tiêu:
- Chứa các hàm thuần (pure functions / helper) để dùng trực tiếp bởi WebUI/REST API.
- Không chứa argparse / CLI loop — CLI có thể ở file riêng nếu cần.
- Giải thích chi tiết từng hàm trong docstring / comment.

Lưu ý bảo mật:
- Giữ file SECRET và private key ở nơi an toàn (chmod 600), không commit lên VCS.
- Thư viện sử dụng HMAC-SHA1 theo RFC4226/6238 (phổ biến cho Google Authenticator).
"""

from typing import Tuple
import base64
import binascii
import hmac
import hashlib
import os
import struct
import time
import shutil
import subprocess

# --- Config / constants ----------------------------------------------------
DEFAULT_DIGITS = 6          # chuẩn: 6 chữ số
DEFAULT_TIME_STEP = 30      # TOTP step (giây)
SECRET_BYTES = 20           # 160-bit secret (common practice)
SECRET_FILE = "otp_secret.txt"
PRIV_KEY_FILE = "ed25519_key"
PUB_KEY_FILE = PRIV_KEY_FILE + ".pub"
USED_OTP_FILE = "otp_used_codes.txt"



# --- Utility / I/O ---------------------------------------------------------
def generate_base32_secret() -> str:
    """
    Sinh một secret ngẫu nhiên, trả về Base32 (chuỗi, không có padding).

    - SECRET_BYTES bytes được sinh từ os.urandom (CSPRNG).
    - Mã hóa Base32 để dễ import vào Google Authenticator / Authy.
    - Trả về string in hoa (base64.b32encode trả chuỗi hoa theo chuẩn).

    Trả về:
        str: Base32 secret (ví dụ "JBSWY3DPEHPK3PXP")
    """
    raw = os.urandom(SECRET_BYTES)
    # b32 string mặc định có padding '=' — .strip() loại bỏ padding (thường chấp nhận được)
    b32 = base64.b32encode(raw).decode("ascii").strip()
    return b32


def save_secret(secret_b32: str, path: str = SECRET_FILE) -> None:
    """
    Lưu secret Base32 vào file (một dòng).

    - Nếu file đã tồn tại, tạo backup path + ".bak".
    - Viết text mode, newline ở cuối.
    - Không thay đổi permission file ở đây (tùy hệ thống), nhưng khuyến nghị chmod 600 nếu cần.

    Arguments:
        secret_b32: Base32 secret
        path: đường dẫn file để lưu (mặc định SECRET_FILE)
    """
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(secret_b32 + "\n")


def load_secret(path: str = SECRET_FILE) -> str:
    """
    Đọc và trả về secret Base32 từ file.

    - Raises FileNotFoundError nếu file không tồn tại.
    - Trả về chuỗi đã strip() (loại whitespace/newline).

    Arguments:
        path: đường dẫn file chứa secret
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# --- RFC helpers -----------------------------------------------------------
def int_to_bytes(i: int) -> bytes:
    """
    Chuyển integer (counter) sang 8-byte big-endian như RFC4226 yêu cầu.

    Ví dụ: int_to_bytes(1) -> b'\x00\x00\x00\x00\x00\x00\x00\x01'
    """
    return struct.pack(">Q", i)


def dynamic_truncate(hmac_digest: bytes) -> int:
    """
    Áp dụng dynamic truncation theo RFC4226.

    - Lấy offset = last_byte & 0x0F
    - Lấy 4 bytes từ offset, clear MSB (0x7F) cho byte đầu
    - Trả về integer 31-bit (unsigned)

    Arguments:
        hmac_digest: digest của HMAC (SHA1 -> 20 bytes)
    Raises:
        IndexError: nếu hmac_digest ngắn hơn 4 + offset (không hợp lệ)
    """
    # offset in range 0..15 (vì SHA1 digest length 20)
    offset = hmac_digest[-1] & 0x0F
    # compose 31-bit integer theo RFC (clear sign bit)
    code = (
        ((hmac_digest[offset] & 0x7F) << 24)
        | ((hmac_digest[offset + 1] & 0xFF) << 16)
        | ((hmac_digest[offset + 2] & 0xFF) << 8)
        | (hmac_digest[offset + 3] & 0xFF)
    )
    return code


def hotp(secret_b32: str, counter: int, digits: int = DEFAULT_DIGITS) -> str:
    """
    Sinh mã HOTP theo RFC4226.

    Steps:
    1. Base32-decode secret -> raw key bytes
    2. Message = 8-byte counter (big-endian)
    3. HMAC-SHA1(key, message)
    4. Dynamic truncate -> dbc
    5. otp = dbc % 10^digits
    6. Zero-pad để có đúng "digits" chữ số

    Arguments:
        secret_b32: Base32 secret
        counter: integer counter (non-negative)
        digits: số chữ số OTP (khuyến nghị 6)

    Trả về:
        str: mã HOTP dạng zero-padded

    Raises:
        ValueError: nếu secret Base32 không hợp lệ
    """
    # Decode Base32 (case-insensitive)
    try:
        key = base64.b32decode(secret_b32, casefold=True)
    except binascii.Error as e:
        raise ValueError("Invalid Base32 secret") from e

    # Message là 8 byte big-endian từ counter
    msg = int_to_bytes(counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()

    dbc = dynamic_truncate(digest)
    otp_val = dbc % (10 ** digits)
    # zero-pad
    return str(otp_val).zfill(digits)


def totp(
    secret_b32: str,
    timestamp: int = None,
    timestep: int = DEFAULT_TIME_STEP,
    t0: int = 0,
    digits: int = DEFAULT_DIGITS,
) -> Tuple[str, int]:
    """
    Sinh mã TOTP theo RFC6238, process cơ bản dùng HOTP(counter = floor((now - T0)/X)).

    Arguments:
        secret_b32: Base32 secret
        timestamp: epoch seconds để tính (nếu None -> dùng time.time())
        timestep: X (giây), mặc định 30
        t0: start time offset, mặc định 0
        digits: số chữ số OTP

    Trả về:
        (code, remaining_seconds)
        - code: OTP string
        - remaining_seconds: số giây còn lại cho mã hiện tại

    Ghi chú:
        - Hàm không đọc/ghi file; chỉ tính toán trên secret được truyền vào.
    """
    if timestamp is None:
        timestamp = int(time.time())
    # counter hiện tại theo TOTP
    counter = (timestamp - t0) // timestep
    code = hotp(secret_b32, counter, digits)
    remaining = int(timestep - ((timestamp - t0) % timestep))
    return code, remaining


def format_otpauth_uri(
    secret_b32: str,
    account: str,
    issuer: str,
    algo: str = "SHA1",
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_TIME_STEP,
) -> Tuple[str, str]:
    """
    Tạo otpauth:// URI cho TOTP và HOTP — dễ import vào ứng dụng Authenticator.

    - TOTP URI: otpauth://totp/{issuer}:{account}?secret=...&issuer=...&algorithm=...&digits=...&period=...
    - HOTP URI:  otpauth://hotp/{issuer}:{account}?secret=...&issuer=...&algorithm=...&digits=...&counter=0

    Arguments:
        secret_b32: Base32 secret
        account: label account (ví dụ 'alice@example.com')
        issuer: issuer label (ví dụ 'MyService')
        algo: 'SHA1' (mặc định). (RFC cho phép SHA1/256/512 các giá trị khác)
        digits: số chữ số
        period: timestep (giây) cho TOTP

    Trả về:
        (totp_uri, hotp_uri)
    """
    # Note: không encode các ký tự đặc biệt ở account/issuer ở đây — caller có thể urlencode nếu cần
    totp_uri = (
        f"otpauth://totp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}"
        f"&algorithm={algo}&digits={digits}&period={period}"
    )
    hotp_uri = (
        f"otpauth://hotp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}"
        f"&algorithm={algo}&digits={digits}&counter=0"
    )
    return totp_uri, hotp_uri


# --- Ed25519 keypair helpers (optional) -----------------------------------
def have_ssh_keygen() -> bool:
    """
    Kiểm tra xem hệ thống có `ssh-keygen` (OpenSSH) trong PATH hay không.
    Dùng để quyết định fallback generation method.
    """
    return shutil.which("ssh-keygen") is not None


def generate_ed25519_keypair(verbose: bool = False) -> bool:
    """
    Thử dùng `ssh-keygen` để sinh Ed25519 keypair.

    Behavior:
    - Nếu ssh-keygen có sẵn:
      - Nếu file private tồn tại: backup thành .bak
      - Gọi: ssh-keygen -t ed25519 -N "" -f PRIV_KEY_FILE -C "otp-tool"
      - Trả về True nếu thành công.
    - Nếu ssh-keygen không có, trả về False (caller có thể thử try_cryptography_keypair).

    Arguments:
        verbose: nếu True sẽ in log đơn giản ra stdout (không dùng logging module)

    Trả về:
        bool: True nếu đã tạo thành công bằng ssh-keygen, False nếu không thể.
    """
    if not have_ssh_keygen():
        if verbose:
            print("[*] ssh-keygen not found, skipping ssh-keygen-based key generation")
        return False

    # backup nếu tồn tại
    if os.path.exists(PRIV_KEY_FILE):
        shutil.copy2(PRIV_KEY_FILE, PRIV_KEY_FILE + ".bak")
        if os.path.exists(PUB_KEY_FILE):
            shutil.copy2(PUB_KEY_FILE, PUB_KEY_FILE + ".bak")

    cmd = ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", PRIV_KEY_FILE, "-C", "otp-tool"]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # ssh-keygen tự tạo file với permission phù hợp (600)
        if verbose:
            print(f"[*] Generated {PRIV_KEY_FILE} and {PUB_KEY_FILE} via ssh-keygen")
        return True
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"[!] ssh-keygen failed: {e}")
        return False


def try_cryptography_keypair(verbose: bool = False) -> bool:
    """
    Fallback: tạo Ed25519 keypair bằng Python `cryptography` nếu library có sẵn.

    Behavior:
    - Nếu cryptography không cài, trả về False.
    - Nếu có: tạo PKCS8 PEM private + OpenSSH public, lưu ra file.
    - Thiết lập permission private key thành 0o600 để an toàn.

    Trả về:
        bool: True nếu viết file thành công, False nếu lỗi / package chưa cài.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
    except Exception:
        if verbose:
            print("[*] Python package 'cryptography' not available — cannot generate keypair")
        return False

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Private key in PEM, PKCS8 (no encryption)
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    # Public in OpenSSH authorized_keys format
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    with open(PRIV_KEY_FILE, "wb") as f:
        f.write(priv_bytes)
    # Set permission to 600 for private key
    try:
        os.chmod(PRIV_KEY_FILE, 0o600)
    except Exception:
        # Không fatal nếu chmod không được phép trên một số FS, nhưng nên log nếu verbose
        if verbose:
            print("[!] Warning: unable to chmod private key file to 600")

    with open(PUB_KEY_FILE, "wb") as f:
        f.write(pub_bytes)

    if verbose:
        print(f"[*] Generated {PRIV_KEY_FILE} (PEM PKCS8) and {PUB_KEY_FILE} (OpenSSH) via cryptography")
    return True

# --- OTP verification helpers ---------------------------------------------

def _load_used_otps(path: str = USED_OTP_FILE) -> set:
    """Đọc file chứa các mã OTP đã dùng, trả về set."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def _save_used_otps(used: set, path: str = USED_OTP_FILE) -> None:
    """Ghi set các OTP đã dùng xuống file."""
    with open(path, "w", encoding="utf-8") as f:
        for code in used:
            f.write(code + "\n")

def verify_totp(secret_b32: str, code: str,
                timestep: int = DEFAULT_TIME_STEP,
                digits: int = DEFAULT_DIGITS,
                window: int = 1, t0: int = 0,
                timestamp: int = None,
                block_reuse: bool = True) -> bool:
    """
    Xác minh mã TOTP do user nhập (theo RFC6238), kèm cơ chế block mã đã dùng.
    """
    if timestamp is None:
        timestamp = int(time.time())

    # chặn reuse
    if block_reuse:
        used = _load_used_otps()
        if code in used:
            return False  # đã dùng rồi

    counter = (timestamp - t0) // timestep
    for offset in range(-window, window + 1):
        test_counter = counter + offset
        if test_counter < 0:
            continue
        expected = hotp(secret_b32, test_counter, digits)
        if hmac.compare_digest(expected, code):
            if block_reuse:
                used.add(code)
                _save_used_otps(used)
            return True
    return False
def verify_hotp(secret_b32: str, code: str, counter: int,
                digits: int = DEFAULT_DIGITS, look_ahead: int = 1,
                block_reuse: bool = True) -> Tuple[bool, int]:
    """
    Xác minh mã HOTP do user nhập, kèm cơ chế block mã đã dùng.
    """
    # chặn reuse
    if block_reuse:
        used = _load_used_otps()
        if code in used:
            return False, counter

    for i in range(look_ahead + 1):
        expected = hotp(secret_b32, counter + i, digits)
        if hmac.compare_digest(expected, code):
            if block_reuse:
                used.add(code)
                _save_used_otps(used)
            return True, counter + i + 1
    return False, counter

# --- Example usage helpers (dành cho WebUI) -------------------------------
def init_secret_and_keypair(
    account: str = "user@example",
    issuer: str = "otp-tool",
    digits: int = DEFAULT_DIGITS,
    period: int = DEFAULT_TIME_STEP,
    try_keypair: bool = True,
    verbose: bool = False,
) -> Tuple[str, str]:
    """
    Tiện ích gộp: tạo secret mới, lưu vào SECRET_FILE, cố gắng tạo keypair (ssh-keygen hoặc cryptography),
    và trả về otpauth URIs.

    Trả về:
        (totp_uri, hotp_uri)

    Ghi chú: hàm này tiện để gọi từ route '/init' trong WebUI; caller có thể bắt exceptions I/O nếu cần.
    """
    secret = generate_base32_secret()
    save_secret(secret)
    ok = False
    if try_keypair:
        ok = generate_ed25519_keypair(verbose=verbose)
        if not ok:
            ok = try_cryptography_keypair(verbose=verbose)
    if verbose and not ok:
        print("[!] Keypair not created (no ssh-keygen and no cryptography).")

    totp_uri, hotp_uri = format_otpauth_uri(secret, account=account, issuer=issuer, digits=digits, period=period)
    return totp_uri, hotp_uri


# If this module is executed directly, do nothing — it's core-only for import.
if __name__ == "__main__":
    print("otp_core.py is a library module. Import it from your WebUI backend instead of executing directly.")
