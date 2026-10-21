"""화면 출력과 파일 접근이 없는 거래 필드 검증 함수."""

import re
from datetime import date

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


def validate_amount(value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValidationError(
            "금액은 양수 정수여야 합니다.",
            "0, 음수, 소수, 불리언을 제외한 정수를 입력하세요. 예: 15000",
        )


def validate_transaction_type(value: str) -> None:
    if not isinstance(value, str) or value not in ("income", "expense"):
        raise ValidationError(
            "허용되지 않은 거래 타입입니다.",
            "수입은 income, 지출은 expense로 입력하세요.",
        )


def parse_tags(value: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise ValidationError(
            "태그 입력은 문자열이어야 합니다.",
            "태그를 쉼표로 구분하거나 빈 문자열을 입력하세요.",
        )
    return tuple(tag.strip() for tag in value.split(",") if tag.strip())
