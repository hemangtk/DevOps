"""Flask front end so the image has something to serve.
Name: Hemang | Enrollment number: 24bcs10209
"""
import os

from flask import Flask, jsonify

from app.calculator import add, divide, multiply, subtract

app = Flask(__name__)
VERSION = os.getenv("APP_VERSION", "dev")

OPS = {"add": add, "subtract": subtract, "multiply": multiply, "divide": divide}


@app.route("/")
def index():
    return (
        "<h1>DevOps CI/CD demo</h1>"
        f"<p>version {VERSION}</p>"
        "<p>Hemang &middot; 24bcs10209</p>"
        "<p>try /calc/add/2/3</p>"
    )


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION)


@app.route("/calc/<op>/<a>/<b>")
def calc(op, a, b):
    """Take the operands as strings so both "2" and "2.5" work -
    Flask's <float:> converter will not match a plain integer."""
    if op not in OPS:
        return jsonify(error=f"unknown operation {op}"), 400
    try:
        x, y = float(a), float(b)
    except ValueError:
        return jsonify(error="operands must be numbers"), 400
    try:
        return jsonify(op=op, a=x, b=y, result=OPS[op](x, y))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
