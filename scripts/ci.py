"""Я останавливаю CI на первом отказе независимо от Linux/PowerShell."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for args in (
        ["-m", "pip", "install", "--require-hashes", "-r", "requirements.lock"],
        ["-m", "pip", "check"],
        ["-m", "pytest", "--cov", "--cov-report=term-missing", "--cov-report=html:reports/coverage", "--junitxml=reports/junit.xml", "-q"],
        ["scripts/mutation_check.py"],
        ["scripts/http_smoke.py"],
        ["scripts/zip_smoke.py"],
    ):
        subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
