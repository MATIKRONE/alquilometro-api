FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app
RUN pip install --no-cache-dir "poetry>=2.0,<3.0"
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main --no-root
COPY alquilometro_api ./alquilometro_api
COPY frontend/index.html frontend/style.css frontend/app.js frontend/web.py ./frontend/

EXPOSE 8000
CMD ["sh", "-c", "python -m alquilometro_api.semilla && exec uvicorn frontend.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
