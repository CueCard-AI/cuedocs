FROM node:20-alpine AS y-provider-builder

ARG AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ARG AWS_REGION=${AWS_REGION}
ARG AWS_SECRETS_MANAGER_SECRET_ID=${AWS_SECRETS_MANAGER_SECRET_ID}

ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
ENV AWS_REGION=${AWS_REGION}
ENV AWS_SECRETS_MANAGER_SECRET_ID=${AWS_SECRETS_MANAGER_SECRET_ID}

WORKDIR /home/frontend/

COPY ./src/frontend/package.json ./package.json
COPY ./src/frontend/yarn.lock ./yarn.lock
COPY ./src/frontend/servers/y-provider/package.json ./servers/y-provider/package.json
COPY ./src/frontend/packages/eslint-config-impress/package.json ./packages/eslint-config-impress/package.json

RUN yarn install

COPY ./src/frontend/packages/eslint-config-impress ./packages/eslint-config-impress
COPY ./src/frontend/servers/y-provider ./servers/y-provider

WORKDIR /home/frontend/servers/y-provider
RUN yarn build

FROM node:20-alpine AS y-provider

WORKDIR /home/frontend/

COPY ./src/frontend/package.json ./package.json
COPY ./src/frontend/yarn.lock ./yarn.lock
COPY ./src/frontend/servers/y-provider/package.json ./servers/y-provider/package.json

WORKDIR /home/frontend/servers/y-provider

RUN apk add \
  aws-cli

COPY --from=y-provider-builder \
    /home/frontend/servers/y-provider/dist \
    ./dist

RUN NODE_ENV=production yarn install --frozen-lockfile

# Remove npm, contains CVE related to cross-spawn and we don't use it.
RUN rm -rf /usr/local/bin/npm /usr/local/lib/node_modules/npm

# Un-privileged user running the application
ARG DOCKER_USER
USER ${DOCKER_USER}

# Copy entrypoint
COPY ./docker/files/usr/local/bin/entrypoint /usr/local/bin/entrypoint

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]

CMD ["yarn", "start"]
