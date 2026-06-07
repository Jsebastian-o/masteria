from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from .routers.estimations import router

app = FastAPI()
app.include_router(router)
