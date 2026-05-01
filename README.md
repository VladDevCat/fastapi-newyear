# Лабораторные работы 6-7: MongoDB, Redis, MinIO

## Lab 6. MongoDB и Redis

### Что реализовано

В рамках Lab 6 приложение переведено с PostgreSQL на MongoDB, а Redis используется для кеширования и инвалидации access-сессий по JTI.

Основные изменения:

- PostgreSQL заменен на MongoDB.
- SQLAlchemy/Alembic больше не используются для запуска приложения.
- Репозитории работают с MongoDB через PyMongo.
- Soft delete реализован через поле `deleted_at`.
- Redis используется для кеширования:
  - списков items;
  - публичного профиля пользователя;
  - metadata файлов в Lab 7.
- Access token JTI хранится в Redis с TTL access token.
- При logout JTI удаляется из Redis, поэтому старый access token сразу становится недействительным.

### Основные файлы

| Файл | Назначение |
|---|---|
| `app/common/db.py` | Подключение к MongoDB, `MongoUnitOfWork`, создание индексов |
| `app/common/mongo_helpers.py` | Конвертация dataclass-моделей в MongoDB-документы и обратно |
| `app/common/cache.py` | Единый Redis-сервис: `get`, `set`, `del_key`, `delByPattern` |
| `app/modules/items/repository.py` | MongoDB-репозиторий для items |
| `app/modules/items/service.py` | Кеширование списков items и инвалидация при записи |
| `app/modules/users/repository.py` | MongoDB-репозиторий пользователей |
| `app/modules/users/service.py` | Кеширование публичного профиля |
| `app/modules/auth/service.py` | Запись/удаление access JTI в Redis |
| `app/modules/auth/dependencies.py` | Проверка JWT и JTI в Redis |
| `docker-compose.yml` | Сервисы `mongo`, `redis`, `app` |

### Пример `.env` для Lab 6

```env
MONGO_INITDB_ROOT_USERNAME=student
MONGO_INITDB_ROOT_PASSWORD=student_secure_password
MONGO_DB_NAME=wp_labs
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_AUTH_SOURCE=admin
MONGO_URI=mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password
REDIS_DB=0
REDIS_KEY_PREFIX=wp
ITEMS_CACHE_TTL_SECONDS=120
USER_PROFILE_CACHE_TTL_SECONDS=300

JWT_ACCESS_SECRET=change_me_access_secret
JWT_REFRESH_SECRET=change_me_refresh_secret
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d

COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=

APP_BASE_URL=http://localhost:4200
FRONTEND_REDIRECT_URL=http://localhost:4200/docs

APP_ENV=development
SWAGGER_ENABLED=true
```

## Lab 6. Сценарии тестирования

### 1. Запуск окружения

```powershell
docker compose up --build -d
docker compose ps
```

Ожидаемо:

- `holiday_prep_app` запущен;
- `wp_labs_mongo` healthy;
- `wp_labs_redis` healthy.

Проверка базового endpoint:

```powershell
curl.exe -i http://localhost:4200/info
```

Ожидаемо:

```text
HTTP/1.1 200 OK
```

### 2. Регистрация пользователя

```powershell
$cookie = "$env:TEMP\lab6-cookies.txt"
$registerJson = "$env:TEMP\lab6-register.json"
$email = "lab6.$([guid]::NewGuid().ToString('N'))@example.com"

@{
  email = $email
  password = "Winter2026"
} | ConvertTo-Json -Compress | Set-Content -NoNewline $registerJson

curl.exe -i -c $cookie `
  -H "Content-Type: application/json" `
  --data-binary "@$registerJson" `
  http://localhost:4200/auth/register
```

Ожидаемо:

```text
HTTP/1.1 201 Created
set-cookie: access_token=...
set-cookie: refresh_token=...
```

Проверка текущего пользователя:

```powershell
curl.exe -i -b $cookie http://localhost:4200/auth/whoami
```

Ожидаемо:

```text
HTTP/1.1 200 OK
```

### 3. Проверка access JTI в Redis

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:auth:user:*:access:*"
```

