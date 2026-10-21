"""콘솔 입력 해석과 도움말 출력."""

import argparse
import sys
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any, NoReturn, TypeVar

from .decorators import handle_errors
from .errors import ValidationError
from .models import Transaction
from .repositories import CategoryStore, TransactionRepository, initialize_stores
from .services import add_category, add_transaction, remove_category
from .validators import (
    parse_date, parse_positive_int, parse_tags,
    validate_registered_category, validate_transaction_type,
)


T = TypeVar("T")


def _read_value(prompt: str, parse: Callable[[str], T]) -> T:
    while True:
        try:
            return parse(input(prompt).strip())
        except ValidationError as error:
            print(f"[오류] {error}", file=sys.stderr)
            print(f"[힌트] {error.hint}", file=sys.stderr)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(**kwargs)
        self.add_argument_group("옵션").add_argument(
            "--help", action="help", help="사용 방법을 출력하고 종료합니다."
        )

    def error(self, message: str) -> NoReturn:
        raise ValidationError(
            f"명령 또는 옵션이 올바르지 않습니다: {message}",
            f"{self.prog} --help로 사용 방법을 확인하세요.",
        )


@handle_errors
def main(argv: list[str] | None) -> int:
    parser = ArgumentParser(
        prog="python -m budget_app",
        description="파일 기반 콘솔 가계부입니다.",
    )
    parser.add_argument_group("저장 경로").add_argument(
        "--data-dir", type=Path, default=Path("./data"), metavar="경로",
        help="데이터 저장 폴더를 지정합니다. 기본값: ./data",
    )
    commands = parser.add_subparsers(dest="command", title="명령")
    category = commands.add_parser(
        "category", help="카테고리를 추가·조회·삭제합니다.",
        description="등록된 카테고리를 관리합니다.",
    )
    actions = category.add_subparsers(
        dest="category_action", required=True, title="카테고리 명령",
    )
    for action, description in (
        ("add", "카테고리명을 입력받아 추가합니다."),
        ("list", "등록된 카테고리를 조회합니다."),
        ("remove", "카테고리명을 입력받아 삭제합니다."),
    ):
        actions.add_parser(action, help=description, description=description)

    commands.add_parser(
        "add", help="거래를 대화형으로 추가합니다.",
        description="날짜·타입·카테고리·금액·메모·태그를 입력받아 저장합니다.",
    )
    listing = commands.add_parser(
        "list", help="최신순 거래 목록을 조회합니다.",
        description="날짜 내림차순으로 거래를 최대 N건 출력합니다.",
    )
    listing.add_argument_group("조회 옵션").add_argument(
        "--limit", type=parse_positive_int, default=20, metavar="N",
        help="출력할 최대 거래 건수입니다. 양수 정수, 기본값: 20",
    )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    initialize_stores(args.data_dir)
    categories = CategoryStore(args.data_dir)
    transactions = TransactionRepository(args.data_dir)
    if args.command == "add":
        date = _read_value("날짜(YYYY-MM-DD): ", parse_date)
        transaction_type = _read_value("타입(income/expense): ", validate_transaction_type)
        names = categories.load()
        print(f"등록된 카테고리: {', '.join(names)}")
        category_name = _read_value(
            "카테고리: ", lambda value: validate_registered_category(value, names),
        )
        amount = _read_value("금액(양수 정수): ", parse_positive_int)
        memo = input("메모(선택): ")
        tags = parse_tags(input("태그(쉼표로 구분, 없으면 엔터): "))
        transaction_id = add_transaction(
            Transaction(
                id=transactions.new_id(), type=transaction_type, date=date,
                amount=amount, category=category_name, memo=memo, tags=tags,
            ),
            categories, transactions,
        )
        print(f"[저장 완료] id={transaction_id}")
    elif args.command == "list":
        count = 0
        with closing(transactions.iter_transactions()) as existing:
            for count, transaction in enumerate(existing, 1):
                print(
                    f"{transaction.id} | {transaction.date.isoformat()} | {transaction.type} | "
                    f"{transaction.category} | {transaction.amount} | {transaction.memo} | "
                    f"{', '.join(transaction.tags)}"
                )
                if count >= args.limit:
                    break
        if count == 0:
            print("거래 내역이 없습니다.")
    elif args.category_action == "list":
        for name in categories.load():
            print(f"- {name}")
    elif args.category_action == "add":
        name = add_category(input("카테고리명: "), categories)
        print(f"[저장 완료] category={name}")
    else:
        name = remove_category(
            input("카테고리명: "), categories, transactions,
        )
        print(f"[삭제 완료] category={name}")
    return 0
