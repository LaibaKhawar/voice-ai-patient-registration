"""Consistent JSON response envelope: {"data": ..., "error": null}."""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Raise anywhere in a request to return an enveloped error response."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def ok(data: Any, status_code: int = 200, meta: dict | None = None) -> JSONResponse:
    body: dict[str, Any] = {"data": jsonable_encoder(data), "error": None}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(body, status_code=status_code)


def fail(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = jsonable_encoder(details)
    return JSONResponse({"data": None, "error": error}, status_code=status_code)