Ожидаемо: ключ вида:

```text
wp:auth:user:{userId}:access:{jti}
```

Проверка TTL:

```powershell
$jtiKey = docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:auth:user:*:access:*" | Select-Object -First 1
docker exec wp_labs_redis redis-cli -a redis_secure_password TTL $jtiKey
```

Ожидаемо: положительное число до `900`, если access token живет 15 минут.

### 4. Создание items

```powershell
$itemJson = "$env:TEMP\lab6-item.json"

@{
  title = "Lights $([guid]::NewGuid().ToString('N').Substring(0,8))"
  description = "Warm white lights"
  status = "planned"
} | ConvertTo-Json -Compress | Set-Content -NoNewline $itemJson

curl.exe -i -b $cookie `
  -H "Content-Type: application/json" `
  --data-binary "@$itemJson" `
  http://localhost:4200/items
```

Ожидаемо:

```text
HTTP/1.1 201 Created
```

### 5. Кеширование GET /items

```powershell
curl.exe -i -b $cookie "http://localhost:4200/items?page=1&limit=10"
```

Проверить Redis:

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:items:*"
```

Ожидаемо:

```text
wp:items:list:user:{userId}:page:1:limit:10
```

### 6. Инвалидация кеша items после POST

Создать еще один item:

```powershell
@{
  title = "Garland $([guid]::NewGuid().ToString('N').Substring(0,8))"
  description = "Fresh garland"
  status = "planned"
} | ConvertTo-Json -Compress | Set-Content -NoNewline $itemJson

curl.exe -i -b $cookie `
  -H "Content-Type: application/json" `
  --data-binary "@$itemJson" `
  http://localhost:4200/items
```

Проверить ключи:

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:items:*"
```

Ожидаемо: кеш списка очищен.

### 7. Проверка данных в MongoDB

```powershell
docker exec wp_labs_mongo mongosh --quiet `
  --username student `
  --password student_secure_password `
  --authenticationDatabase admin `
  wp_labs `
  --eval "db.users.find({}, {password_hash:0,password_salt:0}).forEach(printjson); db.holiday_items.find().forEach(printjson)"
```

Ожидаемо:

- пользователи лежат в коллекции `users`;
- items лежат в коллекции `holiday_items`;
- документы имеют `_id`;
- активные документы имеют `deleted_at: null`.

### 8. Logout и мгновенная инвалидация access token

```powershell
curl.exe -i -b $cookie -X POST http://localhost:4200/auth/logout
```

Ожидаемо:

```text
HTTP/1.1 200 OK
```

Проверить Redis:

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:auth:user:*:access:*"
```

Ожидаемо: JTI текущей сессии удален.

Повторный запрос со старым cookie:

```powershell
curl.exe -i -b $cookie http://localhost:4200/auth/whoami
```

Ожидаемо:

```text
HTTP/1.1 401 Unauthorized
```

## Lab 7. MinIO и объектное хранилище

### Что реализовано

В рамках Lab 7 добавлено объектное хранилище MinIO для хранения файлов.

Основные изменения:

- Добавлен сервис MinIO в Docker.
- Файлы загружаются в MinIO.
- Файлы не хранятся в базе данных как BLOB.
- Файлы не сохраняются в файловую систему приложения.
- В MongoDB хранится только metadata файла.
- Загрузка и скачивание работают через streams.
- Добавлены endpoints:
  - `POST /files`;
  - `GET /files/{fileId}`;
  - `DELETE /files/{fileId}`;
  - `GET /profile`;
  - `POST /profile`.
- Профиль пользователя поддерживает `display_name`, `bio`, `avatar_file_id`.
- Пользователь может скачивать и удалять только свои файлы.
- Metadata файлов кешируется в Redis.
- Bucket создается вручную, не автоматически.

### Основные файлы

