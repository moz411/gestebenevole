FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    locales \
    sqlite3 \
    build-essential \
    libpango1.0-dev \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i '/fr_FR.UTF-8/s/^# //' /etc/locale.gen \
    && locale-gen

COPY requirements.txt /tmp
COPY app /app
COPY entrypoint.sh /

RUN chmod +x /entrypoint.sh && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    groupadd -g 1000 app && \
    useradd -r -u 1000 -g app app && \
    mkdir /data && \
    chown -R app:app /data

USER app
WORKDIR /app
EXPOSE 8080
ENV LANG=fr_FR.UTF-8 \
    LANGUAGE=fr_FR:fr \
    LC_ALL=fr_FR.UTF-8

ENTRYPOINT ["/entrypoint.sh"]
