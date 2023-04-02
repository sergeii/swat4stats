FROM python:3.11.2-slim

ARG git_release_ver="-"
ARG git_release_sha="-"

ARG _build_user_id=10000
ARG _app_user_id=10001

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8
ENV PIP_NO_CACHE_DIR false
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true

RUN apt update && \
    apt install -y --no-install-recommends \
    build-essential \
    bash \
  && rm -rf /var/lib/apt/lists/*

RUN groupadd builder --gid $_build_user_id &&  \
    useradd --create-home -g builder --uid $_build_user_id builder && \
    groupadd app --gid $_app_user_id &&  \
    useradd -g app --uid $_app_user_id --shell /bin/bash app

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

COPY --chown=builder:builder . /app/src

ENV SETTINGS_SECRET_KEY stub
ENV SETTINGS_STATIC_ROOT /app/static

# build django static
WORKDIR /app/src
RUN ./manage.py collectstatic --noinput

ENV GIT_RELEASE_VER $git_release_ver
ENV GIT_RELEASE_SHA $git_release_sha

WORKDIR /app/src
USER app
ENV TERM xterm
CMD ["uwsgi"]
