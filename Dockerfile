ARG git_release_ver="-"
ARG git_release_sha="-"

ARG _build_user_id=10000
ARG _work_user_id=10001

FROM python:3.14.6-slim AS base

ENV \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONIOENCODING=UTF-8 \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  LANG=en_US.UTF-8 \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  PATH="/app/.venv/bin:$PATH"

RUN apt update \
  && apt install -y --no-install-recommends \
    bash \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-warn-script-location poetry==2.4.1


FROM base AS dev

ENV PIP_NO_CACHE_DIR=on

RUN useradd --create-home app \
    && mkdir -p /app/src \
    && chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --without dev

WORKDIR /app/src
ENV TERM=xterm
CMD ["/bin/true"]


FROM base AS prod

ENV PIP_NO_CACHE_DIR=false

ARG _build_user_id
ARG _work_user_id
RUN groupadd builder --gid $_build_user_id \
    && useradd --create-home -g builder --uid $_build_user_id builder \
    && groupadd worker --gid $_work_user_id \
    && useradd -g worker --uid $_work_user_id --shell /bin/bash worker \
    && mkdir -p /app/src \
    && mkdir -p /app/static \
    && chown -R builder:builder /app

USER builder
WORKDIR /app

COPY --chown=builder:builder pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --without dev

COPY --chown=builder:builder . /app/src

ENV SETTINGS_SECRET_KEY=stub
ENV SETTINGS_STATIC_ROOT=/app/static

WORKDIR /app/src
RUN ./manage.py collectstatic --noinput

ARG git_release_ver
ARG git_release_sha

ENV \
  GIT_RELEASE_VER=$git_release_ver \
  GIT_RELEASE_SHA=$git_release_sha \
  SENTRY_RELEASE=$git_release_ver

WORKDIR /app/src
USER worker
CMD ["uwsgi"]
