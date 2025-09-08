#!/usr/bin/env python3
"""
otp_generator.py — TOTP & HOTP generator using HMAC‑SHA1, with verbose mode
and optional keypair generation. No third‑party Python deps required.

Features:
- Generate a Base32 OTP secret (private), save to otp_secret.txt
- Show real‑time TOTP codes (RFC 6238, SHA‑1, 30s step, 6 digits)
- Generate HOTP codes (RFC 4226) for a given counter
- Create an Ed25519 keypair via `ssh-keygen` if available, else try `cryptography`
- Verbose logging of each step

Usage examples:
  # 1) Initialize: create OTP secret + keypair files
  python otp_generator.py init --verbose

  # 2) Show real‑time TOTP (auto refresh)
  python otp_generator.py totp --verbose

  # 3) HOTP for a specific counter
  python otp_generator.py hotp --counter 42 --verbose

  # 4) Print otpauth URIs to import into authenticator apps
  python otp_generator.py uri

Files produced:
  - otp_secret.txt (Base32 secret for TOTP/HOTP)
  - ed25519_key  (private key, OpenSSH PEM)
  - ed25519_key.pub (public key, OpenSSH format)

Security note:
  Keep otp_secret.txt and the private key file secret. Do not sync them publicly.
"""

import argparse # command-line parsing (help messages, subcommands)
import base64
import binascii
import hmac
import hashlib
import os
import struct
import sys
import time
import shutil
import subprocess
from typing import Tuple

DEFAULT_DIGITS = 6
DEFAULT_TIME_STEP = 30  # seconds
SECRET_BYTES = 20       # 160‑bit secret as per common practice
SECRET_FILE = "otp_secret.txt"
PRIV_KEY_FILE = "ed25519_key"
PUB_KEY_FILE = PRIV_KEY_FILE + ".pub"


def log(msg: str, verbose: bool):
    if verbose:
        print(f"[+] {msg}")


def generate_base32_secret(verbose: bool) -> str:
    raw = os.urandom(SECRET_BYTES)
    b32 = base64.b32encode(raw).decode('ascii').strip()
    log(f"Generated {SECRET_BYTES*8}-bit secret (Base32): {b32}", verbose)
    return b32


def save_secret(secret_b32: str, verbose: bool, path: str = SECRET_FILE) -> None:
    if os.path.exists(path):
        log(f"{path} exists — keeping a backup at {path}.bak", verbose)
        shutil.copy2(path, path + ".bak")
    with open(path, 'w') as f:
        f.write(secret_b32 + "\n")
    log(f"Secret saved to {path}", verbose)


def load_secret(path: str = SECRET_FILE) -> str:
    with open(path, 'r') as f:
        return f.read().strip()


def int_to_bytes(i: int) -> bytes:
    # HOTP/TOTP use an 8‑byte counter (big‑endian)
    return struct.pack('>Q', i)


def dynamic_truncate(hmac_digest: bytes) -> int:
    # RFC 4226 dynamic truncation
    offset = hmac_digest[-1] & 0x0F
    code = ((hmac_digest[offset] & 0x7F) << 24 |
            (hmac_digest[offset + 1] & 0xFF) << 16 |
            (hmac_digest[offset + 2] & 0xFF) << 8 |
            (hmac_digest[offset + 3] & 0xFF))
    return code


def hotp(secret_b32: str, counter: int, digits: int = DEFAULT_DIGITS, verbose: bool = False) -> str:
    try:
        key = base64.b32decode(secret_b32, casefold=True)
    except binascii.Error as e:
        raise ValueError("Invalid Base32 secret") from e
    msg = int_to_bytes(counter)
    log(f"HOTP: HMAC‑SHA1(key=secret, msg=counter={counter})", verbose)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    dbc = dynamic_truncate(digest)
    otp = dbc % (10 ** digits)
    code = str(otp).zfill(digits)
    log(f"HOTP raw dbc={dbc} -> code={code}", verbose)
    return code


def totp(secret_b32: str, timestamp: int = None, timestep: int = DEFAULT_TIME_STEP,
         t0: int = 0, digits: int = DEFAULT_DIGITS, verbose: bool = False) -> Tuple[str, int]:
    if timestamp is None:
        timestamp = int(time.time())
    counter = (timestamp - t0) // timestep
    code = hotp(secret_b32, counter, digits, verbose)
    remaining = timestep - ((timestamp - t0) % timestep)
    log(f"TOTP: time={timestamp}, counter={counter}, remaining={remaining}s", verbose)
    return code, remaining


def format_otpauth_uri(secret_b32: str, account: str, issuer: str,
                       algo: str = "SHA1", digits: int = DEFAULT_DIGITS,
                       period: int = DEFAULT_TIME_STEP) -> Tuple[str, str]:
    # TOTP URI
    totp_uri = (
        f"otpauth://totp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}"
        f"&algorithm={algo}&digits={digits}&period={period}"
    )
    # HOTP URI (counter must be provided by the verifier side)
    hotp_uri = (
        f"otpauth://hotp/{issuer}:{account}?secret={secret_b32}&issuer={issuer}"
        f"&algorithm={algo}&digits={digits}&counter=0"
    )
    return totp_uri, hotp_uri


def have_ssh_keygen() -> bool:
    return shutil.which("ssh-keygen") is not None


