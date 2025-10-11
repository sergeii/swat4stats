FROM python:3.14.0-slim

ENV \
  PIP_NO_CACHE_DIR=on \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PYTHONUNBUFFERED=1 \
  PYTHONIOENCODING=UTF-8 \
  PYTHONDONTWRITEBYTECODE=1 \
  LANG=en_US.UTF-8 \
  POETRY_VIRTUALENVS_IN_PROJECT=true

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
ENV PATH="/app/.venv/bin:/home/app/.local/bin:$PATH"

COPY --chown=app:app pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --without dev

WORKDIR /app/src
ENV TERM=xterm
CMD ["/bin/true"]
