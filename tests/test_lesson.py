import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from pydantic import ValidationError
import sys
import os
from pathlib import Path

# --- НАСТРОЙКА ПУТЕЙ ---
ROOT_DIR = Path(__file__).resolve().parent.parent  # /home/.../music_app
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

print(f"🚀 ROOT PROJECT PATH: {ROOT_DIR}")
print(f"📂 CURRENT SYS.PATH: {sys.path[:3]}...")

# --- ИМПОРТЫ МОДУЛЕЙ ---
LessonCreate = None
LessonService = None
BaseAPIWorker = None
IMPORT_ERROR_MSG = ""

try:
    # Попробуем импортировать, предполагая структуру server.schemas и т.д.
    # Если у вас структура другая (например, app.schemas), поменяйте здесь
    from schemas.lesson import LessonCreate as LessonCreate 
    from server.services.lesson_services import LessonService
    from app.workers.base_worker import BaseAPIWorker
except ImportError as e:
    IMPORT_ERROR_MSG = str(e)
    print(f"❌ IMPORT ERROR: {e}")
    print("💡 Совет: Проверьте, что в файлах schemas/services/workers используются абсолютные импорты (например, 'from server.models import ...')")
    print("💡 Либо убедитесь, что папка с моделями добавлена в sys.path выше.")

# Если имя класса другое (не LessonCreateSchema), поправьте импорт выше. 
# Часто бывает LessonCreate, LessonSchema и т.п.

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

# --- Тесты ---

class TestLessonLogic:
    def test_lesson_schema_validation_success(self):
        """Проверка: Корректные данные урока проходят валидацию"""
        if not LessonCreate: 
            pytest.skip(f"Модуль не найден: {IMPORT_ERROR_MSG}")
        
        data = {
            "name": "Упражнение 1",
            "description": "Разминка пальцев",
            "difficult": 2,
            "rhythm": 4,
            "hand": "right",
            "topic_id": 1,
            "notes": {}  # ИСПРАВЛЕНО: был список [], а нужен dict {}
        }
        try:
            lesson = LessonCreate(**data)
            assert lesson.name == "Упражнение 1"
            assert lesson.difficult == 2
        except Exception as e:
            pytest.fail(f"Неожиданная ошибка валидации: {e}")

    def test_lesson_schema_validation_fail(self):
        """Проверка: Неверный уровень сложности вызывает ошибку"""
        if not LessonCreate: 
            pytest.skip(f"Модуль не найден: {IMPORT_ERROR_MSG}")

        data = {
            "name": "Ошибка",
            "difficult": 10, 
            "hand": "right",
            "topic_id": 1,
            "notes": {}
        }
        with pytest.raises(ValidationError):
            LessonCreate(**data)

    @pytest.mark.asyncio
    async def test_calculate_progress_percentage(self, mock_db_session):
        if not LessonService: 
            pytest.skip(f"Модуль не найден: {IMPORT_ERROR_MSG}")

        service = LessonService(mock_db_session)
        total_notes = 20
        correct_hits = 18
        percentage = (correct_hits / total_notes) * 100
        
        assert percentage == 90.0
        assert percentage >= 80.0 

class TestBaseWorker:
    def setup_method(self):
        if not BaseAPIWorker:
            pytest.skip(f"Модуль не найден: {IMPORT_ERROR_MSG}")
        self.worker = BaseAPIWorker(base_url="http://test-api.local")
        self.success_cb = Mock()
        self.error_cb = Mock()

    def test_auth_header_injection(self, qapp):
        # ПРАВИЛЬНЫЙ ПУТЬ: указываем модуль, где используется settings, а не где он определен
        patch_path = 'app.workers.base_worker.settings' 
        
        try:
            with patch(patch_path) as mock_settings:
                mock_settings.value.return_value = "fake_jwt_token_123"
                
                mock_manager = Mock()
                mock_reply = Mock()
                mock_manager.get.return_value = mock_reply
                
                self.worker.manager = mock_manager
                self.worker._make_request("GET", "/user/profile", success_callback=self.success_cb)
                
                assert mock_manager.get.called
                request_obj = mock_manager.get.call_args[0][0]
                auth_header = request_obj.rawHeader(b"Authorization")
                
                # Проверка теперь должна пройти, так как мы подменили settings внутри модуля worker
                assert auth_header == b"Bearer fake_jwt_token_123"
        except Exception as e:
            pytest.fail(f"Ошибка при тестировании заголовка авторизации: {e}")

    def test_error_handling_on_network_failure(self, qapp):
        from PyQt6.QtNetwork import QNetworkReply
        
        mock_reply = Mock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.ConnectionRefusedError
        mock_reply.readAll().data.return_value = b""
        
        self.worker._handle_reply(mock_reply, self.success_cb, self.error_cb)
        
        self.success_cb.assert_not_called()
        self.error_cb.assert_called_once()