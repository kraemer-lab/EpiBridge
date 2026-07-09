FROM python:3.14-slim
RUN pip install --no-cache-dir numpy pandas && \
    mkdir -p /analysis /data /work /output && chmod 777 /output && \
    chown nobody:nogroup /work
