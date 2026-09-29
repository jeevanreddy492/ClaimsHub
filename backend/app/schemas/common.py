from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

T = TypeVar("T")

# Oracle NUMBER(12,2) drops trailing zeros (1200.00 comes back as 1200).
# Every money / percent field in a response goes out with exactly 2 decimals.
Money = Annotated[
    Decimal, PlainSerializer(lambda v: str(v.quantize(Decimal("0.01"))), return_type=str)
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[dict] | None = None
