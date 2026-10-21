"""입력·출력과 분리한 카테고리·거래 업무 처리."""

from calendar import monthrange
from collections.abc import Callable, Generator
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from .errors import AppError, ValidationError
from .models import Transaction, TransactionType
from .repositories import (
    BudgetStore, CategoryStore, TransactionRepository, read_csv, validate_csv_destination, write_csv,
)
from .validators import (
    parse_date, parse_positive_int, parse_tags, validate_amount,
    validate_date_range, validate_export_period, validate_month,
    validate_nonempty, validate_registered_category, validate_transaction_type,
)


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


def summarize_month(
    month: str, transactions: TransactionRepository,
) -> tuple[int, int, dict[str, int]]:
    validate_month(month)
    total_income = 0
    total_expense = 0
    expense_by_category: dict[str, int] = {}
    with closing(transactions.iter_transactions()) as existing:
        for transaction in existing:
            if transaction.date.isoformat()[:7] != month:
                continue
            if transaction.type == "income":
                total_income += transaction.amount
            else:
                total_expense += transaction.amount
                expense_by_category[transaction.category] = (
                    expense_by_category.get(transaction.category, 0) + transaction.amount
                )
    return total_income, total_expense, expense_by_category


def import_transactions(
    path: Path, categories: CategoryStore, transactions: TransactionRepository,
    on_invalid: Callable[[int, ValidationError], None],
) -> tuple[int, int]:
    imported = skipped = 0
    line_number = 0
    try:
        names = categories.load()
        with closing(read_csv(path)) as records:
            for line_number, record in records:
                try:
                    if None in record or any(value is None for value in record.values()):
                        raise ValidationError(
                            "CSV 행의 열 개수가 헤더와 다릅니다.",
                            "메모·태그가 비어 있어도 헤더에 지정한 셀 개수에 맞게 작성하세요.",
                        )
                    transaction = Transaction(
                        id=transactions.new_id(), date=parse_date(record["date"]),
                        type=validate_transaction_type(record["type"]),
                        category=validate_registered_category(record["category"], names),
                        amount=parse_positive_int(record["amount"]),
                        memo=record.get("memo", ""), tags=parse_tags(record.get("tags", "")),
                    )
                except ValidationError as error:
                    skipped += 1
                    on_invalid(line_number, error)
                    continue
                transactions.insert(transaction)
                imported += 1
    except (AppError, OSError) as error:
        hint = error.hint if isinstance(error, AppError) else "입력 파일과 저장 경로의 권한·공간을 확인하세요."
        error_type = ValidationError if isinstance(error, ValidationError) else AppError
        raise error_type(
            f"CSV 가져오기 중단: imported={imported}, skipped={skipped}. "
            f"{path} (마지막으로 읽은 CSV 행: {line_number}): {error}",
            hint,
        ) from None
    return imported, skipped


def export_transactions(
    path: Path, categories: CategoryStore, transactions: TransactionRepository, *,
    month: str | None = None, start_date: date | None = None, end_date: date | None = None,
) -> int:
    validate_export_period(month, start_date, end_date)
    validate_csv_destination(path, transactions.path.parent)
    if month is not None:
        start_date = date.fromisoformat(f"{month}-01")
        end_date = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])
    return write_csv(path, search_transactions(
        categories, transactions, start_date=start_date, end_date=end_date,
    ))


def set_budget(month: str, amount: int, budgets: BudgetStore) -> int:
    validate_month(month)
    validate_amount(amount)
    existing = budgets.load()
    existing[month] = amount
    budgets.save(existing)
    return amount


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
