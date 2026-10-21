"""입력·출력과 분리한 카테고리·거래 업무 처리."""

from collections.abc import Generator
from contextlib import closing
from dataclasses import replace
from datetime import date
from typing import Any

from .errors import AppError, ValidationError
from .models import Transaction, TransactionType
from .repositories import CategoryStore, TransactionRepository
from .validators import validate_date_range, validate_nonempty, validate_registered_category


def add_transaction(
    transaction: Transaction, categories: CategoryStore, transactions: TransactionRepository,
) -> str:
    validate_registered_category(transaction.category, categories.load())
    transactions.insert(transaction)
    return transaction.id


def update_transaction(
    transaction_id: str, changes: dict[str, Any],
    categories: CategoryStore, transactions: TransactionRepository,
) -> str:
    validate_nonempty(transaction_id, "거래 ID")
    if not changes or changes.keys() - {"date", "type", "category", "amount", "memo", "tags"}:
        raise ValidationError(
            "수정할 거래 필드가 올바르지 않습니다.",
            "date, type, category, amount, memo, tags 중 하나 이상을 지정하세요. ID는 변경할 수 없습니다.",
        )
    transaction = replace(transactions.get(transaction_id), **changes)
    validate_registered_category(transaction.category, categories.load())
    transactions.update(transaction)
    return transaction.id


def delete_transaction(transaction_id: str, transactions: TransactionRepository) -> str:
    validate_nonempty(transaction_id, "거래 ID")
    transactions.delete(transaction_id)
    return transaction_id


def search_transactions(
    categories: CategoryStore, transactions: TransactionRepository, *,
    start_date: date | None = None, end_date: date | None = None,
    category: str | None = None, transaction_type: TransactionType | None = None,
    query: str | None = None, tag: str | None = None,
) -> Generator[Transaction, None, None]:
    validate_date_range(start_date, end_date)
    if category is not None:
        validate_registered_category(category, categories.load())
    with closing(transactions.iter_transactions()) as existing:
        for transaction in existing:
            if start_date is not None and transaction.date < start_date:
                continue
            if end_date is not None and transaction.date > end_date:
                continue
            if category is not None and transaction.category != category:
                continue
            if transaction_type is not None and transaction.type != transaction_type:
                continue
            if query is not None and query not in transaction.memo:
                continue
            if tag is not None and tag not in transaction.tags:
                continue
            yield transaction


def add_category(name: str, categories: CategoryStore) -> str:
    validate_nonempty(name, "카테고리")
    name = name.strip()
    names = categories.load()
    if name in names:
        raise ValidationError(
            f"이미 등록된 카테고리입니다: {name}",
            "category list로 목록을 확인하고 다른 이름을 입력하세요.",
        )
    categories.save([*names, name])
    return name


def remove_category(
    name: str, categories: CategoryStore, transactions: TransactionRepository,
) -> str:
    validate_nonempty(name, "카테고리")
    name = name.strip()
    names = categories.load()
    if name not in names:
        raise AppError(
            f"등록되지 않은 카테고리입니다: {name}",
            "category list로 목록을 확인하고 등록된 이름을 입력하세요.",
        )
    with closing(transactions.iter_transactions()) as existing:
        if any(transaction.category == name for transaction in existing):
            raise AppError(
                f"거래에서 사용 중인 카테고리는 삭제할 수 없습니다: {name}",
                "사용 중인 카테고리를 유지하고 다른 이름을 선택하세요.",
            )
    names.remove(name)
    categories.save(names)
    return name
