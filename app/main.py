from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import init_db
from .routes.api import router

BASE = Path(__file__).parent

@asynccontextmanager
async def lifespan(app):
    init_db(); yield

app = FastAPI(title="LaunchMate AI", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