| Файл | Назначение |
|---|---|
| `app/modules/storage/model.py` | Модель metadata файла `FileRecord` |
| `app/modules/storage/repository.py` | MongoDB-репозиторий файлов |
| `app/modules/storage/service.py` | Работа с MinIO, валидация, streams, кеш metadata |
| `app/modules/storage/router.py` | Endpoints `/files` |
| `app/modules/storage/profile_router.py` | Endpoints `/profile` |
| `app/modules/storage/schemas.py` | DTO файлов и профиля |
| `app/modules/users/model.py` | Поля профиля и `avatar_file_id` |
| `app/modules/users/service.py` | Обновление профиля и кеша |
| `app/common/config.py` | Настройки MinIO, MIME-типов и размера |
| `docker-compose.yml` | Сервис MinIO |

### Где реализованы критерии приемки

| Критерий | Где реализовано |
|---|---|
| Загрузка через потоки, не буфер | `app/modules/storage/service.py`, метод `uploadFile`, `client.put_object(..., data=stream, length=size)` |
| Метаданные сохраняются в БД | `app/modules/storage/repository.py`, метод `create`, коллекция `files` |
| Скачивание с правильными заголовками | `app/modules/storage/router.py`, `StreamingResponse`, `Content-Disposition`, `Content-Length`, `media_type` |
| Soft delete и удаление из MinIO | `app/modules/storage/service.py`, `delete_owned_file`; `repository.py`, `soft_delete`; `deleteFile` |
| Профиль с аватаром | `app/modules/storage/profile_router.py`, `app/modules/storage/service.py`, `ProfileService` |
| Проверка владения | `app/modules/storage/service.py`, метод `get_owned_file` |
| MIME и size validation | `app/modules/storage/service.py`, метод `_validate_upload` |
| Файл не хранится в БД/FS приложения | В MongoDB пишется только metadata, файл уходит в MinIO через `put_object` |

### Пример `.env` для Lab 7

```env
MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin_secure_password
MINIO_BUCKET=wp-files
MINIO_SECURE=false
MAX_UPLOAD_SIZE_BYTES=10485760
AVATAR_ALLOWED_MIME_TYPES=image/png,image/jpeg,image/jpg
FILE_META_CACHE_TTL_SECONDS=300
```

Полный `.env` для Lab 6 + Lab 7:

```env
MONGO_INITDB_ROOT_USERNAME=student
MONGO_INITDB_ROOT_PASSWORD=student_secure_password
MONGO_DB_NAME=wp_labs
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_AUTH_SOURCE=admin
MONGO_URI=mongodb://student:student_secure_password@mongo:27017/wp_labs?authSource=admin

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_secure_password
REDIS_DB=0
REDIS_KEY_PREFIX=wp
ITEMS_CACHE_TTL_SECONDS=120
USER_PROFILE_CACHE_TTL_SECONDS=300
FILE_META_CACHE_TTL_SECONDS=300

MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin_secure_password
MINIO_BUCKET=wp-files
MINIO_SECURE=false
MAX_UPLOAD_SIZE_BYTES=10485760
AVATAR_ALLOWED_MIME_TYPES=image/png,image/jpeg,image/jpg

JWT_ACCESS_SECRET=change_me_access_secret
JWT_REFRESH_SECRET=change_me_refresh_secret
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d

COOKIE_SECURE=false
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=

APP_BASE_URL=http://localhost:4200
FRONTEND_REDIRECT_URL=http://localhost:4200/docs

APP_ENV=development
SWAGGER_ENABLED=true
```

## Lab 7. Сценарии тестирования

### 1. Запустить окружение

```powershell
docker compose up --build -d
docker compose ps
```

Ожидаемо:

- `wp_labs_minio` запущен и healthy;
- `holiday_prep_app` запущен;
- `wp_labs_mongo` и `wp_labs_redis` работают.

### 2. Создать bucket вручную

Через MinIO Console:

```text
http://localhost:9001
```

Логин:

```text
minioadmin
```

Пароль:

```text
minioadmin_secure_password
```

Создать bucket:

```text
wp-files
```

Или через CLI:

