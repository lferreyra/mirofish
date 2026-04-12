FROM python:3.11

# Instalar Node.js e ferramentas necessarias
RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm \
  && rm -rf /var/lib/apt/lists/*

# uv para gerenciar deps Python
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Deps Node (cache layer)
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/

# Deps Python (cache layer)
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Instalar todas as dependencias
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# Instalar extras que nao estao no uv.lock ainda
RUN pip install fpdf2 flask-jwt-extended --break-system-packages --quiet 2>/dev/null || true

# Copiar codigo fonte
COPY . .

EXPOSE 3000 5001

# Iniciar frontend + backend
CMD ["npm", "run", "dev"]
