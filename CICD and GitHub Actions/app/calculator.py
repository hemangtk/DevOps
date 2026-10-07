"""A tiny calculator - the unit under test in the CI pipeline.
Name: Hemang | Enrollment number: 24bcs10209
"""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("division by zero is not allowed")
    return a / b
