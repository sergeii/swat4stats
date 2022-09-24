ARG git_release_sha="-"
ARG _build_user_id=10000
ARG _app_user_id=10001


FROM python:3.8.5-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8
ENV PIP_NO_CACHE_DIR false
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV LANG en_US.UTF-8

RUN apk add --no-cache \
  bash \
  rsync \
  postgresql-dev \
  libffi-dev \
  libressl-dev

# build time only dependencies
RUN apk add --no-cache --virtual \
    .build-deps \
    gcc \
    make \
    musl-dev \
    libc-dev

ARG _build_user_id
ARG _app_user_id
RUN addgroup builder --gid $_build_user_id \
  && adduser --disabled-password --ingroup builder --uid $_build_user_id builder \
  && addgroup app --gid $_app_user_id \
  && adduser --disabled-password --no-create-home --ingroup app --uid $_app_user_id --shell /bin/bash app

RUN mkdir -p /app/src \
    && mkdir -p /app/static \
    && chown -R builder:builder /app

# prepare virtualenv
USER builder

WORKDIR /app
COPY --chown=builder:builder requirements-pip.txt /app/
RUN pip install --user --no-warn-script-location -r requirements-pip.txt
ENV PATH /app/env/bin:/home/builder/.local/bin:$PATH

COPY --chown=builder:builder Pipfile Pipfile.lock /app/
RUN python -m venv /app/env \
    && VIRTUAL_ENV=/app/env pipenv install --deploy
ENV VIRTUAL_ENV /app/env

USER root
RUN apk del \
    .build-deps \
    gcc \
    musl-dev \
    libc-dev

USER builder

COPY --chown=builder:builder dockerfile/prod/uwsgi.ini /app/
COPY --chown=builder:builder src/ /app/src

ENV STAGE prod
ENV SETTINGS_SECRET_KEY stub
ENV SETTINGS_SENTRY_DSN secret

# build django static
WORKDIR /app/src
RUN ./manage.py collectstatic --noinput

ENV GIT_RELEASE_SHA $git_release_sha

WORKDIR /app/src
USER app
ENV TERM xterm
CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]
