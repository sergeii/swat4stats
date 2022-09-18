ARG _user_id=10001


FROM python:3.10.7-alpine

ENV PIP_NO_CACHE_DIR on
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1
ENV PYTHONIOENCODING UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true

# run time dependencies
RUN apk add --no-cache \
  bash \
  git \
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

ARG _user_id
RUN addgroup app --gid $_user_id \
  && adduser --disabled-password --ingroup app --uid $_user_id --shell /bin/bash app

RUN mkdir -p /app/src \
    && chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app pip-poetry.txt /app/pip-poetry.txt
RUN pip install --user --no-warn-script-location -r pip-poetry.txt
ENV PATH /app/.venv/bin:/home/app/.local/bin:$PATH

COPY --chown=app:app pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction

USER root
RUN apk del \
    .build-deps \
    gcc \
    musl-dev \
    libc-dev

USER app
WORKDIR /app/src
ENV TERM xterm
VOLUME ["/app/src"]
CMD ["/bin/true"]
