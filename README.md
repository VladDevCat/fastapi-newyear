Holiday Prep API - это REST API для веб-приложения по подготовке к праздникам.
Проект является продолжением лабораторных работ №1 и №2 и реализован на Python 3.11 с использованием FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT, HttpOnly cookies и Docker Compose.

В проекте реализованы:
- REST API для работы с сущностью HolidayItem
- регистрация и вход пользователей
- аутентификация через JWT
- авторизация и защита приватных эндпоинтов
- хранение Access и Refresh токенов в базе данных в хешированном виде
- механизм отзыва сессий (logout, logout-all)
- эндпоинт whoami для проверки статуса авторизации
- безопасное хранение паролей с хешированием и уникальной солью
- OAuth-вход через Yandex
- контейнеризация через Docker и Docker Compose
- модульная архитектура с разделением на Controller / Service / Repository / Model / DTO

--------------------------------
Используемые технологии
- Python 3.11
- FastAPI
- Uvicorn
- PostgreSQL 18
- SQLAlchemy 2
- Alembic
- PyJWT
- bcrypt
- httpx
- Docker
- Docker Compose
----------------------------------
Пример файла переменных окружения
- DB_USER=student
- DB_PASSWORD=student_secure_password
- DB_NAME=wp_labs
- DB_HOST=db
- DB_PORT=5432

- JWT_ACCESS_SECRET=change_me_access_secret
- JWT_REFRESH_SECRET=change_me_refresh_secret
- JWT_ACCESS_EXPIRATION=15m
- JWT_REFRESH_EXPIRATION=7d

- COOKIE_SECURE=false
- COOKIE_SAMESITE=lax
- COOKIE_DOMAIN=

- APP_BASE_URL=http://localhost:4200
- FRONTEND_REDIRECT_URL=http://localhost:4200/docs

- YANDEX_CLIENT_ID=your_yandex_client_id
- YANDEX_CLIENT_SECRET=your_yandex_client_secret
- YANDEX_CALLBACK_URL=http://localhost:4200/auth/oauth/yandex/callback

- RESET_PASSWORD_EXPIRE_MINUTES=30
- OAUTH_STATE_EXPIRE_MINUTES=10
- AUTH_DEBUG_RETURN_RESET_TOKEN=false
--------------------------------------

Запуск проекта
- docker compose up --build

После запуска:
- API: http://localhost:4200
- Swagger UI: http://localhost:4200/docs

Основные эндпоинты:
Auth
- POST /auth/register — регистрация
- POST /auth/login — вход
- POST /auth/refresh — обновление пары токенов
- GET /auth/whoami — профиль текущего пользователя
- POST /auth/logout — выход из текущей сессии
- POST /auth/logout-all — завершение всех сессий
- GET /auth/oauth/yandex — вход через Yandex
- GET /auth/oauth/yandex/callback — callback Yandex
- POST /auth/forgot-password — запрос сброса пароля
- POST /auth/reset-password — установка нового пароля

Items
- GET /items — список своих активных элементов с пагинацией
- GET /items/{id} — один активный элемент
- POST /items — создать элемент
- PUT /items/{id} — полностью обновить элемент
- PATCH /items/{id} — частично обновить элемент
- DELETE /items/{id} — мягкое удаление элемента
-------------------------------------
Безопасность

В проекте реализовано:
- хеширование паролей,
- уникальная соль для каждого пароля
- JWT Access Token и Refresh Token
- передача токенов только через HttpOnly cookies
- серверное хранение токенов в БД в хешированном виде
- отзыв текущей сессии и всех сессий пользователя
- защита приватных эндпоинтов
- проверка владения ресурсом (items доступны только владельцу)
- защита OAuth через state
- скрытие технических деталей ошибок
--------------------------------------

Полный цикл тестирования:
**Регистрация пользователя**
- Запрос:
- POST /auth/register
Content-Type: application/json
{
  "email": "user1@example.com",
  "password": "Password123"

}
- Ожидаемый ответ:
201 Created
в заголовках Set-Cookie для access_token и refresh_token

**Вход пользователя:**
- POST /auth/login
{
  "email": "user1@example.com",
  "password": "Password123"
}
Ожидаемый ответ:
-200 OK
- cookies обновляются

**Доступ к защищённому ресурсу без токена**
Проверка /auth/whoami без авторизации
Запрос:
- GET /auth/whoami
Ожидаемый ответ:
- 401 Unauthorized

