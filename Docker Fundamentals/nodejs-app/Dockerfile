# Hello World - Node.js
# Name: Hemang | Enrollment number: 24bcs10209
FROM node:22-alpine

WORKDIR /app

# Copy the manifest first so this layer is cached and only re-runs
# when dependencies actually change.
COPY package.json ./
RUN npm install --omit=dev

COPY app.js ./

EXPOSE 3000
CMD ["node", "app.js"]
