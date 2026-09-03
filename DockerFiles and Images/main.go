// Multi-stage build demo - a tiny HTTP server with no external dependencies.
// Name: Hemang | Enrollment number: 24bcs10209
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
)

const page = `<!doctype html>
<html><head><meta charset="utf-8"><title>Docker multi-stage build</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#111;color:#eee}
h1{font-size:2.4rem;margin:0 0 .6rem}p{color:#8cc;margin:.2rem}</style></head>
<body><div><h1>Hello World from Docker multi-stage build</h1>
<p>%s &middot; container %s &middot; port 8080</p>
<p>Hemang &middot; 24bcs10209</p></div></body></html>`

func main() {
	host, _ := os.Hostname()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprintf(w, page, runtime.Version(), host)
	})

	// Plain-text endpoint, handy for curl and for container health checks.
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, "Hello World from Docker multi-stage build")
	})

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
