ARG _user_id=10001


FROM node:18.9-alpine

ENV LANG en_US.UTF-8

RUN apk add --no-cache bash

ARG _user_id
RUN addgroup app --gid $_user_id \
  && adduser --disabled-password --ingroup app --uid $_user_id --shell /bin/bash app

COPY --chown=app:app package.json package-lock.json /app/
RUN chown -R app:app /app

USER app
WORKDIR /app

RUN npm install
ENV PATH /app/node_modules/.bin:$PATH

COPY --chown=app:app webpack.config.js /app/

WORKDIR /app/web
USER app
ENV TERM xterm
VOLUME ["/app/web"]
CMD ["npm", "run",  "watch"]
