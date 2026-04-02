"""
Gunicorn 用 WSGI エントリーポイント
"""

from app import create_app

app = create_app()
