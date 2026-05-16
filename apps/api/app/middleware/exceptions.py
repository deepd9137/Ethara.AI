from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse


class BusinessError(Exception):
    def __init__(
        self,
        code: str,
        message: str = "",
        status_code: int = 400,
        details: object = None,
    ) -> None:
        self.code = code
        self.message = message or code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def _error_body(code: str, message: str, details: object = None) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "details": details}}


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> ORJSONResponse:
        code = "UNAUTHORIZED" if exc.status_code == 401 else "HTTP_ERROR"
        return ORJSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, str(exc.detail)),
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(BusinessError)
    async def business_error_handler(
        request: Request, exc: BusinessError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "VALIDATION_ERROR", "Request validation failed", exc.errors()
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        import structlog

        logger = structlog.get_logger()
        logger.exception("unhandled_error", exc_info=exc)
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
        )
