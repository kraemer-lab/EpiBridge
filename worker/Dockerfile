FROM python:3.11-slim

WORKDIR /app

RUN useradd --system --create-home --shell /bin/false --uid 1000 epibridge

# Install backend as a dependency so worker can import models, services, providers
COPY backend /backend
RUN pip install --no-cache-dir -e /backend

COPY worker/worker /app/worker

# Worker runs as epibridge with supplementary docker group from compose
USER epibridge
CMD ["python", "-m", "worker.main"]
