import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop
from controllers.auth import Auth
from controllers.main_window import Main
from workers.auth_worker import AuthWorker
from loader import settings

def main() -> None:
    app = QApplication(sys.argv)
    
    token = settings.value("token")
    window = None

    if token:
        worker = AuthWorker()
        loop = QEventLoop()
        
        # 1. ОБЯЗАТЕЛЬНО инициализируем переменные ДО вложенных функций
        is_token_valid = False
        window_data = {} 
        
        def on_token_valid(user_data):
            nonlocal is_token_valid, window_data # Теперь Python найдет их выше
            is_token_valid = True
            window_data = user_data
            loop.quit()

        def on_token_invalid():
            nonlocal is_token_valid
            is_token_valid = False
            loop.quit()

        def on_error(string):
            print(string)

        worker.token_valid_signal.connect(on_token_valid)
        worker.token_invalid_signal.connect(on_token_invalid)
        worker.error_occurred_signal.connect(on_error)

        worker.verify_token(token)
        loop.exec()
        
        if is_token_valid:
            window = Main(window_data) 
        else:
            settings.remove("token")
            window = Auth()
    else:
        window = Auth()
        
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()