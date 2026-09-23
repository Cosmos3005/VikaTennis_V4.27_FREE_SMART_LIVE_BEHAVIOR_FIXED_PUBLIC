FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# XGBoost's Linux wheel uses OpenMP at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 vika \
    && useradd --system --uid 10001 --gid vika --home-dir /app vika

COPY requirements-runtime.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-runtime.txt

COPY --chown=vika:vika . ./
RUN mkdir -p /app/data /app/models \
    && chown -R vika:vika /app

USER 10001:10001
CMD ["python", "start_bot.py"]
