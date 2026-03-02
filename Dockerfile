FROM python:3.12-slim

# gcc  -- required to build pycryptodome C extension
# git  -- required to install scdatatools from GitLab (PyPI 1.0.4 broken on Python 3.12)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install scdatatools from GitLab HEAD.
# --no-deps:               we install deps separately to pick up binary wheels
# --ignore-requires-python: upstream pins Python <3.11, we run 3.12
RUN pip install --no-cache-dir \
    "git+https://gitlab.com/scmodding/frameworks/scdatatools.git" \
    --no-deps --ignore-requires-python

# Install all scdatatools runtime deps (binary wheels where available)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source
COPY SCRIPTS/ SCRIPTS/
COPY entrypoint.py .

# Single volume mount:
#   /data/Data.p4k           -- drop your Data.p4k here
#   /data/build_manifest.id  -- optional, for proper game version string
#   /data/JSON/              -- output JSON files appear here
VOLUME ["/data"]

# /work is container-local (ephemeral extraction scratch space)
RUN mkdir -p /work/extraction /work/logs

ENV SC_P4K_PATH=/data/Data.p4k \
    SC_OUTPUT_DIR=/work/extraction \
    SC_REPORTS_DIR=/data \
    SC_LOGS_DIR=/data/logs

CMD ["python", "entrypoint.py"]
