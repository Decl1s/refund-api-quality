"""Я сохраняю заказы и возвраты; инвариант суммы защищаю транзакцией SQLite."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from uuid import uuid4


class BusinessError(Exception):
    """Я передаю ожидаемый отказ в API без SQL и внутреннего состояния."""

    def __init__(self, code: str, status: int, message: str):
        super().__init__(message)
        self.code, self.status, self.message = code, status, message


def new_refund_id() -> str:
    return "RF-" + uuid4().hex


class Store:
    def __init__(self, path: Path):
        # Я принимаю путь явно: каждый тест получает свою БД, импорт не создаёт файл.
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    amount_minor INTEGER NOT NULL CHECK(amount_minor BETWEEN 1 AND 100000000),
                    currency TEXT NOT NULL CHECK(currency IN ('RUB', 'USD'))
                );
                CREATE TABLE IF NOT EXISTS refunds (
                    refund_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    amount_minor INTEGER NOT NULL CHECK(amount_minor BETWEEN 1 AND 100000000),
                    currency TEXT NOT NULL CHECK(currency IN ('RUB', 'USD'))
                );
                CREATE INDEX IF NOT EXISTS refunds_order ON refunds(order_id);
            """)

    @contextmanager
    def connection(self, *, write: bool = False):
        con = sqlite3.connect(self.path, timeout=3, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            # Я захватываю writer до чтения суммы: иначе два запроса прочтут
            # один остаток. Проверка, запись и COMMIT составляют одну операцию.
            if write:
                con.execute("BEGIN IMMEDIATE")
            yield con
            if write:
                con.commit()
        except sqlite3.OperationalError as error:
            con.rollback()
            if error.sqlite_errorcode in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise BusinessError("STORE_BUSY", 503, "Я не смог получить блокировку; запрос можно повторить.") from error
            raise
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def create_order(self, order_id: str, amount_minor: int, currency: str) -> dict:
        with self.connection(write=True) as con:
            if con.execute("SELECT 1 FROM orders WHERE order_id=?", (order_id,)).fetchone():
                raise BusinessError("ORDER_EXISTS", 409, "Я уже сохранил заказ с этим идентификатором.")
            con.execute("INSERT INTO orders VALUES (?, ?, ?)", (order_id, amount_minor, currency))
        return self.get_order(order_id)

    def get_order(self, order_id: str) -> dict:
        # Одно SQL-выражение даёт согласованный снимок заказа и его возвратов.
        with self.connection() as con:
            row = con.execute("""
                SELECT o.order_id, o.amount_minor, o.currency,
                       COALESCE(SUM(r.amount_minor), 0) AS refunded_minor,
                       COUNT(r.refund_id) AS refund_count
                FROM orders o LEFT JOIN refunds r USING(order_id)
                WHERE o.order_id=? GROUP BY o.order_id
            """, (order_id,)).fetchone()
        if row is None:
            raise BusinessError("ORDER_NOT_FOUND", 404, "Я не нашёл заказ.")
        result = dict(row)
        result["remaining_minor"] = result["amount_minor"] - result["refunded_minor"]
        return result

    def refund(self, order_id: str, amount_minor: int, currency: str, key: str) -> tuple[dict, bool]:
        with self.connection(write=True) as con:
            previous = con.execute("SELECT * FROM refunds WHERE idempotency_key=?", (key,)).fetchone()
            if previous is not None:
                if (previous["order_id"], previous["amount_minor"], previous["currency"]) != (order_id, amount_minor, currency):
                    raise BusinessError("IDEMPOTENCY_CONFLICT", 409, "Я уже использовал ключ для другого возврата.")
                # Я возвращаю сохранённый факт, не создавая новый refund_id.
                return self.public_refund(previous), True
            order = con.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
            if order is None:
                raise BusinessError("ORDER_NOT_FOUND", 404, "Я не нашёл заказ.")
            if order["currency"] != currency:
                raise BusinessError("CURRENCY_MISMATCH", 409, "Я не смешиваю валюты заказа и возврата.")
            used = con.execute("SELECT COALESCE(SUM(amount_minor), 0) FROM refunds WHERE order_id=?", (order_id,)).fetchone()[0]
            if used + amount_minor > order["amount_minor"]:
                raise BusinessError("REFUND_LIMIT_EXCEEDED", 409, "Я не возвращаю больше оплаченной суммы.")
            refund_id = new_refund_id()
            con.execute("INSERT INTO refunds VALUES (?, ?, ?, ?, ?)", (refund_id, key, order_id, amount_minor, currency))
            return {"refund_id": refund_id, "order_id": order_id, "amount_minor": amount_minor, "currency": currency}, False

    @staticmethod
    def public_refund(row: sqlite3.Row) -> dict:
        return {name: row[name] for name in ("refund_id", "order_id", "amount_minor", "currency")}
