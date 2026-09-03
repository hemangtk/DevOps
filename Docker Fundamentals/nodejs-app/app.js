// Hello World web app - Node.js
// Name: Hemang | Enrollment number: 24bcs10209
const http = require('http');

const PORT = process.env.PORT || 3000;

const page = `<!doctype html>
<html><head><meta charset="utf-8"><title>Node.js in Docker</title>
<style>body{font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#111;color:#eee}
h1{font-size:3rem;margin:0}p{color:#8cc}</style></head>
<body><div><h1>Hello World</h1>
<p>Node.js ${process.version} &middot; running in Docker</p>
<p>Hemang &middot; 24bcs10209</p></div></body></html>`;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(page);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Node.js app listening on http://0.0.0.0:${PORT}`);
});
