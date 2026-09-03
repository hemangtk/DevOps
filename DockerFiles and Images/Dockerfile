# Multi-stage build
# Name: Hemang | Enrollment number: 24bcs10209
#
# A compiled program needs a toolchain to BUILD but not to RUN.
# Stage 1 has the Go compiler. Stage 2 has only the finished binary.

# ---------- stage 1: build ----------
FROM golang:1.23-alpine AS build
WORKDIR /src

COPY main.go .
RUN go mod init hello-multistage >/dev/null 2>&1 \
 && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/hello .
# CGO_ENABLED=0 -> a fully static binary, so it can run on an image with no libc.
# -ldflags="-s -w" -> strip the symbol table and DWARF debug info.

# ---------- stage 2: run ----------
FROM scratch
COPY --from=build /out/hello /hello

EXPOSE 8080
ENTRYPOINT ["/hello"]
