# Droomvriendjes Backend - Railway Deployment
# FastAPI + Supabase + React frontend

# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Install Node dependencies
COPY frontend/package.json frontend/yarn.lock* ./
RUN npm install

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY backend/server.py ./main.py

# Copy built React frontend into the backend's static directory
COPY --from=frontend-builder /frontend/dist/ ./backend/static/

# Create uploads directory
RUN mkdir -p /app/uploads

# Set working directory to backend
WORKDIR /app/backend

# Railway sets PORT automatically
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start command
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]