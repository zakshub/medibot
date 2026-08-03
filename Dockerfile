FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade "pip>=26.1.2" \
    && python -m pip wheel --wheel-dir /wheels .

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDIBOT_ENVIRONMENT=production \
    MEDIBOT_DEBUG=false

RUN addgroup --system medibot \
    && adduser --system --ingroup medibot --no-create-home medibot

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels medibot==0.1.0 \
    && rm -rf /wheels \
    && python -m pip uninstall --yes setuptools wheel \
    && python -m pip uninstall --yes pip

USER medibot
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=2)"]

CMD ["uvicorn", "medibot.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
