# One image for both Cloud Run services; only the start command differs.
#   API (default): uvicorn main:app
#   UI:            streamlit run ui/Main.py   (overridden at deploy time)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8080
CMD exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
