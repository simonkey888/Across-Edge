FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps -e .
ENTRYPOINT ["python", "-m", "across_edge.cli"]
CMD ["safety-check"]
