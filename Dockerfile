FROM python:3.13-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    locales \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    fontconfig \
    shared-mime-info \
    fonts-dejavu-core \
    libffi8 \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i '/fr_FR.UTF-8/s/^# //' /etc/locale.gen \
    && locale-gen \
    && fc-cache -r -v

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}" \
    PIP_ROOT_USER_ACTION=ignore

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /app
COPY entrypoint.py /entrypoint.py

RUN chmod +x /entrypoint.py \
    && mkdir /data \
    && chown -R 65532:65532 /app /data \
    && mkdir -p /opt/distroless/usr/lib/x86_64-linux-gnu \
    && mkdir -p /opt/distroless/lib/x86_64-linux-gnu \
    && mkdir -p /opt/distroless/usr/share \
    && cp -a /usr/lib/x86_64-linux-gnu/. /opt/distroless/usr/lib/x86_64-linux-gnu/ \
    && cp -a /lib/x86_64-linux-gnu/. /opt/distroless/lib/x86_64-linux-gnu/ \
    && cp -a /usr/share/fonts /opt/distroless/usr/share/ \
    && cp -a /usr/share/mime /opt/distroless/usr/share/ \
    && cp -a /usr/lib/locale/fr_FR.utf8 /opt/distroless/usr/lib/locale/

FROM gcr.io/distroless/python3.13-debian12

ENV PYTHONUNBUFFERED=1 \
    LANG=fr_FR.UTF-8 \
    LC_ALL=fr_FR.UTF-8 \
    PATH="/opt/venv/bin:${PATH}"

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
COPY --from=builder /entrypoint.py /entrypoint.py
COPY --from=builder /data /data
COPY --from=builder /opt/distroless/usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=builder /opt/distroless/lib/x86_64-linux-gnu /lib/x86_64-linux-gnu
COPY --from=builder /opt/distroless/usr/share/fonts /usr/share/fonts
COPY --from=builder /opt/distroless/usr/share/mime /usr/share/mime
COPY --from=builder /opt/distroless/usr/lib/locale/fr_FR.utf8 /usr/lib/locale/fr_FR.utf8

USER nonroot
WORKDIR /app
EXPOSE 8080

ENTRYPOINT ["/opt/venv/bin/python", "/entrypoint.py"]