def generate_ed25519_keypair(verbose: bool) -> bool:
    """Generate Ed25519 keypair using ssh-keygen if available.
    Returns True on success, False otherwise.
    """
    if not have_ssh_keygen():
        log("ssh-keygen not found in PATH — skipping OpenSSH key generation.", verbose)
        return False

    if os.path.exists(PRIV_KEY_FILE):
        log(f"Existing {PRIV_KEY_FILE} detected — creating backup.", verbose)
        shutil.copy2(PRIV_KEY_FILE, PRIV_KEY_FILE + ".bak")
        if os.path.exists(PUB_KEY_FILE):
            shutil.copy2(PUB_KEY_FILE, PUB_KEY_FILE + ".bak")

    cmd = [
        "ssh-keygen", "-t", "ed25519", "-N", "", "-f", PRIV_KEY_FILE, "-C", "otp-tool"
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log(f"Generated {PRIV_KEY_FILE} (private) and {PUB_KEY_FILE} (public)", verbose)
        return True
    except subprocess.CalledProcessError as e:
        log(f"ssh-keygen failed: {e}", verbose)
        return False


def try_cryptography_keypair(verbose: bool) -> bool:
    """Fallback: generate Ed25519 keypair using the cryptography library if installed.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
    except Exception as e:  # lib not installed
        log("Python package 'cryptography' not available — cannot generate keypair.", verbose)
        return False

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    with open(PRIV_KEY_FILE, 'wb') as f:
        f.write(priv_bytes)
    with open(PUB_KEY_FILE, 'wb') as f:
        f.write(pub_bytes)
    log(f"Generated {PRIV_KEY_FILE} (private) and {PUB_KEY_FILE} (public) via cryptography.", verbose)
    return True


# --- CLI ---
def cmd_help(args):
    print("No command specified. Use -h for help.")

def cmd_init(args):
    secret = generate_base32_secret(args.verbose)
    save_secret(secret, args.verbose)

    ok = generate_ed25519_keypair(args.verbose)
    if not ok:
        # fallback attempt with cryptography
        ok = try_cryptography_keypair(args.verbose)
    if not ok:
        print("[!] Could not generate Ed25519 keypair. Install OpenSSH (ssh-keygen) or 'cryptography'.")

    totp_uri, hotp_uri = format_otpauth_uri(
        secret, account=args.account, issuer=args.issuer,
        digits=args.digits, period=args.period
    )
    print("[*] otpauth URIs (import into authenticator apps):")
    print("    TOTP:", totp_uri)
    print("    HOTP:", hotp_uri)


def cmd_totp(args):
    secret = load_secret()
    print("Press Ctrl+C to quit. Generating TOTP in real time...\n")
    last_code = None
    try:
        while True:
            now = int(time.time())
            code, remaining = totp(secret, now, args.period, 0, args.digits, args.verbose)
            if code != last_code:
                print(f"TOTP: {code}  (valid ~{remaining:2d}s)")
                last_code = code
            else:
                # Update remaining seconds inline
                print(f".. {remaining:2d}s left", end='\r', flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBye.")


def cmd_hotp(args):
    secret = load_secret()
    code = hotp(secret, args.counter, args.digits, args.verbose)
    print(f"HOTP(counter={args.counter}): {code}")


def cmd_uri(args):
    secret = load_secret()
    totp_uri, hotp_uri = format_otpauth_uri(secret, args.account, args.issuer, digits=args.digits, period=args.period)
    print("TOTP URI:")
    print(totp_uri)
    print("\nHOTP URI:")
    print(hotp_uri)


# python otp_generator.py <subcommand> [options]
"""
eg..:
    python otp_generator.py init --help
    python otp_generator.py init -h
    python otp_generator.py init init --account alice@example --issuer MyService
    python otp_generator.py totp --digits 8 --period 60
    python otp_generator.py hotp --counter 123456
    python otp_generator.py uri --account alice@example --issuer MyService
"""
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TOTP/HOTP (HMAC‑SHA1) generator with verbose output and keypair helper.")
    sub = p.add_subparsers(dest="cmd")
    p.set_defaults(func=cmd_help)

    # init
    pi = sub.add_parser("init", help="Generate OTP secret and Ed25519 keypair; print otpauth URIs")
    pi.add_argument("--account", default="user@example", help="Account label for otpauth URI")
    pi.add_argument("--issuer", default="otp-tool", help="Issuer label for otpauth URI")
    pi.add_argument("--digits", type=int, default=DEFAULT_DIGITS, help="Number of OTP digits")
    pi.add_argument("--period", type=int, default=DEFAULT_TIME_STEP, help="TOTP time step (seconds)")
    pi.add_argument("--verbose", action="store_true", help="Verbose output")
    pi.set_defaults(func=cmd_init)

    # totp
    pt = sub.add_parser("totp", help="Show TOTP code in real time")
    pt.add_argument("--digits", type=int, default=DEFAULT_DIGITS)
    pt.add_argument("--period", type=int, default=DEFAULT_TIME_STEP)
    pt.add_argument("--verbose", action="store_true")
    pt.set_defaults(func=cmd_totp)

    # hotp
    ph = sub.add_parser("hotp", help="Generate HOTP code for a specific counter")
    ph.add_argument("--counter", type=int, required=True)
    ph.add_argument("--digits", type=int, default=DEFAULT_DIGITS)
    ph.add_argument("--verbose", action="store_true")
    ph.set_defaults(func=cmd_hotp)

    # uri
    pu = sub.add_parser("uri", help="Print otpauth URIs for TOTP/HOTP")
    pu.add_argument("--account", default="user@example")
    pu.add_argument("--issuer", default="otp-tool")
    pu.add_argument("--digits", type=int, default=DEFAULT_DIGITS)
    pu.add_argument("--period", type=int, default=DEFAULT_TIME_STEP)
    pu.set_defaults(func=cmd_uri)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

