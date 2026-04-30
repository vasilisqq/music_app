import logging
import os
from datetime import datetime

import uvicorn

# from app.core.config import settings
# from app.core.redis import redis_client
# from app.core.middleware import LoggingMiddleware, ErrorHandlingMiddleware
from api import api_router
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

os.makedirs("server/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("server/logs/app.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# Декоратор для создания асинхронного контекстного менеджера жизненного цикла приложения
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
    openapi_url="/api/v1/openapi.json",
)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return await http_exception_handler(request, exc)


# ✅ Обработчик всех остальных исключений
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ✅ Healthcheck
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# порядок важен - они выполняются в обратном порядке
# app.add_middleware(ErrorHandlingMiddleware)
# app.add_middleware(LoggingMiddleware)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Разрешенные домены
#     allow_credentials=True,  # Разрешить куки и авторизацию
#     allow_methods=["*"],  # Разрешенные HTTP-методы
#     allow_headers=["*"],  # Разрешенные заголовки
# )

# Подключение роутеров
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "FastAPI Auth Project"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
