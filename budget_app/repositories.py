"""JSONL 저장소와 원본을 보존하는 파일 교체."""

import json
import os
from collections.abc import Generator, Iterable
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import uuid4

from .errors import AppError, ValidationError
from .models import Transaction
from .validators import parse_date, validate_amount, validate_month, validate_nonempty


JsonRecord = dict[str, Any]
DEFAULT_CATEGORIES = ("food", "transport", "rent", "salary", "etc")


def _data_error(path: Path, line_number: int, reason: str) -> AppError:
    return AppError(
        f"{path}:{line_number} 저장 데이터가 올바르지 않습니다: {reason}",
        "해당 행의 JSON 형식과 필드 값을 확인한 뒤 다시 실행하세요.",
    )


def _read_jsonl(path: Path) -> Generator[tuple[int, JsonRecord], None, None]:
    try:
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("각 행은 JSON 객체여야 합니다.")
                except ValueError as error:
                    raise _data_error(path, line_number, str(error)) from None
                yield line_number, record
    except UnicodeError:
        raise AppError(
            f"{path} 파일의 문자 인코딩이 올바르지 않습니다.",
            "파일을 UTF-8 형식으로 저장하세요.",
        ) from None


def _write_jsonl(path: Path, records: Generator[JsonRecord, None, None]) -> None:
    # ponytail: 단일 프로세스 쓰기 전제, 동시 쓰기가 필요하면 파일 잠금을 추가한다.
    temporary_path: Path | None = None
    try:
        with closing(records), NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as output:
            temporary_path = Path(output.name)
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        os.replace(output.name, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _transaction_key(transaction: Transaction) -> tuple[int, str]:
    return -transaction.date.toordinal(), transaction.id


def _transaction_record(transaction: Transaction) -> JsonRecord:
    return {
        "id": transaction.id,
        "type": transaction.type,
        "date": transaction.date.isoformat(),
        "amount": transaction.amount,
        "category": transaction.category,
        "memo": transaction.memo,
        "tags": list(transaction.tags),
    }


class TransactionRepository:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "transactions.jsonl"

    def new_id(self) -> str:
        return f"TX-{uuid4().hex}"

    def iter_transactions(self) -> Generator[Transaction, None, None]:
        previous_key: tuple[int, str] | None = None
        with closing(_read_jsonl(self.path)) as records:
            for line_number, record in records:
                try:
                    if record.keys() - {
                        "id", "type", "date", "amount", "category", "memo", "tags",
                    }:
                        raise ValueError("지원하지 않는 거래 필드가 있습니다.")
                    tags = record.get("tags", [])
                    if not isinstance(tags, list):
                        raise ValueError("tags는 문자열 배열이어야 합니다.")
                    transaction = Transaction(
                        id=record["id"], type=record["type"],
                        date=parse_date(record["date"]), amount=record["amount"],
                        category=record["category"], memo=record.get("memo", ""),
                        tags=tuple(tags),
                    )
                except (KeyError, ValueError, TypeError, ValidationError) as error:
                    raise _data_error(self.path, line_number, str(error)) from None
                key = _transaction_key(transaction)
                if previous_key is not None and key < previous_key:
                    raise _data_error(
                        self.path, line_number, "거래의 정렬 순서가 올바르지 않습니다.",
                    )
                previous_key = key
                yield transaction

    def get(self, transaction_id: str) -> Transaction:
        with closing(self.iter_transactions()) as existing:
            for transaction in existing:
                if transaction.id == transaction_id:
                    return transaction
        raise AppError(
            f"없는 거래 ID입니다: {transaction_id}",
            "list로 거래 ID를 확인하고 다시 실행하세요.",
        )

    def insert(self, transaction: Transaction) -> None:
        self._rewrite(transaction.id, transaction, require_existing=False)

    def update(self, transaction: Transaction) -> None:
        self._rewrite(transaction.id, transaction, require_existing=True)

    def delete(self, transaction_id: str) -> None:
        self._rewrite(transaction_id, None, require_existing=True)

    def _rewrite(
        self, transaction_id: str, transaction: Transaction | None, *, require_existing: bool,
    ) -> None:
        # ponytail: 변경마다 전체 파일 재작성, 대량 가져오기 병목 시 일괄 병합으로 전환한다.
        def records() -> Generator[JsonRecord, None, None]:
            found = False
            inserted = False
            with closing(self.iter_transactions()) as existing:
                for current in existing:
                    if current.id == transaction_id:
                        if not require_existing or found:
                            raise AppError(
                                f"중복된 거래 ID입니다: {transaction_id}",
                                "거래 ID를 확인하고 저장 파일의 중복 데이터를 정리하세요.",
                            )
                        found = True
                        continue
                    if (
                        transaction is not None and not inserted
                        and _transaction_key(transaction) < _transaction_key(current)
                    ):
                        yield _transaction_record(transaction)
                        inserted = True
                    yield _transaction_record(current)
            if require_existing and not found:
                raise AppError(
                    f"없는 거래 ID입니다: {transaction_id}",
                    "list로 거래 ID를 확인하고 다시 실행하세요.",
                )
            if transaction is not None and not inserted:
                yield _transaction_record(transaction)

        _write_jsonl(self.path, records())


class CategoryStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "categories.jsonl"

    def load(self) -> list[str]:
        names: list[str] = []
        with closing(_read_jsonl(self.path)) as records:
            for line_number, record in records:
                try:
                    if set(record) != {"name"}:
                        raise ValueError("카테고리에는 name 필드만 필요합니다.")
                    name = record["name"]
                    validate_nonempty(name, "카테고리")
                    if name in names:
                        raise ValueError("중복된 카테고리입니다.")
                except (KeyError, ValueError, ValidationError) as error:
                    raise _data_error(self.path, line_number, str(error)) from None
                names.append(name)
        return names

    def save(self, names: Iterable[str]) -> None:
        def records() -> Generator[JsonRecord, None, None]:
            seen: set[str] = set()
            for name in names:
                validate_nonempty(name, "카테고리")
                if name in seen:
                    raise ValidationError("중복된 카테고리입니다.", "서로 다른 이름을 입력하세요.")
                seen.add(name)
                yield {"name": name}

        _write_jsonl(self.path, records())


class BudgetStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "budgets.jsonl"

    def load(self) -> dict[str, int]:
        budgets: dict[str, int] = {}
        with closing(_read_jsonl(self.path)) as records:
            for line_number, record in records:
                try:
                    if set(record) != {"month", "amount"}:
                        raise ValueError("예산에는 month와 amount 필드가 필요합니다.")
                    month, amount = record["month"], record["amount"]
                    validate_month(month)
                    validate_amount(amount)
                    if month in budgets:
                        raise ValueError("중복된 월 예산입니다.")
                except (KeyError, ValueError, ValidationError) as error:
                    raise _data_error(self.path, line_number, str(error)) from None
                budgets[month] = amount
        return budgets

    def save(self, budgets: dict[str, int]) -> None:
        def records() -> Generator[JsonRecord, None, None]:
            for month, amount in budgets.items():
                validate_month(month)
                validate_amount(amount)
                yield {"month": month, "amount": amount}

        _write_jsonl(self.path, records())


def initialize_stores(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in ("transactions.jsonl", "categories.jsonl", "budgets.jsonl"):
        path = data_dir / name
        try:
            with path.open("x", encoding="utf-8"):
                pass
        except FileExistsError:
            if not path.is_file():
                raise AppError(
                    f"저장 경로가 파일이 아닙니다: {path}",
                    "다른 데이터 저장 폴더를 지정하세요.",
                ) from None
    categories = CategoryStore(data_dir)
    if not categories.load():
        categories.save(DEFAULT_CATEGORIES)
