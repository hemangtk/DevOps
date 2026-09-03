# Hello World - Java
# Name: Hemang | Enrollment number: 24bcs10209
FROM eclipse-temurin:21-jdk-alpine

WORKDIR /app
COPY Main.java ./

# Compile at build time so the container starts straight into the app.
RUN javac Main.java

EXPOSE 8000
CMD ["java", "Main"]
