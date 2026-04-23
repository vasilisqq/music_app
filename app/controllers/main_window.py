from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QScrollArea, QListWidgetItem

from GUI.lesson_list_item import LessonListItemWidget, truncate
from PyQt6.QtCore import Qt, QSize

from loader import settings
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard
from GUI.helpful import FlowLayout

from workers.auth_worker import AuthWorker
from workers.topic_worker import TopicWorker
from workers.lesson_worker import LessonWorker
from workers.progress_worker import ProgressWorker

from controllers.admin import AdminController
from controllers.profile import ProfileController


class Main(QMainWindow):
    def __init__(self, user_data: dict):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.user_data = user_data
        self.auth_worker = AuthWorker()

        self.ui.adminPanelBtn.setVisible(False)
        user_role = self.user_data.get("role", "пользователь")
        if user_role == "администратор":
            self.ui.adminPanelBtn.setVisible(True)

        self.ui.topicsListWidget.hide()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.topics_container = QWidget()
        self.flow_layout = FlowLayout(self.topics_container, spacing=25)
        self.scroll_area.setWidget(self.topics_container)
        self.ui.topicsPageLayout.addWidget(self.scroll_area)

        self.admin_controller = AdminController(self.ui)
        self.profile_controller = ProfileController(self.ui, self.user_data, self.auth_worker)

        self.topic_worker = TopicWorker()
        self.lesson_worker = LessonWorker()
        self.progress_worker = ProgressWorker()

        self._selected_topic_id: int | None = None
        self._topics_subview: str = "topics"  # topics | lessons
        self._lessons_cache = []
        self._completed_lesson_ids: set[int] = set()

        self._setup_signals()
        self._load_topics()
        self.show_home()

    def _setup_signals(self):
        self.ui.homeBtn.clicked.connect(self.show_home)
        self.ui.profileBtn.clicked.connect(self.show_profile)
        self.ui.adminPanelBtn.clicked.connect(self.show_admin_panel)
        self.ui.logoutBtn.clicked.connect(self.logout)

        self.ui.cardPlayBtn.clicked.connect(self.show_topics)
        self.ui.backBtn.clicked.connect(self._on_topics_back_clicked)

        self.topic_worker.topics_loaded_signal.connect(self._on_topics_loaded)
        self.topic_worker.error_signal.connect(self._show_error)

        self.lesson_worker.lessons_by_topic_loaded_signal.connect(self._on_lessons_loaded)
        self.lesson_worker.lesson_error_sygnal.connect(self._show_error)

        self.progress_worker.completed_lessons_loaded_signal.connect(self._on_progress_loaded)
        self.progress_worker.lesson_completed_signal.connect(self._on_lesson_completed)
        self.progress_worker.error_signal.connect(self._show_error)

        self.ui.topicsListWidget.itemClicked.connect(self._on_lesson_clicked)

    def _load_topics(self):
        self._show_topics_view()
        self.topic_worker.get_topics()

    def _show_topics_view(self):
        self._topics_subview = "topics"
        self.ui.topicsHeaderLabel.setText("Темы")
        self.ui.topicsListWidget.hide()
        self.scroll_area.show()

    def _show_lessons_view(self, title: str):
        self._topics_subview = "lessons"
        self.ui.topicsHeaderLabel.setText(title)
        self.scroll_area.hide()
        self.ui.topicsListWidget.show()

    def _on_topics_back_clicked(self):
        if self.ui.stackedWidget.currentWidget() != self.ui.topicsPageWidget:
            self.show_home()
            return

        if self._topics_subview == "lessons":
            self._selected_topic_id = None
            self._show_topics_view()
            return

        self.show_home()

    def _on_topics_loaded(self, topics):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for topic in topics:
            card = LessonCard(title=topic.name, progress=0.0, payload=topic.id)
            card.clicked.connect(self._on_topic_selected)
            self.flow_layout.addWidget(card)

    def _on_topic_selected(self, topic_id: int):
        self._selected_topic_id = int(topic_id)
        self._show_lessons_view("Уроки")
        self.ui.topicsListWidget.clear()
        self.lesson_worker.get_lessons_by_topic(self._selected_topic_id)

    def _on_lessons_loaded(self, lessons):
        self._lessons_cache = sorted(lessons, key=lambda l: (l.order_in_topic or 0, l.id))
        if self._selected_topic_id is None:
            return
        self.progress_worker.get_completed_lessons_for_topic(self._selected_topic_id)

    def _on_progress_loaded(self, completed_ids: list[int]):
        self._completed_lesson_ids = set(int(x) for x in completed_ids)
        self._render_lessons_with_locks()

    def _render_lessons_with_locks(self):
        self.ui.topicsListWidget.clear()
        self.ui.topicsListWidget.setSpacing(8)
        self.ui.topicsListWidget.setUniformItemSizes(False)

        prev_completed = True
        for idx, lesson in enumerate(self._lessons_cache):
            is_completed = lesson.id in self._completed_lesson_ids
            is_unlocked = is_completed or (idx == 0) or prev_completed

            icon = "•"
            if is_completed:
                icon = "✅"
            elif not is_unlocked:
                icon = "🔒"

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, lesson.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, lesson)

            widget = LessonListItemWidget(
                title=lesson.name,
                description=truncate(getattr(lesson, "description", ""), 160),
                icon=icon,
                locked=not is_unlocked,
            )

            item_height = max(96, widget.sizeHint().height(), widget.minimumSizeHint().height())
            item.setSizeHint(QSize(0, item_height))
            widget.setMinimumHeight(item_height)

            if not is_unlocked:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)

            self.ui.topicsListWidget.addItem(item)
            self.ui.topicsListWidget.setItemWidget(item, widget)
            prev_completed = is_completed
            item.setSizeHint(item.sizeHint().expandedTo(widget.sizeHint()))
            

            self.ui.topicsListWidget.addItem(item)
            self.ui.topicsListWidget.setItemWidget(item, widget)
            prev_completed = is_completed

    def _on_lesson_clicked(self, item: QListWidgetItem):
        # Проверка на блокировку урока
        if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            self._show_error("Этот урок пока заблокирован. Пройдите предыдущие упражнения в теме.")
            return

        lesson = item.data(Qt.ItemDataRole.UserRole + 1)
        if lesson is None:
            lesson_id = int(item.data(Qt.ItemDataRole.UserRole))
            lesson = next((l for l in self._lessons_cache if int(l.id) == lesson_id), None)
            if lesson is None:
                return

        from controllers.lesson_player import LessonPlayerController

        # Скрываем боковое меню (как в CreatorController)
        self.ui.drawerWidget.hide()

        self.lesson_player_page = LessonPlayerController(lesson)
        self.lesson_player_page.closed.connect(self._on_lesson_player_closed)

        self.ui.stackedWidget.addWidget(self.lesson_player_page)
        self.ui.stackedWidget.setCurrentWidget(self.lesson_player_page)


    def _on_lesson_player_closed(self, was_completed: bool):
        # Возвращаем боковое меню при закрытии урока
        self.ui.drawerWidget.show()

        if was_completed and self._selected_topic_id is not None:
            self.progress_worker.get_completed_lessons_for_topic(self._selected_topic_id)

        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)
        if hasattr(self, "lesson_player_page"):
            self.ui.stackedWidget.removeWidget(self.lesson_player_page)
            self.lesson_player_page.deleteLater()

    def _on_lesson_completed(self, lesson_id: int):
        self._completed_lesson_ids.add(int(lesson_id))
        self._render_lessons_with_locks()

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "Ошибка", msg)

    def _set_active_tab(self, button, widget):
        self.ui.stackedWidget.setCurrentWidget(widget)
        nav_buttons = [self.ui.homeBtn, self.ui.profileBtn, self.ui.settingsBtn, self.ui.adminPanelBtn]
        for btn in nav_buttons:
            is_active = btn == button
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_home(self):
        self._set_active_tab(self.ui.homeBtn, self.ui.homePageWidget)

    def show_profile(self):
        self._set_active_tab(self.ui.profileBtn, self.ui.profilePageWidget)

    def show_admin_panel(self):
        self._set_active_tab(self.ui.adminPanelBtn, self.ui.adminPageWidget)

    def show_topics(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)
        self._show_topics_view()
        self._load_topics()

    def logout(self):
        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            settings.remove("token")
            from controllers.auth import Auth

            self.auth_window = Auth()
            self.close()
            self.auth_window.show()
