# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY "BPOM Compliance AI UI Redesign/package.json" "BPOM Compliance AI UI Redesign/package-lock.json" ./
RUN npm install --legacy-peer-deps
COPY "BPOM Compliance AI UI Redesign/" ./
RUN npm run build

# Stage 2: Setup Python Backend
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (Tesseract for OCR)
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn python-multipart

# Copy backend code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/dist "/app/BPOM Compliance AI UI Redesign/dist"

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Run the API
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]
