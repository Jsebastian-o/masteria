from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from .routers.estimations import router as estimations_router
from .routers.sessions import router as sessions_router

app = FastAPI()
app.include_router(estimations_router)
app.include_router(sessions_router)
