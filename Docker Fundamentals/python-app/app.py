# Hello World web app - Python / Flask
# Name: Hemang | Enrollment number: 24bcs10209
import sys
from flask import Flask

app = Flask(__name__)

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Python in Docker</title>
<style>body{{font-family:system-ui,sans-serif;display:grid;place-items:center;height:100vh;margin:0;background:#111;color:#eee}}
h1{{font-size:3rem;margin:0}}p{{color:#8cc}}</style></head>
<body><div><h1>Hello World</h1>
<p>Python {version} &middot; Flask &middot; running in Docker</p>
<p>Hemang &middot; 24bcs10209</p></div></body></html>"""


@app.route("/")
def hello():
    return PAGE.format(version=sys.version.split()[0])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
