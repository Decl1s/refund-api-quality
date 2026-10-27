"""Я проверяю demo из распакованного source-only архива."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile
from package_release import ROOT, NAME, archive


def main():
    evidence = archive()
    with TemporaryDirectory() as folder:
        with zipfile.ZipFile(ROOT / "artifacts" / NAME) as bundle:
            bundle.extractall(folder)
        result = subprocess.run([sys.executable, "-X", "utf8", "scripts/demo.py"], cwd=Path(folder),
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        assert "HTTP 201" in result.stdout and "HTTP 200" in result.stdout and "HTTP 409" in result.stdout
    print({"zip_demo": True, **evidence})


if __name__ == "__main__":
    main()
