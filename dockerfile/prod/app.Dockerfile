ARG git_release_sha="-"
ARG _build_user_id=10000
ARG _app_user_id=10001


FROM node:18.9 AS webpack

ENV NODE_ENV production

ARG _build_user_id
RUN groupadd builder --gid $_build_user_id && \
    useradd --create-home -g builder --uid $_build_user_id builder

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


FROM python:3.10.7

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING UTF-8
ENV PIP_NO_CACHE_DIR false
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true
ENV STAGE prod

RUN apt install -y --no-install-recommends \
    bash \
  && rm -rf /var/lib/apt/lists/*

ARG _build_user_id
ARG _app_user_id
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

COPY --from=webpack --chown=builder:builder /app/web/dist/. /app/src/web/dist

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
