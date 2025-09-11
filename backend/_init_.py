"""
BACKEND PACKAGE INITIALIZATION FILE

Đây là file __init__.py của package backend - file đánh dấu thư mục backend là một Python package.
Backend package for OTP management using Flask.
Integrates with otp core functions.
"""

from .app import app

__all__ = ['app']