# Hello World - React (Vite)
# Name: Hemang | Enrollment number: 24bcs10209
#
# Multi-stage: stage 1 needs Node to build, stage 2 only needs a web server.
# The finished image contains static files and nginx, not the toolchain.

# ---------- stage 1: build ----------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json ./
RUN npm install

COPY vite.config.js index.html ./
COPY src ./src
RUN npm run build          # produces /app/dist

# ---------- stage 2: serve ----------
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
