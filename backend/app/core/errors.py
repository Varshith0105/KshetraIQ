from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message, "details": details}})


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic may retain a raw ValueError in an error context. Encode it before
    # returning JSON so bad user input stays a 422 rather than becoming a 500.
    return error_response(422, "validation_error", "Please correct the highlighted inputs.", jsonable_encoder(exc.errors()))
