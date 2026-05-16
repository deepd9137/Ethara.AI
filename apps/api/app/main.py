from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Team Task Manager")
    return app


app = create_app()
