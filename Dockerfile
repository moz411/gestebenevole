FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    locales \
    sqlite3 \
    libpango1.0-dev \
    libcairo2-dev && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i '/fr_FR.UTF-8/s/^# //' /etc/locale.gen && \
    locale-gen

COPY requirements.txt /tmp
COPY app /app
COPY entrypoint.sh /

ENV PIP_ROOT_USER_ACTION=ignore
RUN chmod +x /entrypoint.sh && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    groupadd -g 1000 app && \
    useradd -r -u 1000 -d /app -g app app && \
    chown -R app:app /app && \
    mkdir /data && \
    chown -R app:app /data

USER app
RUN  fc-cache -r -v 
WORKDIR /app
EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
