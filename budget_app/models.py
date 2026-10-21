"""거래 데이터 구조와 생성 시점의 유효성 검증."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from .errors import ValidationError
from .validators import validate_amount, validate_nonempty, validate_transaction_type


TransactionType = Literal["income", "expense"]


@dataclass(frozen=True)
class Transaction:
    id: str
    type: TransactionType
    date: date
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_nonempty(self.id, "거래 ID")
        validate_transaction_type(self.type)
        if type(self.date) is not date:
            raise ValidationError(
                "거래 날짜는 datetime.date 객체여야 합니다.",
                "YYYY-MM-DD 문자열을 parse_date()로 변환하세요.",
            )
        validate_amount(self.amount)
        validate_nonempty(self.category, "카테고리")
        if not isinstance(self.memo, str):
            raise ValidationError(
                "메모는 문자열이어야 합니다.",
                "메모를 문자열로 입력하거나 빈 문자열로 생략하세요.",
            )
        if not isinstance(self.tags, tuple):
            raise ValidationError(
                "태그는 문자열 튜플이어야 합니다.",
                "쉼표로 구분한 문자열을 parse_tags()로 변환하세요.",
            )
        for tag in self.tags:
            validate_nonempty(tag, "태그")
