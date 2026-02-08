from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
# from app.core.config import settings
# from app.core.redis import redis_client
# from app.core.middleware import LoggingMiddleware, ErrorHandlingMiddleware
# from app.api.v1.router import api_router

#Декоратор для создания асинхронного контекстного менеджера жизненного цикла приложения
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     await redis_client.connect()
#     yield
#     # Shutdown
#     await redis_client.disconnect()

app = FastAPI(
    title="music_app",
    version="1.0.0",
    description="FastAPI приложение с полной системой аутентификации",
    openapi_url="/api/v1/openapi.json"
)

#порядок важен - они выполняются в обратном порядке
# app.add_middleware(ErrorHandlingMiddleware)
# app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешенные домены
    allow_credentials=True,  # Разрешить куки и авторизацию
    allow_methods=["*"],  # Разрешенные HTTP-методы
    allow_headers=["*"],  # Разрешенные заголовки
)

# Подключение роутеров
# app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "FastAPI Auth Project"}

if __name__ == "__main__":
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )