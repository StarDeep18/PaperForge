# Stage 1: Build React SPA
FROM node:20.18.0-alpine AS builder

WORKDIR /app

COPY client/package*.json ./
RUN npm ci --prefer-offline --no-audit

COPY client/ ./

ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.27.2-alpine

LABEL org.opencontainers.image.title="PaperForge Client"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="PaperForge Team"
LABEL org.opencontainers.image.description="React Single Page Application served by Nginx"

COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
