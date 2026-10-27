# Какие технологии я использую

Я проверил актуальные версии 27.10.2026 по официальному PyPI и закрепил весь
набор hashes в `requirements.lock`. В `DEPENDENCIES.txt` я оставил короткий
перечень всех 28 distributions, включая условные зависимости Windows.
Локально Linux устанавливает 26; Windows-зависимости я проверяю отдельным CI.

| Компонент | Версия | Для чего я выбрал | Официальный источник |
| --- | --- | --- | --- |
| CPython | 3.12.15 локально; 3.12.10 в Windows CI | Я использую один minor Python 3.12; фиксирую фактический patch отдельно | [Python](https://docs.python.org/3.12/) |
| SQLite | 3.53.1 локально | Я проверяю реальные writer-lock, FK и rollback через стандартный sqlite3 | [SQLite](https://www.sqlite.org/lang_transaction.html), [sqlite3](https://docs.python.org/3.12/library/sqlite3.html) |
| FastAPI | 0.162.0 | Я описываю JSON/HTTP контракт и получаю OpenAPI/Swagger | [Testing](https://fastapi.tiangolo.com/tutorial/testing/) |
| Uvicorn | 0.54.0 | Я запускаю настоящий локальный ASGI-сервер для ручного просмотра и HTTP smoke | [Uvicorn](https://www.uvicorn.org/) |
| pytest | 9.1.1 | Я использую fixtures, параметризацию, метки, assert и JUnit | [pytest](https://docs.pytest.org/en/stable/) |
| pytest-cov | 7.1.0 | Я измеряю строки/ветви и формирую HTML отчёт | [pytest-cov](https://pytest-cov.readthedocs.io/) |
| Hypothesis | 6.170.12 | Я генерирую последовательности и проверяю инвариант независимой моделью | [Hypothesis](https://hypothesis.readthedocs.io/en/latest/quickstart.html) |
| HTTPX2 | 2.16.0 | Я использую рекомендованный актуальной Starlette клиент внутри TestClient | [Starlette TestClient](https://starlette.dev/testclient/), [HTTPX2](https://pypi.org/project/httpx2/) |
| Pydantic | 2.14.1 | Я требую strict integer, заданные поля и валюты | [Pydantic](https://docs.pydantic.dev/latest/concepts/strict_mode/) |
| uv | 0.13.1 локально | Я создаю локальную venv и universal lock с hashes; для обычного запуска достаточно pip | [uv](https://docs.astral.sh/uv/pip/compile/) |
| Git | 2.53.0 локально | Я использую собственный корень, codex/ и явный allowlist | [Git](https://git-scm.com/docs) |
| GitHub Actions | checkout `3d3c42e5aac5ba805825da76410c181273ba90b1`; setup-python `5fda3b95a4ea91299a34e894583c3862153e4b97` | Я закрепил действия по commit SHA и выпускаю архив после двух проверок | [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) |
| OpenAPI / Swagger UI | Схему задаёт FastAPI; UI поставляется стандартной страницей /docs | Я пробую запросы вручную; JS/CSS UI требуют доступ к CDN | [FastAPI metadata/docs](https://fastapi.tiangolo.com/tutorial/metadata/) |

Я использую стандартную библиотеку: pathlib, sqlite3, contextlib, uuid,
argparse, tempfile, threading, concurrent.futures, socket, urllib, subprocess,
zipfile, hashlib, json, shutil и re. Отдельных пакетов для них не устанавливаю.
Для IDE я положил обычные JSON tasks/launch; Python/debugpy расширения редактора
опциональны и в runtime зависимостями не являются.

## Как я фиксирую транзитивные зависимости

Я храню точные версии и hashes всех прямых и транзитивных пакетов в lock; краткий
список ниже я получил из него автоматически. Для транзитивных компонентов я даю
официальные страницы публикации. Starlette/AnyIO обеспечивают ASGI и потоки,
pydantic-core/annotated-types/typing-inspection — валидацию, httpcore2/h11/
truststore/idna — клиентский HTTP/TLS, coverage — измерение покрытия,
sortedcontainers — внутренние структуры Hypothesis, остальные — служебные
зависимости перечисленных библиотек. `colorama` устанавливается на Windows;
`httpcore2` и `truststore` имеют условие исключения Emscripten. Universal lock
также фиксирует `httpx2-jsfetch` для Emscripten, хотя этот профиль я не запускаю.

| Distribution | Версия | Условие | Официальная публикация |
| --- | --- | --- | --- |
| `annotated-doc` | 0.0.5 | Без дополнительного условия | [PyPI](https://pypi.org/project/annotated-doc/0.0.5/) |
| `annotated-types` | 0.8.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/annotated-types/0.8.0/) |
| `anyio` | 4.15.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/anyio/4.15.1/) |
| `click` | 8.5.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/click/8.5.0/) |
| `colorama` | 0.4.6 | sys_platform == 'win32' | [PyPI](https://pypi.org/project/colorama/0.4.6/) |
| `coverage` | 7.17.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/coverage/7.17.0/) |
| `fastapi` | 0.162.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/fastapi/0.162.0/) |
| `h11` | 0.16.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/h11/0.16.0/) |
| `httpcore2` | 2.16.0 | sys_platform != 'emscripten' | [PyPI](https://pypi.org/project/httpcore2/2.16.0/) |
| `httpx2` | 2.16.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/httpx2/2.16.0/) |
| `httpx2-jsfetch` | 1.0 | sys_platform == 'emscripten' | [PyPI](https://pypi.org/project/httpx2-jsfetch/1.0/) |
| `hypothesis` | 6.170.12 | Без дополнительного условия | [PyPI](https://pypi.org/project/hypothesis/6.170.12/) |
| `idna` | 3.20 | Без дополнительного условия | [PyPI](https://pypi.org/project/idna/3.20/) |
| `iniconfig` | 2.3.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/iniconfig/2.3.1/) |
| `opentelemetry-api` | 1.45.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/opentelemetry-api/1.45.1/) |
| `packaging` | 26.3 | Без дополнительного условия | [PyPI](https://pypi.org/project/packaging/26.3/) |
| `pluggy` | 1.7.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/pluggy/1.7.0/) |
| `pydantic` | 2.14.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/pydantic/2.14.1/) |
| `pydantic-core` | 2.50.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/pydantic-core/2.50.1/) |
| `pygments` | 2.21.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/pygments/2.21.0/) |
| `pytest` | 9.1.1 | Без дополнительного условия | [PyPI](https://pypi.org/project/pytest/9.1.1/) |
| `pytest-cov` | 7.1.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/pytest-cov/7.1.0/) |
| `sortedcontainers` | 2.4.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/sortedcontainers/2.4.0/) |
| `starlette` | 1.10.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/starlette/1.10.0/) |
| `truststore` | 0.10.5 | sys_platform != 'emscripten' | [PyPI](https://pypi.org/project/truststore/0.10.5/) |
| `typing-extensions` | 4.16.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/typing-extensions/4.16.0/) |
| `typing-inspection` | 0.4.4 | Без дополнительного условия | [PyPI](https://pypi.org/project/typing-inspection/0.4.4/) |
| `uvicorn` | 0.54.0 | Без дополнительного условия | [PyPI](https://pypi.org/project/uvicorn/0.54.0/) |

Я пересобираю lock командой `uv pip compile --universal --python-version 3.12
--generate-hashes --no-emit-index-url --output-file requirements.lock requirements.in`.
Обычная установка использует `pip install --require-hashes -r requirements.lock`.
Я не требую глобальной установки uv, Docker или отдельной СУБД.
