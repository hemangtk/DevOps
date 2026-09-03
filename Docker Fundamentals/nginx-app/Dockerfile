# Hello World - Nginx
# Name: Hemang | Enrollment number: 24bcs10209
FROM nginx:alpine

# Replace the default nginx welcome page with ours.
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
