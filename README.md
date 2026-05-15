# Лабораторная работа №9: Kubernetes

## Краткое описание

В основной проект внедрён Kubernetes-слой для FastAPI-приложения: MongoDB, Redis, MinIO, RabbitMQ, авторизация, кеширование, загрузка файлов и welcome email через очередь.

Для Kubernetes добавлены:

- health endpoints: `/health`, `/health/live`, `/health/ready`;
- readiness-проверка зависимостей: MongoDB, Redis, RabbitMQ, MinIO;
- liveness-проверка процесса;
- Kubernetes manifests для MongoDB, Redis, MinIO, RabbitMQ, Mailpit и API;
- probes в `Deployment/api`;
- горизонтальное масштабирование API;
- Redis distributed lock для регистрации пользователя, чтобы несколько pod не создавали одного пользователя одновременно.

## Структура

```text
app/                    FastAPI-приложение
k8s/00-namespace.yaml   Namespace wp-labs
k8s/02-mongodb/         MongoDB StatefulSet + Service + Secret
k8s/03-redis/           Redis Deployment + Service + Secret
k8s/04-minio/           MinIO StatefulSet + Service + Secret
k8s/05-rabbitmq/        RabbitMQ StatefulSet + Service + Secret
k8s/06-api/             API Deployment + Service + ConfigMap + Secret
k8s/07-mailpit/         Mailpit Deployment + Service
```

PostgreSQL-манифесты оставлены в шаблоне, но для текущего проекта не используются, потому что приложение уже переведено на MongoDB.

## Основные файлы в API

| Файл | Назначение |
|---|---|
| `app/modules/health/router.py` | `/health`, `/health/live`, `/health/ready` |
| `app/main.py` | подключение health-router, startup/shutdown приложения |
| `app/common/cache.py` | Redis cache и distributed lock: `acquire_lock`, `release_lock` |
| `app/modules/auth/service.py` | lock вокруг регистрации пользователя |
| `app/common/queue/rabbitmq.py` | RabbitMQ setup/publish/consume/ack/nack и `ping` для readiness |
| `k8s/06-api/deployment.yaml` | probes, replicas, envFrom, ресурсы API |
| `k8s/06-api/configmap.yaml` | нечувствительная конфигурация API |
| `k8s/06-api/secret.yaml` | пароли, JWT secrets, ключи MinIO/RabbitMQ |

## Сборка Docker-образа

```powershell
cd D:\fastapi-newyear
docker build -t wp-labs/api:1.0.0 .
```

Проверка, что образ появился:

```powershell
docker images wp-labs/api
```

## Деплой в Kubernetes

Перед деплоем включите Kubernetes в Docker Desktop.

Проверка:

```powershell
kubectl cluster-info
kubectl get nodes
```

Применить namespace:

```powershell
cd D:\fastapi-newyear
kubectl apply -f k8s/00-namespace.yaml
```

Применить зависимости:

```powershell
kubectl apply -f k8s/02-mongodb/
kubectl apply -f k8s/03-redis/
kubectl apply -f k8s/04-minio/
kubectl apply -f k8s/05-rabbitmq/
kubectl apply -f k8s/07-mailpit/
```

Применить API:

```powershell
kubectl apply -f k8s/06-api/
```

Проверить запуск:

```powershell
kubectl get all -n wp-labs
kubectl get pods -n wp-labs -o wide
```

Дождаться готовности API:

```powershell
kubectl rollout status deployment/api -n wp-labs
```

## Port-forward

API:

```powershell
kubectl port-forward svc/api 4200:4200 -n wp-labs
```

Swagger:

```text
http://localhost:4200/api/docs
```

RabbitMQ Management UI:

```powershell
kubectl port-forward svc/rabbitmq 15672:15672 -n wp-labs
```

Открыть:

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

Mailpit:

```powershell
kubectl port-forward svc/mailpit 8025:8025 -n wp-labs
```

Открыть:

```text
http://localhost:8025
```

MinIO Console:

```powershell
kubectl port-forward svc/minio 9001:9001 -n wp-labs
```

Открыть:

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

## Health endpoints

После `port-forward svc/api 4200:4200`:

```powershell
curl.exe http://localhost:4200/health
curl.exe http://localhost:4200/health/live
curl.exe http://localhost:4200/health/ready
```

Ожидаемый `/health/live`:

```json
{
  "status": "ok",
  "checked_at": "..."
}
```

