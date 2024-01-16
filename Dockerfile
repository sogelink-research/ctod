FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN apt-get update && \
    apt-get install -y gcc && \
    pip install poetry

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

COPY ./ctod /app/ctod/
COPY app.py /app/

EXPOSE 5000

CMD ["python", "app.py"]