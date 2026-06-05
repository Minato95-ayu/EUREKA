FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL=
ARG VITE_WS_URL=/ws
ARG VITE_3D_API_URL=
ARG VITE_3D_API_KEY=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_3D_API_URL=$VITE_3D_API_URL
ENV VITE_3D_API_KEY=$VITE_3D_API_KEY
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
RUN printf '%s\n' \
  'server {' \
  '  listen 80;' \
  '  server_name _;' \
  '  root /usr/share/nginx/html;' \
  '  index index.html;' \
  '' \
  '  # Gzip compression' \
  '  gzip on;' \
  '  gzip_vary on;' \
  '  gzip_proxied any;' \
  '  gzip_comp_level 6;' \
  '  gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;' \
  '' \
  '  # Security headers' \
  '  add_header X-Frame-Options "SAMEORIGIN" always;' \
  '  add_header X-Content-Type-Options "nosniff" always;' \
  '  add_header X-XSS-Protection "1; mode=block" always;' \
  '  add_header Referrer-Policy "strict-origin-when-cross-origin" always;' \
  '' \
  '  # Cache static assets' \
  '  location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {' \
  '    expires 30d;' \
  '    add_header Cache-Control "public, immutable";' \
  '  }' \
  '' \
  '  location / {' \
  '    try_files $uri $uri/ /index.html;' \
  '  }' \
  '}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