```powershell
docker exec wp_labs_minio mc alias set local http://localhost:9000 minioadmin minioadmin_secure_password
docker exec wp_labs_minio mc mb local/wp-files
```

Проверить:

```powershell
docker exec wp_labs_minio mc ls local
```

### 3. Создать тестовый PNG

```powershell
$png = "$env:TEMP\avatar-test.png"

[byte[]]$bytes = `
0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,
0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,
0x08,0x06,0x00,0x00,0x00,0x1F,0x15,0xC4,
0x89,0x00,0x00,0x00,0x0A,0x49,0x44,0x41,
0x54,0x78,0x9C,0x63,0x00,0x01,0x00,0x00,
0x05,0x00,0x01,0x0D,0x0A,0x2D,0xB4,0x00,
0x00,0x00,0x00,0x49,0x45,0x4E,0x44,0xAE,
0x42,0x60,0x82

[IO.File]::WriteAllBytes($png, $bytes)
Get-Item $png
```

### 4. Зарегистрировать пользователя

```powershell
$cookie = "$env:TEMP\lab7-cookies.txt"
$registerJson = "$env:TEMP\lab7-register.json"
$email = "lab7.$([guid]::NewGuid().ToString('N'))@example.com"

@{
  email = $email
  password = "Winter2026"
} | ConvertTo-Json -Compress | Set-Content -NoNewline $registerJson

curl.exe -i -c $cookie `
  -H "Content-Type: application/json" `
  --data-binary "@$registerJson" `
  http://localhost:4200/auth/register
```

Ожидаемо:

```text
HTTP/1.1 201 Created
```

### 5. Проверить профиль до загрузки аватара

```powershell
curl.exe -i -b $cookie http://localhost:4200/profile
```

Ожидаемо:

```json
"avatar_file_id": null,
"avatar": null
```

### 6. Загрузить файл

```powershell
$uploadResponse = curl.exe -s -i -b $cookie `
  -F "file=@$png;type=image/png;filename=avatar-test.png" `
  http://localhost:4200/files

$uploadResponse
```

Ожидаемо:

```text
HTTP/1.1 201 Created
```

Получить `fileId`:

```powershell
$fileId = (($uploadResponse -split "`r?`n`r?`n")[-1] | ConvertFrom-Json).id
$fileId
```

### 7. Проверить metadata в MongoDB

```powershell
docker exec wp_labs_mongo mongosh --quiet `
  --username student `
  --password student_secure_password `
  --authenticationDatabase admin `
  wp_labs `
  --eval "printjson(db.files.findOne({_id:'$fileId'}))"
```

Ожидаемо:

- есть `original_name`;
- есть `object_key`;
- есть `size`;
- есть `mimetype`;
- есть `bucket`;
- есть `user_id`;
- `deleted_at: null`;
- нет содержимого файла как BLOB.

### 8. Проверить объект в MinIO

```powershell
docker exec wp_labs_minio mc find local/wp-files
```

Ожидаемо:

```text
local/wp-files/users/{userId}/files/{fileId}.png
```

### 9. Проверить Redis metadata cache

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:files:*:meta"
```

Ожидаемо:

```text
wp:files:{fileId}:meta
```

Проверить TTL:

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password TTL "wp:files:$fileId:meta"
```

Ожидаемо: число до `300`.

### 10. Скачать файл

```powershell
$downloadPath = "$env:TEMP\downloaded-avatar-test.png"
$headersPath = "$env:TEMP\download-headers.txt"

curl.exe -s -D $headersPath `
  -b $cookie `
  -o $downloadPath `
  "http://localhost:4200/files/$fileId"

Get-Content $headersPath
Get-Item $downloadPath
```

Ожидаемые заголовки:

```text
HTTP/1.1 200 OK
content-disposition: attachment; filename*=UTF-8''avatar-test.png
content-length: 67
content-type: image/png
```

### 11. Обновить профиль с аватаром

