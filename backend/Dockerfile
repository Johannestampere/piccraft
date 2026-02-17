FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download rembg model
RUN python -c "from rembg import new_session; new_session('u2net')"

# Pre-download Depth Anything V2 Base model
RUN python -c "from transformers import AutoImageProcessor, AutoModelForDepthEstimation; AutoImageProcessor.from_pretrained('depth-anything/Depth-Anything-V2-Base-hf'); AutoModelForDepthEstimation.from_pretrained('depth-anything/Depth-Anything-V2-Base-hf')"

COPY app/ ./app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]