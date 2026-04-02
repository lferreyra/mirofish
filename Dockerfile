FROM python:3.11-slim

# Node.js 20 インストール
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# uv をコピー
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# 依存ファイルを先にコピー（キャッシュ活用）
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# 依存インストール
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# ソースをコピー
COPY . .

# フロントエンドをビルド
RUN npm run build

EXPOSE 5001

CMD ["sh", "-c", "cd /app/backend && uv run gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 1 --threads 4 --timeout 600 wsgi:app"]
