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
    - Tạo secret mới, lưu vào file JSON (secret + digits + period + algo)
    - Thử tạo keypair
    - In ra TOTP & HOTP URI
    """
    secret = otp_core.generate_base32_secret()
    otp_core.save_secret(secret, digits=args.digits, period=args.period)

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
    Xử lý lệnh `totp`: sinh mã TOTP theo config trong file (hoặc override bằng args).
    """
    cfg = otp_core.load_secret()
    secret = cfg["secret"]
    digits = args.digits or cfg.get("digits", otp_core.DEFAULT_DIGITS)
    period = args.period or cfg.get("period", otp_core.DEFAULT_TIME_STEP)

    print(f"Press Ctrl+C to quit. Generating {digits}-digit TOTP every {period}s...\n")
    last_code = None
    try:
        while True:
            now = int(time.time())
            code, remaining = otp_core.totp(secret, now, period, 0, digits)
            if code != last_code:
                print(f"TOTP ({digits}d): {code}  (valid ~{remaining:2d}s)")
                last_code = code
            else:
                print(f".. {remaining:2d}s left", end='\r', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBye.")


def cmd_hotp(args):
    """
    Xử lý lệnh `hotp`: sinh mã HOTP theo config.
    """
    cfg = otp_core.load_secret()
    secret = cfg["secret"]
    digits = args.digits or cfg.get("digits", otp_core.DEFAULT_DIGITS)

    code = otp_core.hotp(secret, args.counter, digits)
    print(f"HOTP({digits}d, counter={args.counter}): {code}")


def cmd_uri(args):
    """
    In lại URI từ secret + config đã lưu.
    """
    cfg = otp_core.load_secret()
    secret = cfg["secret"]
    digits = cfg.get("digits", otp_core.DEFAULT_DIGITS)
    period = cfg.get("period", otp_core.DEFAULT_TIME_STEP)

    totp_uri, hotp_uri = otp_core.format_otpauth_uri(
        secret, args.account, args.issuer, digits=digits, period=period
    )
    print("TOTP URI:\n", totp_uri)
    print("\nHOTP URI:\n", hotp_uri)


def cmd_help(args):
    print("'python -m otp -h' or 'python -m otp_cli -h' for help.")


def cmd_verify_totp(args):
    """
    Verify TOTP code từ user.
    """
    cfg = otp_core.load_secret()
    secret = cfg["secret"]
    digits = args.digits or cfg.get("digits", otp_core.DEFAULT_DIGITS)
    period = args.period or cfg.get("period", otp_core.DEFAULT_TIME_STEP)

    if digits != otp_core.DEFAULT_DIGITS:
        print(f"[!] Warning: using {digits} digits. "
              f"Ensure your Authenticator app is configured for {digits}-digit codes!")

    ok = otp_core.verify_totp(
        secret,
        args.code,
        timestep=period,
        digits=digits,
        window=args.window,
    )
    if ok:
        print("[+] TOTP code is VALID")
    else:
        print("[-] TOTP code is INVALID")


def cmd_verify_hotp(args):
    """
    Verify HOTP code từ user.
    """
    cfg = otp_core.load_secret()
    secret = cfg["secret"]
    digits = args.digits or cfg.get("digits", otp_core.DEFAULT_DIGITS)

    if digits != otp_core.DEFAULT_DIGITS:
        print(f"[!] Warning: using {digits} digits. "
              f"Ensure your Authenticator app is configured for {digits}-digit codes!")

    ok, new_counter = otp_core.verify_hotp(
        secret,
        args.code,
        args.counter,
        digits=digits,
        look_ahead=args.look_ahead,
    )
    if ok:
        print(f"[+] HOTP code is VALID (next counter = {new_counter})")
    else:
        print("[-] HOTP code is INVALID")


# --- Argparse builder ---
def build_parser() -> argparse.ArgumentParser:
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
    pt.add_argument("--digits", type=int, help="Override number of digits")
    pt.add_argument("--period", type=int, help="Override TOTP period (seconds)")
    pt.set_defaults(func=cmd_totp)

    # hotp
    ph = sub.add_parser("hotp", help="Generate HOTP code for a specific counter")
    ph.add_argument("--counter", type=int, required=True)
    ph.add_argument("--digits", type=int, help="Override number of digits")
    ph.set_defaults(func=cmd_hotp)

    # uri
    pu = sub.add_parser("uri", help="Print otpauth URIs for TOTP/HOTP")
    pu.add_argument("--account", default="user@example")
    pu.add_argument("--issuer", default="otp-tool")
    pu.set_defaults(func=cmd_uri)

    # verify
    pv = sub.add_parser("verify", help="Verify an OTP code (TOTP or HOTP)")
    sub_v = pv.add_subparsers(dest="verify_type")

    pvt = sub_v.add_parser("totp", help="Verify a TOTP code")
    pvt.add_argument("--code", required=True, help="OTP code to verify")
    pvt.add_argument("--digits", type=int, help="Override number of digits")
    pvt.add_argument("--period", type=int, help="Override TOTP period")
    pvt.add_argument("--window", type=int, default=1, help="Allowed +/- step window")
    pvt.set_defaults(func=cmd_verify_totp)

    pvh = sub_v.add_parser("hotp", help="Verify a HOTP code")
    pvh.add_argument("--code", required=True, help="OTP code to verify")
    pvh.add_argument("--counter", type=int, required=True, help="Current HOTP counter")
    pvh.add_argument("--digits", type=int, help="Override number of digits")
    pvh.add_argument("--look-ahead", type=int, default=1, help="Allowed counter look-ahead")
    pvh.set_defaults(func=cmd_verify_hotp)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
