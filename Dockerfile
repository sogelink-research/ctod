FROM python:3.10-slim

WORKDIR /app

ENV GDAL_CACHEMAX=75%
ENV GDAL_DISABLE_READDIR_ON_OPEN=TRUE
ENV GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES
ENV GDAL_HTTP_MULTIPLEX=YES
ENV GDAL_INGESTED_BYTES_AT_OPEN=32768

COPY pyproject.toml poetry.lock /app/
COPY ./ctod /app/ctod/
COPY app.py /app/

RUN apt-get update \
    && apt-get install -y gcc \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev \
    && apt-get remove -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 5000

CMD ["python", "app.py"]