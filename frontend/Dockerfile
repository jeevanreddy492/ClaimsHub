# ---- build the React app ----
FROM node:22-alpine AS build
WORKDIR /ui
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Caddy serves the UI and proxies /api to FastAPI (HTTPS in prod) ----
FROM caddy:2-alpine
COPY --from=build /ui/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
