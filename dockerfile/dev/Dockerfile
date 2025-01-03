FROM python:3.12.8-slim

ENV PIP_NO_CACHE_DIR on
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1
ENV PYTHONIOENCODING UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV LANG en_US.UTF-8
ENV POETRY_VIRTUALENVS_IN_PROJECT true

RUN apt update && \
    apt install -y --no-install-recommends \
    build-essential \
    bash \
  && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home app \
    && mkdir -p /app/src \
    && chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app pip-poetry.txt /app/pip-poetry.txt
RUN pip install --user --no-warn-script-location -r pip-poetry.txt
ENV PATH /app/.venv/bin:/home/app/.local/bin:$PATH

COPY --chown=app:app pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --without dev

WORKDIR /app/src
ENV TERM xterm
CMD ["/bin/true"]
