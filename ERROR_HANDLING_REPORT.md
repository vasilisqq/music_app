ОБРАБОТКА ОШИБОК И ТАЙМАУТЫ В WORKERS
=====================================

Все файлы workers (/app/workers/) были обновлены с добавлением:

1. ТАЙМАУТЫ (10 сек) для каждого сетевого запроса
   - Константа: REQUEST_TIMEOUT_MS = 10000 (миллисекунды)
   - Метод: request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)
   - QTimer срабатывает при превышении времени

2. МЕТОДЫ УПРАВЛЕНИЯ ТАЙМАУТАМИ
   - _setup_timeout(reply, timeout_msg) - установить таймаут для запроса
   - _cleanup_timeout(reply) - очистить таймаут после завершения
   - self.timeout_timers = {} - словарь для отслеживания таймаутов

3. ПОПАНАЯ ОБРАБОТКА ОШИБОК (try-except-finally)
   - Обработка JSON парсинга (JSONDecodeError)
   - Обработка валидации моделей (ValueError)
   - Обработка сетевых ошибок (NetworkError)
   - Логирование ошибок в консоль (print)
   - Гарантированная очистка ресурсов (finally: reply.deleteLater())

ОБНОВЛЁННЫЕ ФАЙЛЫ
=================

✅ app/workers/auth_worker.py
   - create_user() - регистрация пользователя
   - login_user() - вход пользователя
   - verify_token() - проверка токена
   - update_profile() - обновление профиля
   - get_all_users() - получение всех пользователей (админ)
   - toggle_user_status() - изменение статуса пользователя (админ)
   - edit_user() - редактирование пользователя (админ)
   + Обработчики ответов: _user_reply, _verify_reply, _update_reply, etc.
   + Методы таймаутов: _setup_timeout, _cleanup_timeout

✅ app/workers/topic_worker.py
   - get_topics() - получение всех тем
   - create_topic() - создание темы
   - edit_topic() - редактирование темы
   - delete_topic() - удаление темы
   + Обработчики ответов: _on_get_reply, _on_create_reply, _on_update_reply, _on_delete_reply
   + Улучшена _handle_error() с JSON парсингом
   + Методы таймаутов: _setup_timeout, _cleanup_timeout

✅ app/workers/lesson_worker.py
   - create_lesson() - создание урока
   - get_lesson_by_id() - получение урока по ID
   - update_lesson() - обновление урока
   - delete_lesson() - удаление урока
   - get_lessons_by_topic() - получение уроков по теме
   + Обработчики ответов со смежной обработкой ошибок
   + _build_json_request() теперь устанавливает таймаут
   + Методы таймаутов: _setup_timeout, _cleanup_timeout

✅ app/workers/progress_worker.py
   - get_completed_lessons_for_topic() - получение выполненных уроков
   - complete_lesson() - отметить урок выполненным
   - get_profile_stats() - получение статистики профиля
   + Обработчики ответов с полной обработкой ошибок
   + Методы таймаутов: _setup_timeout, _cleanup_timeout

✅ app/workers/admin_stats_worker.py
   - get_dashboard_stats() - получение статистики админ-панели
   + Обработчик ответов с полной обработкой ошибок
   + Методы таймаутов: _setup_timeout, _cleanup_timeout


ТИПИЧНЫЙ ПОТОК ОБРАБОТКИ ОШИБОК
================================

Пример для метода create_user():

1. TRY блок подготовки запроса:
   - Формирование URL
   - Создание QNetworkRequest
   - Установка таймаута: request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)
   - Отправка запроса через self.manager.post()
   - Установка обработчика и таймаута: _setup_timeout(reply, msg)

2. EXCEPT блок при ошибке подготовки:
   - Отправка сигнала ошибки через error_occurred_signal.emit()

3. Обработчик ответа _user_reply():
   - TRY блок:
     а) Проверка reply.error() == NetworkError.NoError
     б) При успехе: JSON парсинг с except json.JSONDecodeError
     в) При ошибке: обработка через _handle_error()
   - EXCEPT блок при критической ошибке: логирование + сигнал ошибки
   - FINALLY блок: reply.deleteLater() + _cleanup_timeout(reply)


ПРЕИМУЩЕСТВА
============

✅ Таймауты предотвращают зависание приложения при неответе сервера
✅ Полная обработка JSON ошибок (вместо bare except)
✅ Гарантированная очистка ресурсов (finally + deleteLater)
✅ Информативные сообщения об ошибках для пользователя
✅ Логирование ошибок в консоль для отладки
✅ Единообразный паттерн обработки во всех workers


АВТОМАТИЧЕСКОЕ СРАБАТЫВАНИЕ ТАЙМАУТА
=====================================

Если сервер не ответит в течение 10 секунд:
1. QTimer сработает (on_timeout callback)
2. reply.abort() остановит запрос
3. Будет отправлен сигнал об ошибке: "Ошибка: превышено время ожидания сервера"
4. reply.isFinished() вернёт True
5. _cleanup_timeout() очистит таймер из словаря

Если сервер ответит в срок:
1. reply.finished сигнал сработает первым
2. Обработчик вызовет _cleanup_timeout()
3. Таймер будет остановлен и удалён из словаря


ПРИМЕРЫ СООБЩЕНИЙ ОБ ОШИБКАХ
=============================

Таймауты:
- "Ошибка регистрации: превышено время ожидания сервера"
- "Ошибка входа: превышено время ожидания сервера"
- "Ошибка загрузки тем: превышено время ожидания сервера"

JSON парсинг:
- "Ошибка парсинга ответа сервера: ..."
- "Ошибка парсинга тем: ..."
- "Ошибка парсинга статистики: ..."

Сетевые ошибки:
- Деталь от FastAPI сервера (из JSON: {"detail": "..."})
- Или fallback сообщение: "Ошибка связи с сервером"

Критические ошибки:
- "Критическая ошибка обработки ответа: ..."
- "Критическая ошибка при создании урока: ..."
