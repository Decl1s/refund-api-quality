"""Я запускаю стенд только на loopback и явно выбираю файл БД."""

import argparse
from pathlib import Path
import uvicorn
from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="Я запускаю учебный API возвратов.")
    parser.add_argument("--db", type=Path, default=Path("workspace/refunds.db"), help="Я храню синтетическое состояние в этом файле.")
    parser.add_argument("--port", type=int, default=8766, help="Я выбираю свободный локальный порт.")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Я ожидаю порт от 1 до 65535.")
    uvicorn.run(create_app(args.db), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
