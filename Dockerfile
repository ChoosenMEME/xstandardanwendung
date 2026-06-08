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

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/kern.min.css /app/static/kern/kern.min.css
COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/fonts /app/static/kern/fonts
COPY --from=kern-assets /kern/node_modules/@kern-ux/native/dist/js /app/static/kern/js

WORKDIR /app

RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]