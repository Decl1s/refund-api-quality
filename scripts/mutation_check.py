"""Я проверяю три конкретные мутации в одноразовых копиях, исходник не меняю."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("Граница полного возврата", 'used + amount_minor > order["amount_minor"]',
     'used + amount_minor >= order["amount_minor"]', "test_api.py::test_exact_full_refund"),
    ("Сравнение повторного запроса", '(previous["order_id"], previous["amount_minor"], previous["currency"]) !=',
     '(previous["order_id"], previous["amount_minor"], previous["currency"]) ==', "test_api.py::test_repeat_does_not_double_refund"),
    ("Валюта возврата", 'order["currency"] != currency',
     'order["currency"] == currency', "test_api.py::test_currency_mismatch"),
]


def main():
    results = []
    for title, before, after, test in MUTATIONS:
        with TemporaryDirectory() as folder:
            target = Path(folder)
            shutil.copytree(ROOT / "refund_api", target / "refund_api", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "tests", target / "tests", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy2(ROOT / "pyproject.toml", target)
            source = target / "refund_api/store.py"
            value = source.read_text(encoding="utf-8")
            if value.count(before) != 1:
                raise RuntimeError("Я не нашёл единственное место мутации: " + title)
            source.write_text(value.replace(before, after), encoding="utf-8")
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            result = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests/" + test],
                                    cwd=target, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            # pytest exit=1 означает упавшую проверку; import/collection error=2
            # я не засчитываю как обнаруженную бизнес-ошибку.
            if result.returncode != 1 or "1 failed" not in result.stdout:
                print(result.stdout, result.stderr)
                raise RuntimeError("Я не подтвердил обнаружение мутации: " + title)
            results.append({"mutation": title, "detected": True})
    print(json.dumps({"detected": len(results), "total": len(MUTATIONS), "checks": results}, ensure_ascii=True))


if __name__ == "__main__":
    main()
