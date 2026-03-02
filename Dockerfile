FROM python:3.12-slim

# gcc  -- pycryptodome C extension
# git  -- scdatatools install + repo self-update
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install scdatatools from GitLab HEAD first (slow, changes rarely — good cache layer)
# --no-deps:               install deps separately to pick up binary wheels
# --ignore-requires-python: upstream pins Python <3.11, we run 3.12
RUN pip install --no-cache-dir \
    "git+https://gitlab.com/scmodding/frameworks/scdatatools.git" \
    --no-deps --ignore-requires-python

# Clone the pipeline repo (docker branch) — code comes from git, not COPY
ARG REPO_URL=https://github.com/saladin1980/sc_datapack.git
ARG BRANCH=docker
RUN git clone --branch ${BRANCH} ${REPO_URL} .

# Install runtime deps from cloned requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# /data  -- single volume mount (Data.p4k in, JSON out)
# /work  -- ephemeral extraction scratch space (container-local)
VOLUME ["/data"]
RUN mkdir -p /work/extraction /work/logs

ENV SC_P4K_PATH=/data/Data.p4k \
    SC_OUTPUT_DIR=/work/extraction \
    SC_REPORTS_DIR=/data \
    SC_LOGS_DIR=/data/logs

CMD ["python", "entrypoint.py"]
