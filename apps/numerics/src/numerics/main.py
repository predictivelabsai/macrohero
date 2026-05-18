"""MacroHero numerics service — FastAPI app entrypoint."""

from fastapi import FastAPI

from numerics.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MacroHero Numerics",
        version="0.1.0",
        # Internal service: no docs in production. Comment this out locally
        # if you want /docs and /redoc back.
        # docs_url=None,
        # redoc_url=None,
    )
    app.include_router(router)
    return app


app = create_app()
