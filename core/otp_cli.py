#!/usr/bin/env python3
"""
otp_cli.py — CLI wrapper cho otp_core.py

Cung cấp các subcommand:
- init : tạo secret + keypair, in ra otpauth URIs
- totp : hiển thị mã TOTP theo thời gian thực
- hotp : sinh mã HOTP với counter cụ thể
- uri  : in ra otpauth URIs từ secret đã lưu
"""

import argparse
import time
import otp_core  # import toàn bộ logic từ file core

# --- CLI command handlers ---
def cmd_init(args):
    """
    Xử lý lệnh `init`:
    - Tạo secret mới, lưu vào file
    - Thử tạo keypair (ssh-keygen / cryptography)
    - In ra TOTP & HOTP URI
    """
    secret = otp_core.generate_base32_secret()
    otp_core.save_secret(secret)

    # thử tạo keypair
    ok = otp_core.generate_ed25519_keypair(verbose=args.verbose)
    if not ok:
        ok = otp_core.try_cryptography_keypair(verbose=args.verbose)
    if not ok:
        print("[!] Could not generate Ed25519 keypair. Install OpenSSH (ssh-keygen) or 'cryptography'.")

    totp_uri, hotp_uri = otp_core.format_otpauth_uri(
        secret, account=args.account, issuer=args.issuer,
        digits=args.digits, period=args.period
    )
    print("[*] otpauth URIs (import into authenticator apps):")
    print("    TOTP:", totp_uri)
    print("    HOTP:", hotp_uri)


def cmd_totp(args):
    """
    Xử lý lệnh `totp`:
    - Load secret từ file
    - Liên tục sinh mã TOTP theo thời gian thực
    - In ra mỗi khi mã thay đổi
    """
    secret = otp_core.load_secret()
    print("Press Ctrl+C to quit. Generating TOTP in real time...\n")
    last_code = None
    try:
        while True:
            now = int(time.time())
            code, remaining = otp_core.totp(secret, now, args.period, 0, args.digits)
            if code != last_code:
                print(f"TOTP: {code}  (valid ~{remaining:2d}s)")
                last_code = code
            else:
                print(f".. {remaining:2d}s left", end='\r', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBye.")


def cmd_hotp(args):
    """
    Xử lý lệnh `hotp`:
    - Load secret từ file
    - Sinh mã HOTP cho counter chỉ định
    """
    secret = otp_core.load_secret()
    code = otp_core.hotp(secret, args.counter, args.digits)
    print(f"HOTP(counter={args.counter}): {code}")


def cmd_uri(args):
    """
    Xử lý lệnh `uri`:
    - Load secret từ file
    - In ra TOTP & HOTP otpauth URI
    """
    secret = otp_core.load_secret()
    totp_uri, hotp_uri = otp_core.format_otpauth_uri(
        secret, args.account, args.issuer, digits=args.digits, period=args.period
    )
    print("TOTP URI:")
    print(totp_uri)
    print("\nHOTP URI:")
    print(hotp_uri)

def cmd_help(args):
    print("'python -m otp -h' or 'python -m otp_cli -h' for help.")

# --- Argparse builder ---
def build_parser() -> argparse.ArgumentParser:
    """
    Tạo argparse parser với các subcommand:
    - init, totp, hotp, uri
    """
    p = argparse.ArgumentParser(description="TOTP/HOTP generator CLI (wrapper for otp_core.py)")
    sub = p.add_subparsers(dest="cmd")
    p.set_defaults(func=cmd_help)

    # init
    pi = sub.add_parser("init", help="Generate OTP secret + Ed25519 keypair, print otpauth URIs")
    pi.add_argument("--account", default="user@example", help="Account label for otpauth URI")
    pi.add_argument("--issuer", default="otp-tool", help="Issuer label for otpauth URI")
    pi.add_argument("--digits", type=int, default=otp_core.DEFAULT_DIGITS, help="Number of OTP digits")
    pi.add_argument("--period", type=int, default=otp_core.DEFAULT_TIME_STEP, help="TOTP time step (seconds)")
    pi.add_argument("--verbose", action="store_true", help="Verbose output")
    pi.set_defaults(func=cmd_init)

    # totp
    pt = sub.add_parser("totp", help="Show TOTP code in real time")
    pt.add_argument("--digits", type=int, default=otp_core.DEFAULT_DIGITS)
    pt.add_argument("--period", type=int, default=otp_core.DEFAULT_TIME_STEP)
    pt.set_defaults(func=cmd_totp)

    # hotp
    ph = sub.add_parser("hotp", help="Generate HOTP code for a specific counter")
    ph.add_argument("--counter", type=int, required=True)
    ph.add_argument("--digits", type=int, default=otp_core.DEFAULT_DIGITS)
    ph.set_defaults(func=cmd_hotp)

    # uri
    pu = sub.add_parser("uri", help="Print otpauth URIs for TOTP/HOTP")
    pu.add_argument("--account", default="user@example")
    pu.add_argument("--issuer", default="otp-tool")
    pu.add_argument("--digits", type=int, default=otp_core.DEFAULT_DIGITS)
    pu.add_argument("--period", type=int, default=otp_core.DEFAULT_TIME_STEP)
    pu.set_defaults(func=cmd_uri)

    return p


def main():
    """Entry point CLI: parse args và gọi hàm tương ứng."""
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
