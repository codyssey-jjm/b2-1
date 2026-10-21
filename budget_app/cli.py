"""콘솔 입력 해석과 도움말 출력."""

import argparse
from pathlib import Path
from typing import Any, NoReturn

from .decorators import handle_errors
from .errors import ValidationError
from .repositories import CategoryStore, TransactionRepository, initialize_stores
from .services import add_category, remove_category


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

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    initialize_stores(args.data_dir)
    categories = CategoryStore(args.data_dir)
    if args.category_action == "list":
        for name in categories.load():
            print(f"- {name}")
    elif args.category_action == "add":
        name = add_category(input("카테고리명: "), categories)
        print(f"[저장 완료] category={name}")
    else:
        name = remove_category(
            input("카테고리명: "), categories, TransactionRepository(args.data_dir),
        )
        print(f"[삭제 완료] category={name}")
    return 0
