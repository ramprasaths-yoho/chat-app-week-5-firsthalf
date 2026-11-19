from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import chat, sessions, usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # or run schema.sql by hand
    yield


app = FastAPI(title="AI Chat App", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(usage.router)
