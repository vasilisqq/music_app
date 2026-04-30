import os
import sys

from PyQt6.QtCore import pyqtSignal

# Импортируем базовый класс
from workers.base_worker import BaseAPIWorker

# Добавляем путь для импорта схем
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.admin_stats import AdminStatsResponse


class AdminStatsWorker(BaseAPIWorker):
    """
    Воркер для получения аналитики и статистики приложения в панель администратора.
    """

    stats_loaded_signal = pyqtSignal(AdminStatsResponse)
    error_signal = pyqtSignal(str)

    def __init__(self):
        # Инициализируем базовый класс (сетевой менеджер и настройки)
        super().__init__()

    def get_dashboard_stats(self, period: str = "all") -> None:
        # Подгоняем периоды под жесткие ограничения бэкенда (7, 30, 90)
        days_map = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 90,  # Сервер не пускает больше 90 дней
            "all": 90,  # Отправляем максимум разрешенного
        }
        # Если придет что-то непонятное, по умолчанию ставим 30
        days = days_map.get(period, 30)

        self._make_request(
            method="GET",
            endpoint=f"/admin/stats/dashboard?period_days={days}",
            success_callback=self._on_stats_received,
            error_callback=self.error_signal.emit,
        )

    def _on_stats_received(self, data: dict) -> None:
        try:
            stats = AdminStatsResponse.model_validate(data)
            self.stats_loaded_signal.emit(stats)
        except Exception as e:
            self.error_signal.emit(f"Ошибка валидации статистики: {str(e)}")

    def get_popularity_report(self) -> None:
        """
        Пример дополнительного метода для детальных отчетов,
        если ты решишь их добавить в диплом.
        """
        self._make_request(
            method="GET",
            endpoint="/admin/stats/popularity",
            success_callback=lambda d: print("Отчет получен:", d),
            error_callback=self.error_signal.emit,
        )
