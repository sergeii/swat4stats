ARG git_release_sha="-"
ARG _build_user_id=10000
ARG _app_user_id=10001


FROM node:18.9-alpine AS webpack

ENV NODE_ENV production

ARG _build_user_id
RUN addgroup builder --gid $_build_user_id \
  && adduser --disabled-password --ingroup builder --uid $_build_user_id builder

RUN mkdir -p /app/web/dist \
    && chown -R builder:builder /app

USER builder
WORKDIR /app

# install nodejs packages
COPY --chown=builder:builder package.json package-lock.json webpack.config.js /app/
RUN npm install --production
ENV PATH /app/node_modules/.bin:$PATH

# compile the static files
COPY --chown=builder:builder web/src /app/web/src
RUN npm run build


FROM python:3.10.7-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8
ENV PIP_NO_CACHE_DIR false
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true
ENV STAGE prod

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

USER builder
WORKDIR /app

COPY --chown=builder:builder pip-poetry.txt /app/pip-poetry.txt
RUN pip install --user --no-warn-script-location -r pip-poetry.txt
ENV PATH /app/.venv/bin:/home/builder/.local/bin:$PATH

COPY --chown=builder:builder pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction

COPY --from=webpack --chown=builder:builder /app/web/dist /app/src/web/dist

USER root
RUN apk del \
    .build-deps \
    gcc \
    musl-dev \
    libc-dev

USER builder
COPY --chown=builder:builder . /app/src
COPY --chown=builder:builder dockerfile/prod/uwsgi.ini /app/

# build django static
WORKDIR /app/src
RUN ./manage.py collectstatic --noinput

ENV GIT_RELEASE_SHA $git_release_sha

WORKDIR /app/src
USER app
ENV TERM xterm
CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]
