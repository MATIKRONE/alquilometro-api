FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry>=2.0,<3.0"

# Primero solo los archivos de dependencias: si no cambian, Docker
# reutiliza esta capa y el build siguiente es mucho mas rapido.
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main --no-root

COPY alquilometro_api ./alquilometro_api

EXPOSE 8000

CMD ["uvicorn", "alquilometro_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
