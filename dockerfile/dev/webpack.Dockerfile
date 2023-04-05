FROM node:18.9-alpine

ENV LANG en_US.UTF-8

RUN apt update && \
    apt install -y --no-install-recommends \
    bash \
  && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home app \
    && mkdir -p /app/web \
    && chown -R app:app /app

USER app
WORKDIR /app

COPY --chown=app:app package.json package-lock.json /app/
RUN npm install
ENV PATH /app/node_modules/.bin:$PATH

COPY --chown=app:app webpack.config.js /app/

WORKDIR /app/web
ENV TERM xterm
CMD ["npm", "run",  "watch"]
