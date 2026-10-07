"""Unit tests - these are what the CI pipeline runs.
Name: Hemang | Enrollment number: 24bcs10209
"""
import pytest

from app.calculator import add, divide, multiply, subtract


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(10, 4) == 6
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(5, 0) == 0


def test_divide():
    assert divide(10, 2) == 5
    assert divide(9, 3) == 3


def test_divide_by_zero_raises():
    with pytest.raises(ValueError, match="division by zero"):
        divide(1, 0)
