# Refund API Quality Lab

[← Каталог моих проектов](https://github.com/Decl1s/Decl1s/blob/main/PROJECTS.md) · [С чего я начинаю](START_HERE.md) · [Контракт и решения](TEST_PLAN.md) · [Что я проверил](VALIDATION.md)

Я проверяю частичный возврат, повтор ключа и конфликт суммы; затем смотрю, какие мутации находят тесты.

**Я проверяю, что частичный возврат не превышает сумму заказа, а повтор запроса не возвращает деньги второй раз.**

Я сделал небольшой учебный QA-проект в теме интернет-магазина: рабочий API,
тест-план, автоматические проверки и упражнения. Вместо настоящих платежей я
использую синтетические заказы в локальной SQLite.

**Python · FastAPI · pytest · Hypothesis · SQLite**

[Карта кода](START_HERE.md) · [Тест-план](TEST_PLAN.md) · [Подробный разбор и задания](NOTES.md) ·
[Фактические проверки](VALIDATION.md) · [Actions](https://github.com/Decl1s/refund-api-quality/actions) ·
[Релизы](https://github.com/Decl1s/refund-api-quality/releases)

## Что я показываю

| Риск | Как я его проверяю |
| --- | --- |
| Ошибка в сумме или типе | Я проверяю границы, JSON integer, валюту и неизвестные поля |
| Двойной возврат при повторе | Я повторяю `Idempotency-Key` и сравниваю тело, статус и состояние БД |
| Тот же ключ с другим содержимым | Я ожидаю 409 и сохранение исходного результата |
| Гонка за одним остатком | Я одновременно отправляю два запроса через отдельные клиенты и реальные SQLite-соединения |
| Сбой и перезапуск | Я проверяю rollback, освобождение блокировки и повтор после создания нового экземпляра приложения |
| Проверки только «для галочки» | Я вношу три контролируемые ошибки во временные копии и подтверждаю падение соответствующих тестов |

## Как я запускаю проект

Я использую Python **3.12**. Из каталога проекта создаю отдельное окружение:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python scripts/demo.py
```

На Windows я выполняю `py -3.12 -m venv .venv` и заменяю `.venv/bin/python`
на `.venv\Scripts\python.exe` в остальных командах. Транзитивные версии и
условные зависимости Windows я закрепил в `requirements.lock`.

В demo я вижу статусы **201 → 200 → 409 → 201**: возврат 3000, повтор 3000,
отказ на лишние 8000 и финальные 7000. В конце `remaining_minor=0`, `refund_count=2`.
Demo создаёт временную БД и удаляет только её после завершения.

## Как я запускаю проверки

```bash
.venv/bin/python -m pytest --cov --cov-report=term-missing --cov-report=html:reports/coverage --junitxml=reports/junit.xml -q
.venv/bin/python scripts/mutation_check.py
.venv/bin/python scripts/http_smoke.py
.venv/bin/python scripts/zip_smoke.py
```

Я получаю HTML покрытия в `reports/coverage/index.html` и JUnit XML в
`reports/junit.xml`. Мутационная проверка должна показать `detected=3, total=3`.
HTTP smoke поднимает свой временный Uvicorn на свободном loopback-порту и
останавливает его. ZIP smoke проверяет demo из распакованной поставки.

Для отдельного сценария я запускаю, например:

```bash
.venv/bin/python -m pytest tests/test_api.py::test_repeat_does_not_double_refund -v
.venv/bin/python -m pytest -m concurrency -v
```

## Как я проверяю API вручную

```bash
.venv/bin/python -m refund_api --db workspace/manual.db --port 8766
```

Я открываю **http://127.0.0.1:8766/docs**, нажимаю `Try it out` и выполняю:

1. `POST /orders`: `{"order_id":"MANUAL-1","amount_minor":10000,"currency":"RUB"}` → 201.
2. `POST /orders/MANUAL-1/refunds`: заголовок `Idempotency-Key: manual-first`, тело `{"amount_minor":3000,"currency":"RUB"}` → 201.
3. Тот же запрос с тем же ключом → 200 и прежний `refund_id`.
4. С тем же ключом и `amount_minor=3001` → 409 `IDEMPOTENCY_CONFLICT`.
5. С новым ключом и `amount_minor=8000` → 409 `REFUND_LIMIT_EXCEEDED`.
6. `GET /orders/MANUAL-1` → `refunded_minor=3000`, `remaining_minor=7000`, `refund_count=1`.

Я останавливаю процесс через Ctrl+C и запускаю с тем же `--db`: состояние и ключ
повтора сохраняются. Для новой попытки использую другой `order_id` или новый файл
БД. Повторное создание того же заказа намеренно даёт 409. Swagger UI загружает
свои статические ресурсы с CDN; без сети я использую `scripts/demo.py` и автотесты.

## Где я меняю поведение

Я меняю контракт в [app.py](refund_api/app.py), транзакции в
[store.py](refund_api/store.py), ожидаемое поведение в [TEST_PLAN.md](TEST_PLAN.md).
В [START_HERE](START_HERE.md) я оставил порядок чтения и точки остановки в IDE;
в [NOTES](NOTES.md) — пять заданий с критериями проверки.

Я держу стенд на `127.0.0.1`, без учётных записей и реального PSP. Я не использую
его для настоящих денег или интернет-деплоя. API и БД — объект моих QA-проверок;
проект остаётся компактным учебным примером, отдельно от CommerceGuard.

## Что я уточнил в версии 0.1.1

Я связал запуск, контракт, фактические проверки и общий каталог в начале README. Я сохранил бизнес-сценарии и закреплённые зависимости. Для обновлённого source-only архива я выделил patch-версию; прежний выпуск сохраняю.
