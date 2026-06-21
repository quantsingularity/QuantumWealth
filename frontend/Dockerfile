# Standalone frontend image: builds the React app and serves it with its
# own nginx. Use this if you want to deploy the frontend independently of
# the backend (a separate host, a CDN origin, etc).
#
# The default docker-compose.yml in this repo does NOT use this Dockerfile
# - it builds the frontend into a shared volume and serves it from the
# same nginx instance that proxies the API, to reuse that instance's
# rate-limiting and security headers for the whole app. Use this image
# instead if you specifically want the frontend deployed separately; if
# you do, point its API calls at the backend's actual public URL and add
# that origin to the backend's CORS_ORIGINS.

FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.standalone.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:80/ > /dev/null || exit 1
