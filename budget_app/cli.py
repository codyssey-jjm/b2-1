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
from .repositories import BudgetStore, CategoryStore, TransactionRepository, initialize_stores
from .services import (
    add_category, add_transaction, delete_transaction, remove_category,
    search_transactions, set_budget, summarize_month, update_transaction,
)
from .validators import (
    parse_date, parse_positive_int, parse_tags,
    validate_date_range, validate_month, validate_nonempty,
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

    updating = commands.add_parser(
        "update", help="ID로 거래의 지정한 필드를 수정합니다.",
        description="변경할 필드를 하나 이상 지정합니다. 생략한 필드는 유지합니다.",
    )
    update_options = updating.add_argument_group("수정 옵션")
    update_options.add_argument("--id", required=True, metavar="ID", help="수정할 거래 ID입니다.")
    update_options.add_argument(
        "--date", type=parse_date, metavar="YYYY-MM-DD", help="변경할 날짜입니다.",
    )
    update_options.add_argument(
        "--type", type=validate_transaction_type, metavar="income/expense", help="변경할 타입입니다.",
    )
    update_options.add_argument("--category", metavar="이름", help="등록된 카테고리 이름입니다.")
    update_options.add_argument(
        "--amount", type=parse_positive_int, metavar="금액", help="변경할 금액입니다. 양수 정수만 허용합니다.",
    )
    update_options.add_argument("--memo", metavar="메모", help='변경할 메모입니다. ""로 비웁니다.')
    update_options.add_argument(
        "--tags", type=parse_tags, metavar="태그", help='쉼표로 구분한 태그입니다. ""로 비웁니다.',
    )
    deleting = commands.add_parser(
        "delete", help="ID로 거래 한 건을 삭제합니다.", description="지정한 ID의 거래를 삭제합니다.",
    )
    deleting.add_argument_group("삭제 옵션").add_argument(
        "--id", required=True, metavar="ID", help="삭제할 거래 ID입니다.",
    )

    searching = commands.add_parser(
        "search", help="조건에 맞는 거래를 최신순으로 검색합니다.",
        description="지정한 조건을 모두 적용합니다. 조건이 없으면 전체 거래를 조회합니다.",
    )
    search_options = searching.add_argument_group("검색 조건")
    search_options.add_argument(
        "--from", dest="start_date", type=parse_date, metavar="YYYY-MM-DD",
        help="시작일입니다. 해당 날짜를 포함합니다.",
    )
    search_options.add_argument(
        "--to", dest="end_date", type=parse_date, metavar="YYYY-MM-DD",
        help="종료일입니다. 해당 날짜를 포함합니다.",
    )
    search_options.add_argument(
        "--category", metavar="이름", help="등록된 카테고리와 정확히 일치하는 거래를 찾습니다.",
    )
    search_options.add_argument(
        "--type", type=validate_transaction_type, metavar="income/expense",
        help="거래 타입을 지정합니다.",
    )
    search_options.add_argument(
        "--q", metavar="검색어", help="메모에 포함된 문자열을 찾습니다. 대소문자를 구분합니다.",
    )
    search_options.add_argument(
        "--tag", metavar="태그", help="태그 한 개와 정확히 일치하는 거래를 찾습니다. 대소문자를 구분합니다.",
    )

    summary = commands.add_parser(
        "summary", help="월별 합계와 카테고리별 지출 순위를 조회합니다.",
        description="지정한 월의 합계·지출 TOP N·예산 사용률과 초과 여부를 출력합니다.",
    )
    summary_options = summary.add_argument_group("요약 옵션")
    summary_options.add_argument(
        "--month", required=True, metavar="YYYY-MM", help="조회할 월입니다.",
    )
    summary_options.add_argument(
        "--top", type=parse_positive_int, default=5, metavar="N",
        help="출력할 최대 지출 카테고리 수입니다. 양수 정수, 기본값: 5. 동률은 이름순입니다.",
    )

    budget = commands.add_parser(
        "budget", help="월별 예산을 설정하거나 조회합니다.", description="월별 지출 예산을 관리합니다.",
    )
    budget_actions = budget.add_subparsers(
        dest="budget_action", required=True, title="예산 명령",
    )
    for action, description in (
        ("set", "지정한 월의 예산을 저장합니다. 기존 예산은 새 금액으로 변경합니다."),
        ("show", "지정한 월의 예산을 조회합니다."),
    ):
        budget_command = budget_actions.add_parser(action, help=description, description=description)
        budget_options = budget_command.add_argument_group("예산 옵션")
        budget_options.add_argument(
            "--month", required=True, metavar="YYYY-MM", help="설정하거나 조회할 월입니다.",
        )
        if action == "set":
            budget_options.add_argument(
                "--amount", required=True, type=parse_positive_int, metavar="금액",
                help="월별 예산 금액입니다. 양수 정수만 허용합니다.",
            )

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command in {"update", "delete"}:
        validate_nonempty(args.id, "거래 ID")
    if args.command == "update":
        changes = {
            name: getattr(args, name)
            for name in ("date", "type", "category", "amount", "memo", "tags")
            if getattr(args, name) is not None
        }
        if not changes:
            raise ValidationError(
                "수정할 필드를 하나 이상 지정해야 합니다.",
                "update --help로 변경할 필드 옵션을 확인하세요.",
            )
        if args.category is not None:
            validate_nonempty(args.category, "카테고리")

    if args.command == "search":
        validate_date_range(args.start_date, args.end_date)
        for value, field_name in (
            (args.category, "카테고리"), (args.q, "메모 검색어"), (args.tag, "태그"),
        ):
            if value is not None:
                validate_nonempty(value, field_name)

    if args.command in {"summary", "budget"}:
        validate_month(args.month)

    initialize_stores(args.data_dir)
    categories = CategoryStore(args.data_dir)
    transactions = TransactionRepository(args.data_dir)
    budgets = BudgetStore(args.data_dir)
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
    elif args.command in {"list", "search"}:
        if args.command == "search":
            results = search_transactions(
                categories, transactions, start_date=args.start_date, end_date=args.end_date,
                category=args.category, transaction_type=args.type, query=args.q, tag=args.tag,
            )
            limit = None
        else:
            results = transactions.iter_transactions()
            limit = args.limit
        count = 0
        with closing(results) as existing:
            for count, transaction in enumerate(existing, 1):
                print(
                    f"{transaction.id} | {transaction.date.isoformat()} | {transaction.type} | "
                    f"{transaction.category} | {transaction.amount} | {transaction.memo} | "
                    f"{', '.join(transaction.tags)}"
                )
                if limit is not None and count >= limit:
                    break
        if count == 0:
            print("조건에 맞는 거래가 없습니다." if args.command == "search" else "거래 내역이 없습니다.")
    elif args.command == "summary":
        budget_amount = budgets.load().get(args.month)
        total_income, total_expense, expense_by_category = summarize_month(args.month, transactions)
        if total_income == 0 and total_expense == 0:
            print(f"{args.month} 거래 데이터가 없습니다.")
        else:
            print(f"총 수입: {total_income}원")
            print(f"총 지출: {total_expense}원")
            print(f"잔액: {total_income - total_expense}원")
        if budget_amount is None:
            print("예산이 설정되어 있지 않습니다.")
        else:
            usage_tenths, remainder = divmod(total_expense * 1000, budget_amount)
            if remainder * 2 >= budget_amount:
                usage_tenths += 1
            print(f"예산: {budget_amount}원 (사용률 {usage_tenths // 10}.{usage_tenths % 10}%)")
            if total_expense > budget_amount:
                print(f"[경고] 예산을 {total_expense - budget_amount}원 초과했습니다.")
        if expense_by_category:
            ranked = sorted(
                expense_by_category.items(), key=lambda item: (-item[1], item[0]),
            )[:args.top]
            print(f"\n지출 TOP {args.top}")
            for rank, (name, amount) in enumerate(ranked, 1):
                print(f"{rank}) {name} {amount}원")
        elif total_income > 0:
            print("지출 내역이 없습니다.")
    elif args.command == "budget":
        if args.budget_action == "set":
            amount = set_budget(args.month, args.amount, budgets)
            print(f"[저장 완료] {args.month} 예산 {amount}원")
        else:
            amount = budgets.load().get(args.month)
            if amount is None:
                print(f"{args.month} 예산이 설정되어 있지 않습니다.")
            else:
                print(f"{args.month} 예산: {amount}원")
    elif args.command == "update":
        transaction_id = update_transaction(args.id, changes, categories, transactions)
        print(f"[수정 완료] id={transaction_id}")
    elif args.command == "delete":
        transaction_id = delete_transaction(args.id, transactions)
        print(f"[삭제 완료] id={transaction_id}")
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
