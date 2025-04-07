from functools import partial

from fastapi import FastAPI

from api.categories import categories_router
from api.helpers import custom_openapi
from api.products import products_router

app = FastAPI()
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(categories_router, prefix="/categories", tags=["categories"])

app.openapi = partial(custom_openapi, app)  # type: ignore[method-assign]
