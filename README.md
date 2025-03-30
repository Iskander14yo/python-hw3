# Сервис сокращения URL-адресов

REST API сервис, позволяющий пользователям сокращать длинные ссылки, получать аналитику и управлять ими.

## Основные возможности

- Создание, чтение, обновление и удаление сокращенных ссылок
- Поддержка пользовательских алиасов
- Статистика по ссылкам (количество кликов, дата последнего использования)
- Срок действия ссылок
- Аутентификация пользователей
- Кэширование популярных ссылок с помощью Redis
- Административный интерфейс для управления пользователями и ссылками

## Технологический стек

- FastAPI (Python веб-фреймворк)
- PostgreSQL (база данных)
- Redis (кэширование)
- SQLAlchemy (ORM)
- Docker/Docker Compose (контейнеризация)

## Описание API


![local deploy](assets/image.png)

### Аутентификация

- `POST /token` - Вход в систему для получения токена доступа
- `POST /register` - Регистрация нового пользователя

### Управление ссылками

- `POST /links/shorten` - Создание новой сокращенной ссылки (поддерживает анонимное создание)
- `GET /links/{short_code}` - Перенаправление на оригинальный URL (307 Temporary Redirect)
- `GET /links/{short_code}/stats` - Получение статистики и информации о ссылке
- `PUT /links/{short_code}` - Обновление ссылки (требуется аутентификация)
- `DELETE /links/{short_code}` - Удаление ссылки (требуется аутентификация)
- `GET /links/search` - Поиск ссылок по оригинальному URL

### Административный интерфейс

- `GET /admin/users` - Получение списка всех пользователей
- `DELETE /admin/users/{user_id}` - Удаление пользователя
- `GET /admin/links/recent` - Получение списка недавно созданных ссылок
- `DELETE /admin/links/{short_code}` - Принудительное удаление ссылки

## Примеры запросов

### Регистрация нового пользователя

```bash
curl -X 'POST' \
  'http://localhost:8000/register' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123"
}'
```

### Вход в систему

```bash
curl -X 'POST' \
  'http://localhost:8000/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=testuser&password=password123'
```

### Создание сокращенной ссылки

```bash
curl -X 'POST' \
  'http://localhost:8000/links/shorten' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://www.example.com/very/long/url/that/needs/shortening",
  "custom_alias": "mylink",
  "expires_at": "2024-12-31T23:59:59"
}'
```

### Получение статистики по ссылке

```bash
curl -X 'GET' \
  'http://localhost:8000/links/mylink/stats'
```

### Обновление ссылки

```bash
curl -X 'PUT' \
  'http://localhost:8000/links/mylink' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://www.example.com/updated/url"
}'
```

### Удаление ссылки

```bash
curl -X 'DELETE' \
  'http://localhost:8000/links/mylink' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

### Поиск ссылок

```bash
curl -X 'GET' \
  'http://localhost:8000/links/search?original_url=https://www.example.com/very/long/url/that/needs/shortening'
```

## Инструкция по запуску

### Предварительные требования

- Установленные Docker и Docker Compose

### Шаги для запуска

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd url-shortener
   ```

2. Соберите и запустите контейнеры:
   ```bash
   docker-compose up -d
   ```

3. API будет доступно по адресу http://localhost:8000

4. Документация API доступна по адресу http://localhost:8000/docs

## Структура базы данных

Приложение использует PostgreSQL со следующими основными таблицами:

### Таблица Users (Пользователи)

- `id`: Первичный ключ
- `username`: Уникальное имя пользователя
- `email`: Уникальный email адрес
- `hashed_password`: Безопасно хэшированный пароль
- `is_active`: Статус пользователя
- `created_at`: Дата регистрации

### Таблица Links (Ссылки)

- `id`: Первичный ключ
- `short_code`: Уникальный короткий код для ссылки
- `original_url`: Оригинальный URL
- `custom_alias`: Опциональный пользовательский алиас
- `created_at`: Дата создания
- `last_used_at`: Дата последнего доступа
- `expires_at`: Дата истечения срока действия
- `clicks`: Количество кликов/переходов
- `is_active`: Статус ссылки
- `user_id`: Внешний ключ к таблице Users (может быть null для анонимных пользователей)

## Кэширование

Redis используется для кэширования наиболее часто используемых ссылок. Кэш инвалидируется или обновляется когда:

- Ссылка обновляется
- Ссылка удаляется
- Срок действия ссылки истек

## Разработка

Для запуска приложения в режиме разработки:

```bash
uvicorn app.main:app --reload
```

## Тестирование

### Запуск тестов

Для запуска тестов с проверкой покрытия кода:

```bash
coverage run -m pytest tests
```

### Просмотр отчета о покрытии

После запуска тестов вы можете просмотреть отчет о покрытии кода в формате HTML:

```bash
coverage html
```

Затем откройте файл `htmlcov/index.html` в любом браузере.

### Консольный отчет о покрытии 

Для быстрого просмотра процента покрытия:

```bash
coverage report
```

### Текущее покрытие кода

В результате выполнения тестов достигнуто покрытие кода 65%, что обеспечивает необходимый минимум для тестирования основного функционала. Наиболее полно покрыты тестами:

- Модели данных (100%)
- Схемы данных Pydantic (100%)
- Вспомогательные функции (100%)
- База данных и Redis соединения (100%)

Для увеличения покрытия можно добавить дополнительные тесты для API эндпоинтов и сервисных функций.

### Примечания к тестированию

- Используется `pytest` для модульных и API-тестов
- `httpx` используется для тестирования API-эндпоинтов
- `pytest-mock` применяется для мокирования зависимостей (БД, кэш)
- Тесты находятся в директории `tests/` на одном уровне с директорией `app/`
