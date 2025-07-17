# IDF Testing Infrastructure - Production Nginx Container
# High-performance reverse proxy with security hardening

FROM nginx:1.25-alpine as base

# Install security updates and required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    openssl \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=Asia/Jerusalem
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create nginx user and directories
RUN addgroup -g 1000 nginx-app && \
    adduser -D -s /bin/sh -u 1000 -G nginx-app nginx-app && \
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /var/log/nginx \
             /etc/nginx/ssl \
             /etc/nginx/conf.d \
    && chown -R nginx-app:nginx-app /var/cache/nginx /var/log/nginx /etc/nginx

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
COPY ssl/ /etc/nginx/ssl/

# Set proper permissions
RUN chown -R nginx-app:nginx-app /etc/nginx && \
    chmod 600 /etc/nginx/ssl/* 2>/dev/null || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Use non-root user
USER nginx-app

# Expose ports
EXPOSE 80 443

# Start nginx
CMD ["nginx", "-g", "daemon off;"]