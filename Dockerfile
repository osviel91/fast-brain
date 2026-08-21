FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY fast_brain ./fast_brain
COPY migrations ./migrations

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "fast_brain.main:app", "--host", "0.0.0.0", "--port", "8080"]
