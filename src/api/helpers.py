from typing import Any

from fastapi import FastAPI
from fastapi import Header
from fastapi.openapi.utils import get_openapi
from fastapi.params import Header as HeaderParam


def HeaderNoSchema(*args: Any, **kwargs: Any) -> HeaderParam:
    return Header(*args, include_in_schema=False, **kwargs)  # type: ignore[no-any-return]


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Inventory API",
        version="1.0",
        routes=app.routes,
        servers=[{"url": "/inventory"}],
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BasicAuth": {"type": "http", "scheme": "basic"}
    }
    openapi_schema["security"] = [{"BasicAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema
