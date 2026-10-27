"""Я оставляю HTTP-валидацию здесь, денежный инвариант — в транзакционном Store."""

from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .store import BusinessError, Store

ORDER_PATTERN = r"^[A-Z0-9][A-Z0-9-]{0,39}$"
KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
OrderId = Annotated[str, ApiPath(pattern=ORDER_PATTERN, max_length=40)]
Money = Annotated[int, Field(ge=1, le=100_000_000)]


class RefundInput(BaseModel):
    # Я отклоняю bool, float и строку "100": контракт принимает только JSON integer.
    model_config = ConfigDict(strict=True, extra="forbid")
    amount_minor: Money
    currency: Literal["RUB", "USD"]


class OrderInput(RefundInput):
    order_id: Annotated[str, Field(pattern=ORDER_PATTERN, max_length=40)]


def create_app(database: Path) -> FastAPI:
    store = Store(database)
    app = FastAPI(title="Мой стенд проверки возвратов", version=__version__,
                  description="Я проверяю учебный API на синтетических заказах; реальные деньги не перевожу.")

    @app.exception_handler(BusinessError)
    async def business_error(_request, error: BusinessError):
        headers = {"Retry-After": "1"} if error.status == 503 else None
        return JSONResponse(status_code=error.status, headers=headers,
                            content={"error": {"code": error.code, "message": error.message}})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request, error: RequestValidationError):
        # Я показываю место и тип ошибки, не отражаю присланные значения в ответ.
        return JSONResponse(status_code=422, content={
            "error": {"code": "VALIDATION_ERROR", "message": "Я отклонил запрос, нарушающий контракт."},
            "issues": [{"location": list(e["loc"]), "type": e["type"]} for e in error.errors()],
        })

    @app.get("/health", summary="Я проверяю доступность процесса")
    def health():
        return {"status": "ok", "version": __version__}

    @app.post("/orders", status_code=201, summary="Я сохраняю синтетический оплаченный заказ")
    def create_order(body: OrderInput):
        return store.create_order(body.order_id, body.amount_minor, body.currency)

    @app.get("/orders/{order_id}", summary="Я читаю сумму и остаток возврата")
    def get_order(order_id: OrderId):
        return store.get_order(order_id)

    @app.post("/orders/{order_id}/refunds", summary="Я создаю или повторяю частичный возврат")
    def refund(order_id: OrderId, body: RefundInput,
               idempotency_key: Annotated[str, Header(pattern=KEY_PATTERN, max_length=64)]):
        result, replay = store.refund(order_id, body.amount_minor, body.currency, idempotency_key)
        return JSONResponse(status_code=200 if replay else 201, content=result,
                            headers={"Idempotency-Replayed": "true" if replay else "false"})

    return app
