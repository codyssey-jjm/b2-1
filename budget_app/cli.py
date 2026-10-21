"""콘솔 입력 해석과 도움말 출력."""

import argparse
from typing import NoReturn

from .decorators import handle_errors
from .errors import ValidationError


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValidationError(
            f"명령 또는 옵션이 올바르지 않습니다: {message}",
            "python -m budget_app --help로 사용 방법을 확인하세요.",
        )


@handle_errors
def main(argv: list[str] | None) -> int:
    parser = ArgumentParser(
        prog="python -m budget_app",
        description="파일 기반 콘솔 가계부입니다.",
        add_help=False,
    )
    parser.add_argument_group("옵션").add_argument(
        "--help", action="help", help="사용 방법을 출력하고 종료합니다."
    )
    parser.parse_args(argv)
    parser.print_help()
    return 0
