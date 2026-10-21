"""CLI 오류를 사용자 메시지와 종료 코드로 변환."""

import sys
from collections.abc import Callable
from functools import wraps

from .errors import AppError, ValidationError


def handle_errors(
    func: Callable[[list[str] | None], int],
) -> Callable[[list[str] | None], int]:
    @wraps(func)
    def wrapper(argv: list[str] | None) -> int:
        try:
            return func(argv)
        except AppError as error:
            message, hint = str(error), error.hint
            exit_code = 2 if isinstance(error, ValidationError) else 1
        except OSError as error:
            message = f"파일 작업에 실패했습니다: {error}"
            hint = "파일 경로, 접근 권한과 저장 공간을 확인하세요."
            exit_code = 1
        except EOFError:
            message = "입력이 종료되었습니다."
            hint = "명령을 다시 실행하고 필요한 값을 입력하세요."
            exit_code = 1
        except KeyboardInterrupt:
            message = "사용자가 작업을 취소했습니다."
            hint = "작업을 계속하려면 명령을 다시 실행하세요."
            exit_code = 130
        except Exception:
            message = "예상하지 못한 오류가 발생했습니다."
            hint = "입력값을 확인하고 문제가 반복되면 실행한 명령과 상황을 알려주세요."
            exit_code = 1

        print(f"[오류] {message}", file=sys.stderr)
        print(f"[힌트] {hint}", file=sys.stderr)
        return exit_code

    return wrapper
