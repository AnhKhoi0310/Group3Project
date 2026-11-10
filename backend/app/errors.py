from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import NAME_REQUIRED, URL_REQUIRED

FALLBACK_MESSAGES = {"name": NAME_REQUIRED, "source_url": URL_REQUIRED}


class ApiError(Exception):
    """An expected failure, returned to the client in the standard error shape."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


async def handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with user-safe messages per field, never the rejected input."""
    field_errors: dict[str, str] = {}
    for error in exc.errors():
        loc = error["loc"]
        if len(loc) < 2 or loc[0] != "body":
            continue
        field = str(loc[1])
        if field in field_errors:
            continue
        if error["type"] == "value_error":
            message = str(error["msg"]).removeprefix("Value error, ")
        else:
            message = FALLBACK_MESSAGES.get(field, "That value isn't valid.")
        field_errors[field] = message
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "Please correct the highlighted fields.",
            "fieldErrors": field_errors,
        },
    )
