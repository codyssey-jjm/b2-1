"""사용자에게 원인과 해결 힌트를 전달하는 예외."""


class AppError(Exception):
    """처리 가능한 애플리케이션 오류."""

    def __init__(self, message: str, hint: str) -> None:
        super().__init__(message)
        self.hint = hint


class ValidationError(AppError):
    """입력값이나 거래 데이터가 계약을 만족하지 않는 오류."""
