FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:stable-alpine
# The nginx image renders templates with envsubst at startup.
ENV PORT=80 \
    BACKEND_URL=http://backend:8000
RUN rm -f /etc/nginx/conf.d/default.conf
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist/ /usr/share/nginx/html/

EXPOSE 80
