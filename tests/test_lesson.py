import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from pydantic import ValidationError
from datetime import datetime, timezone

# --- НАСТРОЙКА ПУТЕЙ ---
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- ИМПОРТЫ МОДУЛЕЙ ---
from schemas.lesson import LessonCreate, LessonUpdate, LessonReorderRequest, LessonResponse
from server.services.lesson_services import LessonService
from app.workers.base_worker import BaseAPIWorker


# --- Фикстуры ---

@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def lesson_service(mock_db_session):
    return LessonService(mock_db_session)


@pytest.fixture
def valid_lesson_data():
    return {
        "name": "Упражнение 1",
        "description": "Разминка пальцев",
        "difficult": 2,
        "rhythm": 4,
        "hand": "right",
        "topic_id": 1,
        "notes": {"C4": 1, "D4": 2},
    }


# --- Тесты схемы ---

class TestLessonSchema:
    """Тесты валидации и поведения Pydantic-схем уроков."""

    def test_default_values(self, valid_lesson_data):
        """Проверка: Пропущенные опциональные поля получают значения по умолчанию."""
        data = {k: v for k, v in valid_lesson_data.items() if k not in ("hand", "order_in_topic")}
        lesson = LessonCreate(**data)
        assert lesson.hand == "right"
        assert lesson.order_in_topic is None

    def test_required_fields_missing(self):
        """Проверка: Отсутствие обязательных полей вызывает ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LessonCreate(name="Только имя")
        errors = exc_info.value.errors()
        missing_fields = {e["loc"][0] for e in errors}
        assert "description" in missing_fields
        assert "difficult" in missing_fields
        assert "rhythm" in missing_fields
        assert "notes" in missing_fields
        assert "topic_id" in missing_fields

    def test_invalid_difficult_type(self, valid_lesson_data):
        """Проверка: Строка в поле difficult (ожидается int) вызывает ValidationError."""
        data = {**valid_lesson_data, "difficult": "сложно"}
        with pytest.raises(ValidationError):
            LessonCreate(**data)

    def test_invalid_rhythm_type(self, valid_lesson_data):
        """Проверка: Строка в поле rhythm (ожидается float/Decimal) вызывает ValidationError."""
        data = {**valid_lesson_data, "rhythm": "быстро"}
        with pytest.raises(ValidationError):
            LessonCreate(**data)

    def test_from_attributes_conversion(self, valid_lesson_data):
        """Проверка: Схема может быть создана из ORM-объекта с атрибутами."""
        orm_obj = Mock()
        for key, value in valid_lesson_data.items():
            setattr(orm_obj, key, value)
        orm_obj.id = 42
        orm_obj.order_in_topic = 1
        response = LessonResponse.model_validate(orm_obj)
        assert response.id == 42
        assert response.name == valid_lesson_data["name"]
        assert response.order_in_topic == 1

    def test_notes_must_be_dict(self, valid_lesson_data):
        """Проверка: notes должен быть dict, список вызывает ValidationError."""
        data = {**valid_lesson_data, "notes": ["C4", "D4"]}
        with pytest.raises(ValidationError):
            LessonCreate(**data)


# --- Тесты сервиса ---

class TestLessonService:
    """Тесты бизнес-логики сервиса уроков с мокированным доступом к БД."""

    @pytest.mark.asyncio
    async def test_create_lesson_auto_assigns_order(self, lesson_service, mock_db_session, valid_lesson_data):
        """Проверка: При создании урока без order_in_topic вычисляется следующий порядковый номер."""
        data = {k: v for k, v in valid_lesson_data.items() if k != "order_in_topic"}
        schema = LessonCreate(**data)

        # Мокаем запрос максимального order_in_topic
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = 5
        mock_db_session.execute.return_value = mock_result

        await lesson_service.create_lesson(schema)

        # Проверяем, что был вызван запрос с func.max
        call_args = mock_db_session.execute.call_args[0][0]
        assert "max" in str(call_args).lower()

        # Проверяем, что добавленный урок имеет order_in_topic = 6
        added_lesson = mock_db_session.add.call_args[0][0]
        assert added_lesson.order_in_topic == 6

    @pytest.mark.asyncio
    async def test_create_lesson_uses_explicit_order(self, lesson_service, mock_db_session, valid_lesson_data):
        """Проверка: Если order_in_topic передан явно, он используется без запроса к БД."""
        data = {**valid_lesson_data, "order_in_topic": 99}
        schema = LessonCreate(**data)

        await lesson_service.create_lesson(schema)

        # Не должен был вызывать execute для получения max order
        mock_db_session.execute.assert_not_called()
        added_lesson = mock_db_session.add.call_args[0][0]
        assert added_lesson.order_in_topic == 99

    @pytest.mark.asyncio
    async def test_update_lesson_not_found_raises_404(self, lesson_service, mock_db_session):
        """Проверка: Обновление несуществующего урока вызывает HTTPException 404."""
        mock_db_session.get.return_value = None
        schema = LessonUpdate(
            name="New", description="Desc", difficult=1, rhythm=4, notes={}, topic_id=1
        )
        with pytest.raises(Exception) as exc_info:
            await lesson_service.update_lesson(999, schema)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_lesson_duplicate_name_raises_400(self, lesson_service, mock_db_session, valid_lesson_data):
        """Проверка: Обновление урока на имя, уже занятое другим уроком, вызывает 400."""
        existing_lesson = Mock()
        existing_lesson.id = 1
        existing_lesson.name = "Old Name"
        existing_lesson.topic_id = 1
        existing_lesson.order_in_topic = 1
        existing_lesson.notes = {}

        mock_db_session.get.return_value = existing_lesson

        # Другой урок с таким же именем
        duplicate_lesson = Mock()
        duplicate_lesson.id = 2

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = duplicate_lesson
        mock_db_session.execute.return_value = mock_result

        schema = LessonUpdate(**valid_lesson_data)
        with pytest.raises(Exception) as exc_info:
            await lesson_service.update_lesson(1, schema)
        assert exc_info.value.status_code == 400
        assert "названием уже существует" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_lesson_not_found_raises_404(self, lesson_service, mock_db_session):
        """Проверка: Удаление несуществующего урока вызывает HTTPException 404."""
        mock_db_session.get.return_value = None
        with pytest.raises(Exception) as exc_info:
            await lesson_service.delete_lesson(999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_lesson_success(self, lesson_service, mock_db_session):
        """Проверка: Удаление существующего урока вызывает delete и commit."""
        lesson = Mock()
        lesson.id = 5
        mock_db_session.get.return_value = lesson

        result = await lesson_service.delete_lesson(5)

        mock_db_session.delete.assert_called_once_with(lesson)
        mock_db_session.commit.assert_called()
        assert result["id"] == 5

    @pytest.mark.asyncio
    async def test_get_lessons_with_status(self, lesson_service, mock_db_session):
        """Проверка: Правильное присвоение статусов completed/available/locked."""
        lessons = [
            Mock(id=1, order_in_topic=1),
            Mock(id=2, order_in_topic=2),
            Mock(id=3, order_in_topic=3),
            Mock(id=4, order_in_topic=4),
        ]
        # Пользователь прошел только урок 1
        mock_result_lessons = Mock()
        mock_result_lessons.scalars.return_value.all.return_value = lessons
        mock_result_progress = Mock()
        mock_result_progress.scalars.return_value.all.return_value = [1]

        mock_db_session.execute.side_effect = [mock_result_lessons, mock_result_progress]

        result = await lesson_service.get_lessons_with_status_by_topic(1, user_id=10)

        assert result[0].status == "completed"
        assert result[1].status == "available"  # max_completed=1, so 1+1=2 is available
        assert result[2].status == "locked"
        assert result[3].status == "locked"

    @pytest.mark.asyncio
    async def test_reorder_lessons_mismatched_ids_raises_400(self, lesson_service, mock_db_session):
        """Проверка: Переупорядочивание с неполным списком ID вызывает 400."""
        current_lessons = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = current_lessons
        mock_db_session.execute.return_value = mock_result

        request = LessonReorderRequest(lesson_ids=[1, 2])  # пропущен id=3

        with pytest.raises(Exception) as exc_info:
            await lesson_service.reorder_lessons(1, request)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reorder_lessons_updates_order(self, lesson_service, mock_db_session):
        """Проверка: Переупорядочивание обновляет order_in_topic у уроков."""
        lesson1 = Mock(id=1, order_in_topic=10)
        lesson2 = Mock(id=2, order_in_topic=20)
        lesson3 = Mock(id=3, order_in_topic=30)
        current_lessons = [lesson1, lesson2, lesson3]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = current_lessons
        mock_db_session.execute.return_value = mock_result

        request = LessonReorderRequest(lesson_ids=[3, 1, 2])
        result = await lesson_service.reorder_lessons(1, request)

        assert result is True
        assert lesson1.order_in_topic == 1
        assert lesson2.order_in_topic == 2
        assert lesson3.order_in_topic == 0
        mock_db_session.commit.assert_called_once()


# --- Тесты BaseAPIWorker ---

class TestBaseAPIWorker:
    """Тесты HTTP-воркера без реальных сетевых запросов."""

    @pytest.fixture
    def worker(self, qapp):
        return BaseAPIWorker(base_url="http://test-api.local")

    def test_prepare_request_body_with_dict(self, worker):
        """Проверка: словарь сериализуется в JSON-bytes."""
        body = worker._prepare_request_body({"key": "value"})
        assert json.loads(body) == {"key": "value"}

    def test_prepare_request_body_with_pydantic_model(self, worker, valid_lesson_data):
        """Проверка: Pydantic модель сериализуется через model_dump_json."""
        model = LessonCreate(**valid_lesson_data)
        body = worker._prepare_request_body(model)
        parsed = json.loads(body)
        assert parsed["name"] == valid_lesson_data["name"]

    def test_prepare_request_body_with_none(self, worker):
        """Проверка: None возвращает пустые байты."""
        body = worker._prepare_request_body(None)
        assert body == b""

    def test_prepare_request_body_with_invalid_type(self, worker):
        """Проверка: Неподдерживаемый тип возвращает пустые байты."""
        body = worker._prepare_request_body([1, 2, 3])
        assert body == b""

    def test_execute_http_method_unsupported(self, worker):
        """Проверка: Неподдерживаемый HTTP метод возвращает None."""
        request = Mock()
        result = worker._execute_http_method("TRACE", request, b"")
        assert result is None

    def test_handle_success_response_with_json(self, worker):
        """Проверка: Успешный JSON-ответ парсится и передается в колбэк."""
        callback = Mock()
        reply = Mock()
        reply.readAll.return_value.data.return_value = b'{"status": "ok"}'
        worker._handle_success_response(reply, callback)
        callback.assert_called_once_with({"status": "ok"})

    def test_handle_success_response_with_empty_body(self, worker):
        """Проверка: Пустой ответ (например, DELETE) передает None в колбэк."""
        callback = Mock()
        reply = Mock()
        reply.readAll.return_value.data.return_value = b""
        worker._handle_success_response(reply, callback)
        callback.assert_called_once_with(None)

    def test_handle_success_response_with_invalid_json(self, worker):
        """Проверка: Невалидный JSON не вызывает колбэк и не падает."""
        callback = Mock()
        reply = Mock()
        reply.readAll.return_value.data.return_value = b"not json"
        worker._handle_success_response(reply, callback)
        callback.assert_not_called()

    def test_handle_error_response_timeout(self, worker):
        """Проверка: Таймаут возвращает специфичное сообщение."""
        from PyQt6.QtNetwork import QNetworkReply
        callback = Mock()
        reply = Mock()
        reply.error.return_value = QNetworkReply.NetworkError.TimeoutError
        reply.readAll.return_value.data.return_value = b""
        worker._handle_error_response(reply, callback)
        callback.assert_called_once()
        assert "таймаут" in callback.call_args[0][0].lower() or "время ожидания" in callback.call_args[0][0].lower()

    def test_handle_error_response_with_json_detail(self, worker):
        """Проверка: JSON-ответ с ошибкой извлекает detail."""
        from PyQt6.QtNetwork import QNetworkReply
        callback = Mock()
        reply = Mock()
        reply.error.return_value = QNetworkReply.NetworkError.ContentAccessDenied
        reply.readAll.return_value.data.return_value = b'{"detail": "Forbidden"}'
        worker._handle_error_response(reply, callback)
        callback.assert_called_once_with("Forbidden")

    def test_handle_error_response_with_validation_list(self, worker):
        """Проверка: Список ошибок валидации FastAPI преобразуется в читаемую строку."""
        from PyQt6.QtNetwork import QNetworkReply
        callback = Mock()
        reply = Mock()
        reply.error.return_value = QNetworkReply.NetworkError.ContentOperationNotPermittedError
        reply.readAll.return_value.data.return_value = json.dumps({
            "detail": [
                {"loc": ["body", "name"], "msg": "field required"},
                {"loc": ["body", "difficult"], "msg": "ensure this value is greater than 0"}
            ]
        }).encode()
        worker._handle_error_response(reply, callback)
        error_msg = callback.call_args[0][0]
        assert "name" in error_msg
        assert "difficult" in error_msg

    def test_handle_error_response_with_non_json(self, worker):
        """Проверка: Не-JSON ответ с ошибкой использует errorString."""
        from PyQt6.QtNetwork import QNetworkReply
        callback = Mock()
        reply = Mock()
        reply.error.return_value = QNetworkReply.NetworkError.ConnectionRefusedError
        reply.readAll.return_value.data.return_value = b"raw error"
        reply.errorString.return_value = "Connection refused"
        worker._handle_error_response(reply, callback)
        assert "Connection refused" in callback.call_args[0][0]

    def test_make_request_without_token_no_auth_header(self, worker, qapp):
        """Проверка: Без токена заголовок Authorization не устанавливается."""
        with patch("app.workers.base_worker.settings") as mock_settings:
            mock_settings.value.return_value = None
            mock_manager = Mock()
            mock_reply = Mock()
            mock_manager.get.return_value = mock_reply
            worker.manager = mock_manager
            worker._make_request("GET", "/test", success_callback=Mock())
            request_obj = mock_manager.get.call_args[0][0]
            auth_header = request_obj.rawHeader(b"Authorization")
            assert auth_header == b""
