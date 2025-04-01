import random
import string
from locust import HttpUser, task, between
from typing import Optional


def generate_random_url():
    """Генерация случайного URL для тестирования."""
    domain = ''.join(random.choices(string.ascii_lowercase, k=10))
    path = ''.join(random.choices(string.ascii_lowercase + string.digits, k=15))
    return f"https://{domain}.com/{path}"


class URLShortenerUser(HttpUser):
    wait_time = between(1, 3)
    access_token: Optional[str] = None

    def on_start(self):
        """Аутентификация пользователя перед началом тестов."""
        # Регистрация нового пользователя
        username = f"loadtest_user_{random.randint(1, 100000)}"
        register_data = {
            "username": username,
            "email": f"{username}@test.com",
            "password": "testpassword123",
            "full_name": "Load Test User"
        }
        self.client.post("/register", json=register_data)

        # Вход для получения токена доступа
        response = self.client.post("/token", 
            data={
                "username": username,
                "password": "testpassword123"
            }
        )
        self.access_token = response.json()["access_token"]
        self.client.headers = {"Authorization": f"Bearer {self.access_token}"}

    @task(1)
    def create_single_link(self):
        """Создание одиночной сокращенной ссылки."""
        data = {
            "original_url": generate_random_url(),
            "is_active": True
        }
        self.client.post("/links/shorten", json=data)

    @task(2)
    def bulk_create_links(self):
        """Создание нескольких ссылок подряд для тестирования массового создания."""
        for _ in range(5):
            data = {
                "original_url": generate_random_url(),
                "is_active": True
            }
            self.client.post("/links/shorten", json=data)

    @task(3)
    def read_and_redirect(self):
        """Тестирование перенаправления ссылок с кэшированием."""
        # Сначала создаем ссылку
        data = {
            "original_url": generate_random_url(),
            "is_active": True
        }
        response = self.client.post("/links/shorten", json=data)
        short_code = response.json()["short_code"]

        # Затем обращаемся к ней несколько раз для тестирования кэширования
        for _ in range(3):
            self.client.get(f"/links/{short_code}", allow_redirects=False)

    @task(1)
    def search_links(self):
        """Тестирование функциональности поиска ссылок."""
        # Сначала создаем ссылку
        original_url = generate_random_url()
        data = {
            "original_url": original_url,
            "is_active": True
        }
        self.client.post("/links/shorten", json=data)

        # Затем ищем её
        self.client.get(f"/links/search?original_url={original_url}") 