```powershell
$profileJson = "$env:TEMP\profile-update.json"

@{
  display_name = "MinIO Tester"
  bio = "Avatar uploaded through MinIO"
  avatar_file_id = $fileId
} | ConvertTo-Json -Compress | Set-Content -NoNewline $profileJson

curl.exe -i -b $cookie `
  -H "Content-Type: application/json" `
  --data-binary "@$profileJson" `
  http://localhost:4200/profile
```

Ожидаемо:

```text
HTTP/1.1 200 OK
```

В ответе:

```json
"avatar_file_id": "{fileId}",
"avatar": {
  "id": "{fileId}",
  "original_name": "avatar-test.png",
  "size": 67,
  "mimetype": "image/png"
}
```

### 12. Проверить защиту доступа другим пользователем

```powershell
$cookie2 = "$env:TEMP\lab7-cookies-2.txt"
$registerJson2 = "$env:TEMP\lab7-register-2.json"
$email2 = "lab7.other.$([guid]::NewGuid().ToString('N'))@example.com"

@{
  email = $email2
  password = "Winter2026"
} | ConvertTo-Json -Compress | Set-Content -NoNewline $registerJson2

curl.exe -i -c $cookie2 `
  -H "Content-Type: application/json" `
  --data-binary "@$registerJson2" `
  http://localhost:4200/auth/register
```

Попробовать скачать файл первого пользователя:

```powershell
curl.exe -i -b $cookie2 "http://localhost:4200/files/$fileId"
```

Ожидаемо:

```text
HTTP/1.1 403 Forbidden
```

Попробовать поставить чужой файл как аватар:

```powershell
$badProfileJson = "$env:TEMP\bad-profile-update.json"

@{
  avatar_file_id = $fileId
} | ConvertTo-Json -Compress | Set-Content -NoNewline $badProfileJson

curl.exe -i -b $cookie2 `
  -H "Content-Type: application/json" `
  --data-binary "@$badProfileJson" `
  http://localhost:4200/profile
```

Ожидаемо:

```text
HTTP/1.1 403 Forbidden
```

### 13. Проверить MIME validation

```powershell
$txt = "$env:TEMP\not-image.txt"
"hello" | Set-Content $txt

curl.exe -i -b $cookie `
  -F "file=@$txt;type=text/plain;filename=not-image.txt" `
  http://localhost:4200/files
```

Ожидаемо:

```text
HTTP/1.1 400 Bad Request
```

Тело:

```json
{"detail":"Unsupported file type"}
```

### 14. Удалить файл

```powershell
curl.exe -i -b $cookie -X DELETE "http://localhost:4200/files/$fileId"
```

Ожидаемо:

```text
HTTP/1.1 204 No Content
```

### 15. Проверить soft delete в MongoDB

```powershell
docker exec wp_labs_mongo mongosh --quiet `
  --username student `
  --password student_secure_password `
  --authenticationDatabase admin `
  wp_labs `
  --eval "printjson(db.files.findOne({_id:'$fileId'}))"
```

Ожидаемо:

```json
"deleted_at": ISODate(...)
```

### 16. Проверить удаление из MinIO

```powershell
docker exec wp_labs_minio mc find local/wp-files
```

Ожидаемо: объекта с этим `fileId` больше нет.

