FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip uninstall opencv-python -y || true
RUN pip install opencv-python-headless

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
