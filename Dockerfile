############################
# Stage: KERN Assets holen
############################

FROM node:22-bookworm-slim AS kern-assets

WORKDIR /kern

# feste KERN-Version
ARG KERN_VERSION=2.6.2

RUN npm init -y \
    && npm install @kern-ux/native@${KERN_VERSION} --save-exact

############################
# Stage: Django Runtime
############################

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/kern.min.css /app/static/kern/kern.min.css
COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/fonts /app/static/kern/fonts
COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/js /app/static/kern/js

COPY ./docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app

RUN python manage.py collectstatic --noinput

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s CMD python -c "import os, urllib.request; p=os.environ.get('WEB_PORT','8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz/', timeout=5)" || exit 1
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