### 17. Проверить удаление Redis cache

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:files:$fileId:meta"
```

Ожидаемо: пустой вывод.

### 18. Проверить, что скачать удаленный файл нельзя

```powershell
curl.exe -i -b $cookie "http://localhost:4200/files/$fileId"
```

Ожидаемо:

```text
HTTP/1.1 404 Not Found
```

### 19. Проверить, что аватар в профиле очистился

```powershell
curl.exe -s -b $cookie http://localhost:4200/profile
```

Ожидаемо:

```json
"avatar_file_id": null,
"avatar": null
```

# Лабораторная работа №8: RabbitMQ

## Краткое описание

В этой лабораторной работе в приложение добавлена асинхронная обработка события регистрации пользователя через RabbitMQ.

После успешного `POST /auth/register` приложение публикует событие `user.registered` в exchange `app.events`. Фоновый consumer, запущенный в том же контейнере приложения, читает очередь `wp.auth.user.registered`, отправляет приветственное письмо через SMTP и подтверждает сообщение через `ack`.

Если SMTP временно недоступен, consumer делает повторные попытки. После 3 неудачных попыток сообщение отправляется в Dead Letter Queue: `wp.auth.user.registered.dlq`.

Для защиты от повторной обработки одного и того же события используется идемпотентность через Redis: `wp:events:processed:{eventId}`.

## Что добавлено

- RabbitMQ с Management UI.
- Mailpit как локальный SMTP-сервер для тестирования писем.
- Модуль `app/common/queue/` для работы с RabbitMQ.
- Модуль `app/modules/notifications/` для событий, consumer и email-сервиса.
- Публикация события регистрации пользователя.
- Асинхронная отправка welcome email.
- `ack`/`nack`, retry, DLQ.
- Идемпотентность обработки событий через Redis.
- Проверка SMTP-конфигурации при старте приложения.

## Полезные адреса

| Сервис | URL | Доступ |
|---|---|---|
| Swagger | `http://localhost:4200/api/docs` | без логина |
| RabbitMQ Management UI | `http://localhost:15672` | `student` / `student_secure_rabbit_pass_change_in_prod` |
| Mailpit UI | `http://localhost:8025` | без логина |
| API | `http://localhost:4200` | зависит от endpoint |

## Основные файлы

| Файл | Назначение |
|---|---|
| `docker-compose.yml` | Добавляет сервисы `rabbitmq` и `mailpit`, порты, healthcheck и volume. |
| `.env` | Настройки RabbitMQ и SMTP. |
| `requirements.txt` | Зависимость `pika` для RabbitMQ. |
| `app/common/config.py` | Конфигурация RabbitMQ/SMTP и валидация SMTP. |
| `app/common/queue/rabbitmq.py` | Подключение, exchange, queue, DLQ, publish, consume, ack/nack. |
| `app/modules/auth/service.py` | Вызов публикации события после регистрации. |
| `app/modules/notifications/events.py` | Формирование и публикация события `user.registered`. |
| `app/modules/notifications/consumer.py` | Фоновый consumer, retry, DLQ, Redis idempotency. |
| `app/modules/notifications/email_service.py` | Отправка plain text + HTML welcome email через SMTP. |
| `app/main.py` | Startup/shutdown: проверка конфигурации, RabbitMQ setup, старт consumer. |

## Переменные окружения

Пример блока `.env` для Lab 8:

```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=student
RABBITMQ_PASS=student_secure_rabbit_pass_change_in_prod
RABBITMQ_EXCHANGE=app.events
RABBITMQ_DLX=app.dlx
QUEUE_USER_REGISTERED=wp.auth.user.registered
QUEUE_USER_REGISTERED_DLQ=wp.auth.user.registered.dlq
RABBITMQ_MAX_RETRIES=3
RABBITMQ_CONSUMER_MAX_FAILURES=5

SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
SMTP_FROM=no-reply@wp-labs.local
SMTP_SECURE=false
SMTP_LOGIN_URL=http://localhost:4200/api/docs
```

## Запуск

```powershell
docker compose up --build -d
docker compose ps
```

Проверить логи приложения:

```powershell
docker compose logs --tail=100 app
```

Ожидаемые признаки успешного старта:

```text
RabbitMQ user registration consumer bootstrap started
RabbitMQ consumer started for queue=wp.auth.user.registered
Application startup complete
```

## Тестирование через Swagger

### 1. Открыть Swagger

Откройте:

```text
http://localhost:4200/api/docs
```

### 2. Выполнить регистрацию пользователя

В Swagger найдите endpoint:

```text
POST /auth/register
```

Нажмите **Try it out** и отправьте новый email:

```json
{
  "email": "lab8.swagger@example.com",
  "password": "Winter2026"
}
```

Важно: email должен быть новым. Если пользователь уже существует, регистрация вернёт ошибку.

