ARG BASE_IMAGE
FROM ${BASE_IMAGE}

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt
