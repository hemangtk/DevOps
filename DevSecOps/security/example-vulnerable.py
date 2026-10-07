"""DELIBERATELY INSECURE - this file is NOT part of the app.
It exists so the SAST scanner has real findings to report, demonstrating what
bandit catches. It is excluded from the pipeline's scan path.

Name: Hemang | Enrollment number: 24bcs10209
"""
import hashlib
import os
import subprocess   # nosec - imported to demonstrate the finding


def weak_hash(password):
    # B303: MD5 is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()


def command_injection(user_input):
    # B602: shell=True with untrusted input
    return subprocess.call(f"ls {user_input}", shell=True)


def hardcoded_secret():
    # B105: hardcoded password
    api_key = "not-a-real-key-" + "placeholder"  # B105: looks like a hardcoded secret
    return api_key


def insecure_temp():
    # B108: predictable temp file path
    path = "/tmp/app-data.txt"
    with open(path, "w") as fh:
        fh.write("data")
    return os.path.exists(path)