Ожидаемый `/health/ready`, если все зависимости доступны:

```json
{
  "status": "ready",
  "checked_at": "...",
  "checks": {
    "mongo": { "status": "ok" },
    "redis": { "status": "ok" },
    "rabbitmq": { "status": "ok" },
    "minio": { "status": "ok" }
  }
}
```

Если хотя бы одна зависимость недоступна, `/health/ready` вернёт `503`.

## Проверка через Swagger

1. Откройте `http://localhost:4200/api/docs`.
2. Выполните `POST /auth/register` или лабораторный alias `POST /users`.
3. Пример тела:

```json
{
  "email": "lab9.user@example.com",
  "password": "Winter2026"
}
```

Ожидается:

- статус `201 Created`;
- пользователь создан в MongoDB;
- access JTI появился в Redis;
- событие `user.registered` опубликовано в RabbitMQ;
- consumer отправил welcome email в Mailpit.

Для пункта масштабирования из задания можно использовать именно `POST /users`; внутри он вызывает тот же сервис регистрации, Redis-lock и публикацию RabbitMQ-события.

Проверить логи API:

```powershell
kubectl logs -l app=api -n wp-labs --tail=120
```

Ожидаемые строки:

```text
Published RabbitMQ event type=user.registered routing_key=user.registered
Received RabbitMQ event event_id=...
Sending welcome email event_id=...
Welcome email sent for event_id=...
```

## Проверка RabbitMQ

```powershell
kubectl exec -it statefulset/rabbitmq -n wp-labs -- rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

После успешной обработки:

```text
wp.auth.user.registered      0      0
wp.auth.user.registered.dlq  0      0
```

## Проверка Redis lock и идемпотентности

Посмотреть ключи регистрации и событий:

```powershell
kubectl exec -it deploy/redis -n wp-labs -- redis-cli -a redis_secure_password --scan --pattern "wp:*"
```

Во время регистрации кратковременно появляется lock:

```text
wp:locks:auth:register:<email>
```

После обработки события появляется ключ идемпотентности:

```text
wp:events:processed:<eventId>
```

## Горизонтальное масштабирование

Увеличить количество pod API:

```powershell
kubectl scale deployment/api --replicas=4 -n wp-labs
kubectl get pods -n wp-labs -l app=api -o wide
```

Проверить, что все pod готовы:

```powershell
kubectl rollout status deployment/api -n wp-labs
```

Снова выполнить регистрацию через Swagger или curl.

Важно: RabbitMQ отдаёт каждое сообщение только одному consumer, поэтому welcome email не должен дублироваться. Redis-lock дополнительно защищает регистрацию одного и того же email от гонки между pod.

Вернуть 2 реплики:

```powershell
kubectl scale deployment/api --replicas=2 -n wp-labs
```

## Проверка retry и DLQ

Остановить Mailpit:

```powershell
kubectl scale deployment/mailpit --replicas=0 -n wp-labs
```

Создать пользователя:

```powershell
$email = "lab9.dlq.$([guid]::NewGuid().ToString('N'))@example.com"
$body = @{ email = $email; password = "Winter2026" } | ConvertTo-Json -Compress
curl.exe -i -H "Content-Type: application/json" -d $body http://localhost:4200/auth/register
```

Подождать около минуты:

```powershell
Start-Sleep -Seconds 60
```

Проверить DLQ:

```powershell
kubectl exec -it statefulset/rabbitmq -n wp-labs -- rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

Ожидается, что `wp.auth.user.registered.dlq` содержит сообщение.

Вернуть Mailpit:

```powershell
kubectl scale deployment/mailpit --replicas=1 -n wp-labs
```

## Полезные команды отладки

```powershell
kubectl get all -n wp-labs
kubectl get pods -n wp-labs -o wide
kubectl describe pod <pod-name> -n wp-labs
kubectl logs -f <pod-name> -n wp-labs
kubectl logs -l app=api -n wp-labs --tail=200
kubectl exec -it <pod-name> -n wp-labs -- /bin/sh
```

Посмотреть переменные окружения в pod API:

```powershell
kubectl exec -it deploy/api -n wp-labs -- printenv
```

## Очистка

Удалить всё окружение лабораторной:

```powershell
kubectl delete namespace wp-labs
```

После удаления namespace Kubernetes удалит deployment, statefulset, service, secret, configmap и PVC внутри `wp-labs`.



