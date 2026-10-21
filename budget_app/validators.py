"""화면 출력과 파일 접근이 없는 입력값 검증·변환 함수."""

import re
from datetime import date
from typing import Literal, cast

from .errors import ValidationError


def validate_nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"{field_name}은(는) 비어 있지 않은 문자열이어야 합니다.",
            f"{field_name}에 공백 이외의 문자를 입력하세요.",
        )


def parse_date(value: str) -> date:
    try:
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
        ):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "날짜 형식이 올바르지 않거나 존재하지 않는 날짜입니다.",
            "YYYY-MM-DD 형식의 실제 날짜를 입력하세요. 예: 2024-01-15",
        ) from None


def validate_month(value: str) -> None:
    try:
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}", value) is None
        ):
            raise ValueError
        date.fromisoformat(f"{value}-01")
    except ValueError:
        raise ValidationError(
            "월 형식이 올바르지 않습니다.",
            "YYYY-MM 형식의 유효한 월을 입력하세요. 예: 2024-01",
        ) from None


def validate_amount(value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValidationError(
            "금액은 양수 정수여야 합니다.",
            "0, 음수, 소수, 불리언을 제외한 정수를 입력하세요. 예: 15000",
        )


def parse_positive_int(value: str) -> int:
    try:
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]+", value.strip()) is None
        ):
            raise ValueError
        number = int(value)
        if number <= 0:
            raise ValueError
    except ValueError:
        raise ValidationError(
            "양수 정수를 입력해야 합니다.",
            "0보다 큰 정수를 숫자로만 입력하세요. 예: 20, 15000",
        ) from None
    return number


def validate_registered_category(value: str, names: list[str]) -> str:
    validate_nonempty(value, "카테고리")
    if value not in names:
        raise ValidationError(
            f"등록되지 않은 카테고리입니다: {value}",
            "등록된 이름을 입력하세요. 새 이름은 category add로 먼저 등록하세요.",
        )
    return value


def validate_transaction_type(value: str) -> Literal["income", "expense"]:
    if not isinstance(value, str) or value not in ("income", "expense"):
        raise ValidationError(
            "허용되지 않은 거래 타입입니다.",
            "수입은 income, 지출은 expense로 입력하세요.",
        )
    return cast(Literal["income", "expense"], value)


def parse_tags(value: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ValidationError(
            "태그 입력은 문자열이어야 합니다.",
            "태그를 쉼표로 구분하거나 빈 문자열을 입력하세요.",
        )
    return tuple(tag.strip() for tag in value.split(",") if tag.strip())
