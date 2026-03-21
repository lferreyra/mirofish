FROM python:3.11-slim

# Install Node.js (>=18), necessary tools, and curl for healthchecks
RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm curl \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mirofish && useradd -r -g mirofish -m mirofish

# Copy uv from official image
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Copy dependency descriptors first for layer caching
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install dependencies (Node + Python)
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# Copy project source
COPY . .

EXPOSE 3000 5001

# Disable Flask debug mode for production
ENV FLASK_DEBUG=False

# Healthcheck for backend service
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD curl -f http://localhost:5001/health || exit 1

# Switch to non-root user
USER mirofish

# Start frontend and backend (dev mode)
CMD ["npm", "run", "dev"]
