FROM python:3.11-slim

WORKDIR /app

# Install backend as a dependency so worker can import models, services, providers
COPY ../backend /backend
RUN pip install --no-cache-dir -e /backend

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "app.main"]
