# Multi-stage build for the BoardMind Next.js frontend.
# NEXT_PUBLIC_API_URL is baked in at build time (Next.js inlines
# NEXT_PUBLIC_* vars into the client bundle) — pass it as a build arg so the
# same Dockerfile works for local docker-compose and Cloud Run deploys
# pointed at different backend URLs, without editing source.

FROM node:20-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY frontend .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

ENV PORT=8080
EXPOSE 8080
CMD ["npx", "next", "start", "-p", "8080"]