Ожидаемый результат:

- HTTP статус `201 Created`;
- в ответе есть объект `user`;
- в браузер установлены cookies `access_token` и `refresh_token`;
- в логах приложения появятся сообщения о публикации события и отправке письма.

### 3. Проверить логи после Swagger-регистрации

```powershell
docker compose logs --tail=120 app
```

Ожидаемые строки:

```text
Published RabbitMQ event type=user.registered routing_key=user.registered
User registered event published event_id=...
Received RabbitMQ event event_id=... type=user.registered attempt=1
Sending welcome email event_id=... attempt=1
Welcome email sent for event_id=...
```

### 4. Проверить письмо в Mailpit

Откройте:

```text
http://localhost:8025
```

Ожидается письмо:

```text
Subject: Welcome to Holiday Prep
From: no-reply@wp-labs.local
To: lab8.swagger@example.com
```

Письмо содержит:

- обращение по имени или email prefix;
- подтверждение регистрации;
- account id;
- ссылку на вход в систему.

### 5. Проверить очередь в RabbitMQ UI

Откройте:

```text
http://localhost:15672
```

Логин:

```text
student
```

Пароль:

```text
student_secure_rabbit_pass_change_in_prod
```

Перейдите в **Queues and Streams**.

Проверьте:

- очередь `wp.auth.user.registered`;
- очередь `wp.auth.user.registered.dlq`.

После успешной обработки письма у основной очереди должно быть:

```text
Ready: 0
Unacked: 0
```

В деталях очереди также можно увидеть:

- `Consumers: 1`;
- рост счётчиков `Publish`, `Deliver`, `Ack`.

## Тестирование через команды

### 1. Регистрация через curl

```powershell
$email = "lab8.$([guid]::NewGuid().ToString('N'))@example.com"
$bodyPath = Join-Path $env:TEMP "lab8-register.json"
@{
  email = $email
  password = "Winter2026"
} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -NoNewline $bodyPath

Write-Output "EMAIL=$email"
curl.exe -i `
  -H "Content-Type: application/json" `
  --data-binary "@$bodyPath" `
  http://localhost:4200/auth/register
```

Ожидается:

```text
HTTP/1.1 201 Created
```

### 2. Проверка очередей RabbitMQ

```powershell
docker exec wp_labs_rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

После успешной обработки:

```text
wp.auth.user.registered      0      0
wp.auth.user.registered.dlq  0      0
```

Если в DLQ уже лежит тестовое сообщение после проверки отказоустойчивости, это нормально:

```text
wp.auth.user.registered.dlq  1      0
```

### 3. Проверка Mailpit через API

```powershell
curl.exe -s http://localhost:8025/api/v1/messages
```

Быстрый поиск по теме письма:

```powershell
curl.exe -s http://localhost:8025/api/v1/messages | Select-String -Pattern "Welcome to Holiday Prep"
```

### 4. Проверка Redis-ключей идемпотентности

```powershell
docker exec wp_labs_redis redis-cli -a redis_secure_password --scan --pattern "wp:events:processed:*"
```

Ожидается список ключей вида:

```text
wp:events:processed:da4c5d2b-6fe4-483b-9e5c-d8b8fbf7cdb7
```

## Проверка retry и DLQ

Этот сценарий показывает, что сообщение не теряется при ошибке SMTP.

### 1. Остановить SMTP-сервер

```powershell
docker compose stop mailpit
```

### 2. Зарегистрировать нового пользователя

```powershell
$email = "lab8.dlq.$([guid]::NewGuid().ToString('N'))@example.com"
$bodyPath = Join-Path $env:TEMP "lab8-register-dlq.json"
@{
  email = $email
  password = "Winter2026"
} | ConvertTo-Json -Compress | Set-Content -Encoding UTF8 -NoNewline $bodyPath

Write-Output "EMAIL=$email"
curl.exe -i `
  -H "Content-Type: application/json" `
  --data-binary "@$bodyPath" `
  http://localhost:4200/auth/register
