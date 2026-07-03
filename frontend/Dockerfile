# Build stage
FROM node:22-alpine AS builder
WORKDIR /app

ARG VITE_GIT_SHA=local
ARG VITE_BUILD_TIME=
ARG VITE_APP_VERSION=0.13.0 # x-release-please-version

ENV VITE_GIT_SHA=$VITE_GIT_SHA
ENV VITE_BUILD_TIME=$VITE_BUILD_TIME
ENV VITE_API_URL=
ENV VITE_APP_VERSION=$VITE_APP_VERSION

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
