from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from app.models import Base, engine, seed_products
from app.controllers import router as user_router

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'views/templates'))

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_products()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

app.include_router(user_router)
