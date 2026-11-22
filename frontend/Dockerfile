# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store pnpm install --frozen-lockfile

# ---------- dev: Vite dev server, source mounted ----------
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev"]

# ---------- build ----------
FROM deps AS build
COPY . .
RUN pnpm build

# ---------- prod: nginx serving the SPA + proxying /api ----------
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
