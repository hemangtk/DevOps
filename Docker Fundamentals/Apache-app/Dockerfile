# Hello World - Apache httpd
# Name: Hemang | Enrollment number: 24bcs10209
# No application code to build: httpd just serves the document root.
FROM httpd:2.4-alpine

# httpd's document root inside this image
COPY index.html /usr/local/apache2/htdocs/index.html

EXPOSE 80
# The base image already sets CMD ["httpd-foreground"], kept explicit here.
CMD ["httpd-foreground"]
