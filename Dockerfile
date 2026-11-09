FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY ministry ./ministry

RUN useradd --create-home bot \
    && mkdir -p /app/data \
    && chown bot /app/data
USER bot

VOLUME /app/data

CMD ["python", "bot.py"]