**Проверка /items без авторизации**
Запрос:
GET /items?page=1&limit=10
- Ожидаемый ответ:
- 401 Unauthorized

**Доступ к защищённому ресурсу с токеном**
- После регистрации или входа браузер автоматически сохраняет HttpOnly cookies.
- Проверка /auth/whoami
Запрос:
- GET /auth/whoami
- Ожидаемый ответ:
200 OK

**Истечение Access Token**
Для теста время жизни Access Token временно уменьшалось, например:

- JWT_ACCESS_EXPIRATION=1m
Сценарий
1) Выполнить вход
2) Сразу вызвать GET /auth/whoami
3) Получить 200 OK
4) Подождать истечения токена
5) Снова вызвать GET /auth/whoami

Ожидаемый результат:
- сначала 200 OK
- после истечения срока 401 Unauthorized

**Обновление через Refresh Token**
Запрос:
- POST /auth/refresh

Ожидаемый ответ:
- 200 OK
- cookies обновляются

После этого:
- GET /auth/whoami
снова должен вернуть:
200 OK

**Завершение текущей сессии**
Запрос:
- POST /auth/logout
Ожидаемый ответ:
- 200 OK

После этого проверка:
- GET /auth/whoami
Ожидаемый ответ:
- 401 Unauthorized

**Завершение всех сессий**
Сценарий:
- Выполнить вход одним и тем же пользователем в двух разных сессиях
- Проверить /auth/whoami в обеих — обе должны вернуть 200 OK
В одной из сессий вызвать:
- POST /auth/logout-all
После этого проверить /auth/whoami в обеих сессиях
Ожидаемый результат:
- обе сессии становятся невалидными
- /auth/whoami в обеих возвращает 401 Unauthorized

**Вход через OAuth**
- Для тестирования использовался Yandex OAuth.
Сценарий
Открыть в браузере:
- http://localhost:4200/auth/oauth/yandex
- Выполнить вход через Яндекс

После callback сервер:
- проверяет state
- обменивает code на токен провайдера
- получает профиль пользователя
- ищет или создаёт локального пользователя
- создаёт локальную сессию
- устанавливает HttpOnly cookies

После редиректа проверить:
- GET /auth/whoami
Ожидаемый результат:
- 200 OK
- возвращается профиль пользователя

Пример реального результата:

{
  "user": {
    "id": "cf48ed93-fa37-49f7-b71b-04d8bf477e4f",
    "email": "bajunstudio@yandex.ru",
    "phone": null,
    "created_at": "2026-03-13T17:17:29.897877Z"
  }
}

**Два пользователя с одинаковым паролем → разные хеши**
Были зарегистрированы два пользователя с одинаковым паролем:
- user1@example.com
- user2@example.com
Пароль у обоих:
- Password123

После этого была выполнена проверка в базе данных:
SELECT email, password_hash, password_salt
FROM users
WHERE email IN ('user1@example.com', 'user2@example.com');

Ожидаемый результат:
- password_hash у пользователей различается
- password_salt у пользователей различается

Это доказывает:
- пароль не хранится в открытом виде
- используется хеширование
- используется уникальная соль для каждого пользователя

**Защита CRUD и проверка владения ресурсом**
Создание ресурса пользователем 1

Запрос:

POST /items
Content-Type: application/json

Тело:

{
  "title": "Купить гирлянду",
  "description": "Для ёлки",
  "status": "planned"
}

Ожидаемый ответ:

201 Created

Попытка доступа пользователем 2 к чужому ресурсу

Пользователь 2 пытался выполнить:

GET /items/{id}

Ожидаемый результат:

403 Forbidden

Это подтверждает, что реализована проверка владения ресурсом.

**Итоги тестирования**
 В ходе тестирования подтверждено, что:
- регистрация и вход работают
- защищённые ресурсы недоступны без токена
- защищённые ресурсы доступны с валидной сессией
- истечение Access Token обрабатывается корректно
- Refresh Token позволяет продлить сессию
- текущая сессия успешно завершается через logout
- все сессии пользователя успешно завершаются через logout-all
- OAuth-вход через Yandex работает
- /whoami корректно отражает статус авторизации
- одинаковые пароли разных пользователей дают разные хеши благодаря уникальной соли
- приватные CRUD-операции защищены авторизацией
- пользователь может управлять только своими записями


