ARG git_release_ver="-"
ARG git_release_sha="-"

ARG _build_user_id=10000
ARG _work_user_id=10001

FROM python:3.11.2-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8
ENV PIP_NO_CACHE_DIR false
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true

RUN apt update \
  && apt install -y --no-install-recommends \
    build-essential \
    bash \
  && rm -rf /var/lib/apt/lists/*

ARG _build_user_id
ARG _work_user_id
RUN groupadd builder --gid $_build_user_id  \
    && useradd --create-home -g builder --uid $_build_user_id builder \
    && groupadd worker --gid $_work_user_id \
    && useradd -g worker --uid $_work_user_id --shell /bin/bash worker \
    && mkdir -p /app/src \
    && mkdir -p /app/static \
    && chown -R builder:builder /app

USER builder
WORKDIR /app

COPY --chown=builder:builder pip-poetry.txt /app/pip-poetry.txt
RUN pip install --user --no-warn-script-location -r pip-poetry.txt
ENV PATH /app/.venv/bin:/home/builder/.local/bin:$PATH

COPY --chown=builder:builder pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --without dev

COPY --chown=builder:builder . /app/src

ENV SETTINGS_SECRET_KEY stub
ENV SETTINGS_STATIC_ROOT /app/static

# build django static
WORKDIR /app/src
RUN ./manage.py collectstatic --noinput

ARG git_release_ver
ENV GIT_RELEASE_VER $git_release_ver
ARG git_release_sha
ENV GIT_RELEASE_SHA $git_release_sha

ENV SENTRY_RELEASE $git_release_ver

WORKDIR /app/src
USER worker
ENV TERM xterm
CMD ["uwsgi"]
