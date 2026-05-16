FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only PyTorch before requirements.txt to avoid pulling the 2 GB CUDA build from PyPI.
# x86_64: use the dedicated CPU wheel index (no CUDA, smaller download).
# aarch64: that index has no ARM wheels, so fall back to standard PyPI which ships CPU-only ARM builds.
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
        pip install --no-cache-dir torch torchvision; \
    fi

COPY requirements.txt .
# torch/torchvision are already installed above and satisfy the >=constraints in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Bake the InsightFace buffalo_l model into the image so restarts don't re-download ~500 MB.
RUN python -c "\
from insightface.app import FaceAnalysis; \
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
app.prepare(ctx_id=-1, det_size=(640, 640))"

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
