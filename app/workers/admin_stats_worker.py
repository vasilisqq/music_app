import json
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.admin_stats import AdminStatsResponse
from loader import settings


class AdminStatsWorker(QObject):
    stats_loaded_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()

    def get_dashboard_stats(self, period_days: int) -> None:
        url = QUrl(f"http://localhost:8000/admin/stats/dashboard?period_days={period_days}")
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_stats_reply(reply))

    def _on_stats_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.stats_loaded_signal.emit(AdminStatsResponse.model_validate(data))
        else:
            self._handle_error(reply, "Ошибка загрузки статистики")
        reply.deleteLater()

    def _handle_error(self, reply: QNetworkReply, default_msg: str) -> None:
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_signal.emit(data.get("detail", default_msg))
        except:
            self.error_signal.emit("Ошибка связи с сервером")
