FROM node:22.18.0-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN python3 -m pip install --break-system-packages --no-deps -e .
ENTRYPOINT ["python3","scripts/shadow_run.py"]
