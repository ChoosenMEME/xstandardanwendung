FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WEB_PORT=8000
ENV APP_PATH=""

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Nur der Anwendungscode. Tests, lokale DB und Build-Artefakte werden ueber
# .dockerignore vom Build-Kontext ausgeschlossen und landen nicht im Image.
COPY ./app /app

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app

EXPOSE ${WEB_PORT}

HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=30s CMD python -c "import os, urllib.request; p=os.environ.get('WEB_PORT','8000'); a=os.environ.get('APP_PATH','').strip('/'); h=f'/{a}/healthz/' if a else '/healthz/'; urllib.request.urlopen(f'http://127.0.0.1:{p}{h}', timeout=5)" || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Metadaten fuer das veroeffentlichte Release-Image.
ARG VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="xstandardanwendung" \
      org.opencontainers.image.description="Django-Anwendung zur Verarbeitung von XGewerbesteuer-Bescheiden" \
      org.opencontainers.image.source="https://github.com/ChoosenMEME/xstandardanwendung" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"
