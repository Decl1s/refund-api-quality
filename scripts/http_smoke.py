"""Я проверяю настоящий loopback HTTP через Uvicorn и останавливаю свой сервер."""

import json
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import uvicorn
from refund_api.app import create_app


def main():
    for args in (["--help"], ["--port", "0"]):
        result = subprocess.run([sys.executable, "-m", "refund_api", *args], cwd=ROOT, capture_output=True, timeout=15)
        assert result.returncode == (0 if args == ["--help"] else 2)
    with TemporaryDirectory() as folder, socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        base = "http://127.0.0.1:" + str(listener.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(create_app(Path(folder) / "http.db"), log_level="error"))
        worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()

        def call(path, body=None, key=None):
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Idempotency-Key"] = key
            req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
            try:
                response = urlopen(req, timeout=3)
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.load(response)

        try:
            deadline = time.monotonic() + 10
            while True:
                try:
                    if call("/health")[0] == 200:
                        break
                except (URLError, TimeoutError):
                    pass
                if not worker.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Я не дождался HTTP readiness.")
                time.sleep(0.05)
            assert call("/orders", {"order_id": "HTTP-1", "amount_minor": 100, "currency": "RUB"})[0] == 201
            body = {"amount_minor": 60, "currency": "RUB"}
            first = call("/orders/HTTP-1/refunds", body, "http-first")
            repeat = call("/orders/HTTP-1/refunds", body, "http-first")
            excess = call("/orders/HTTP-1/refunds", body, "http-second")
            assert [first[0], repeat[0], excess[0]] == [201, 200, 409]
            assert first[1] == repeat[1]
            assert call("/orders/HTTP-1")[1]["remaining_minor"] == 40
            print(json.dumps({"real_http": True, "statuses": [201, 200, 409], "remaining_minor": 40}))
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            if worker.is_alive():
                raise RuntimeError("Я не смог остановить временный HTTP server.")


if __name__ == "__main__":
    main()
