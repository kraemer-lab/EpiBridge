FROM python:3.13-slim
RUN pip install --no-cache-dir numpy pandas && \
    mkdir -p /analysis /data /work /output && chmod 777 /output && \
    chown nobody:nogroup /work