```

Регистрация должна вернуть `201 Created`, потому что HTTP-регистрация не ждёт успешной отправки email.

### 3. Дождаться retry

SMTP timeout занимает время. Подождите примерно 55 секунд:

```powershell
Start-Sleep -Seconds 55
```

### 4. Проверить DLQ

```powershell
docker exec wp_labs_rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

Ожидается:

```text
wp.auth.user.registered.dlq  1  0
wp.auth.user.registered      0  0
```

### 5. Вернуть SMTP-сервер

```powershell
docker compose start mailpit
```

### 6. Проверить логи retry

```powershell
docker compose logs --tail=160 app
```

Ожидаемые строки:

```text
Welcome email retry requested for event_id=... next_attempt=2
Welcome email retry requested for event_id=... next_attempt=3
Welcome email failed after retries; event_id=... moved to DLQ
```

## Проверка идемпотентности

Смысл проверки: если два раза отправить одно событие с одинаковым `eventId`, письмо должно уйти только один раз.

### 1. Опубликовать одинаковое событие дважды

```powershell
$eventId = [guid]::NewGuid().ToString()
$email = "lab8.idem.$([guid]::NewGuid().ToString('N'))@example.com"

$event = @{
  eventId = $eventId
  eventType = "user.registered"
  timestamp = (Get-Date).ToUniversalTime().ToString("o")
  payload = @{
    userId = [guid]::NewGuid().ToString()
    email = $email
    displayName = "Idempotent User"
  }
  metadata = @{
    attempt = 1
    sourceService = "manual-test"
  }
} | ConvertTo-Json -Depth 6 -Compress

$publishBody = @{
  properties = @{
    delivery_mode = 2
    content_type = "application/json"
  }
  routing_key = "user.registered"
  payload = $event
  payload_encoding = "string"
} | ConvertTo-Json -Depth 6 -Compress

$pair = "student:student_secure_rabbit_pass_change_in_prod"
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = "Basic $basic" }

Write-Output "EVENT_ID=$eventId"
Write-Output "EMAIL=$email"

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:15672/api/exchanges/%2F/app.events/publish" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $publishBody

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:15672/api/exchanges/%2F/app.events/publish" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $publishBody
```

### 2. Проверить, что письмо одно

```powershell
Start-Sleep -Seconds 4
curl.exe -s http://localhost:8025/api/v1/messages | Select-String -Pattern $email
```

Ожидается: письмо для этого email найдено один раз.

### 3. Проверить логи

```powershell
docker compose logs --tail=120 app
```

Ожидаемые строки:

```text
Welcome email sent for event_id=...
RabbitMQ event already processed; ack event_id=...
```

## Очистка DLQ после тестов

Если после проверки retry в `wp.auth.user.registered.dlq` осталось сообщение, его можно удалить через RabbitMQ UI:

1. Открыть `http://localhost:15672`.
2. Перейти в **Queues and Streams**.
3. Открыть `wp.auth.user.registered.dlq`.
4. Нажать **Purge Messages**.

Командой через HTTP API:

```powershell
$pair = "student:student_secure_rabbit_pass_change_in_prod"
$basic = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = "Basic $basic" }

Invoke-RestMethod `
  -Method Delete `
  -Uri "http://localhost:15672/api/queues/%2F/wp.auth.user.registered.dlq/contents" `
  -Headers $headers
```

## Что считается успешной сдачей

- `POST /auth/register` создаёт пользователя.
- После регистрации публикуется событие `user.registered`.
- RabbitMQ queue `wp.auth.user.registered` получает и отдаёт сообщение consumer.
- Consumer отправляет welcome email через SMTP.
- После успешной отправки выполняется `ack`.
- При ошибке SMTP выполняются retry.
- После 3 неудачных попыток сообщение попадает в `wp.auth.user.registered.dlq`.
- Повторное событие с тем же `eventId` не отправляет второе письмо.
- В сообщениях очереди нет паролей, JWT, refresh token и других секретов.

