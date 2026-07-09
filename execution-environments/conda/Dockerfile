FROM mambaorg/micromamba:2.8.1

USER root
RUN mkdir -p /analysis /data /work /output && chmod 777 /output && \
    chown nobody:nogroup /work
ENV PATH="/opt/conda/bin:${PATH}"
USER $MAMBA_USER
