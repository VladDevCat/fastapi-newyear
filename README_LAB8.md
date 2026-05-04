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

