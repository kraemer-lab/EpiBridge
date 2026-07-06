FROM python:3.11-slim

WORKDIR /app

# Install backend as a dependency so worker can import models, services, providers
COPY backend /backend
RUN pip install --no-cache-dir -e /backend

COPY worker/worker /app/worker

CMD ["python", "-m", "worker.main"]
