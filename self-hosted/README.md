# Самостоятельная версия ФОТ без ИИ

В этой версии остаются три бизнес-кейса, 3D-лиса, аудиозаписи, материалы, финальное поздравление, Polly/QR-код и счётчики завершений. Чат-бот, агент, RAG и запросы к языковым моделям исключены. Все файлы размещаются на вашем сервере. Счётчики нового домена начинаются с нуля.

## Установка из этого репозитория

Сервер: Debian/Ubuntu с systemd. Выполнять от root в консоли сервера. Домены `fot-manager-training.ru` и `www.fot-manager-training.ru` должны указывать на сервер; порты 80/443 — принимать подключения.

Скачайте `self-hosted/install.sh` из выбранного коммита и запустите его. Через переменную `FOT_SOURCE_REF` можно закрепить тот же полный SHA коммита, чтобы установщик загрузил именно проверенные исходники. Пароль SSH или ключи языковых моделей установщику не нужны.

```bash
curl -fL https://raw.githubusercontent.com/ekaterinashliakhova/fot-manager-training/main/self-hosted/install.sh -o /tmp/fot-install.sh
bash /tmp/fot-install.sh
```

Установщик создаёт отдельный проект, пользователя `fottraining`, службу systemd, виртуальный хост Nginx, сертификат Let's Encrypt и автоматическое продление. Если другой веб-сервер уже занимает 80/443 или домен явно настроен в другом виртуальном хосте, установка останавливается до изменений. Имеющийся сайт нельзя отключать вслепую: сначала сохраните конфигурацию и адаптируйте только виртуальный хост этого домена.

## Установка из готового архива

```bash
tar -xzf fot-manager-training-no-ai.tar.gz
cd fot-manager-training-no-ai
bash install.sh
```

В архиве уже есть `public/` и `cases.json`, скачивать исходники не требуется.

## Размещение и сохранность данных

- Приложение: `/opt/fot-manager-training/current`; предыдущие релизы остаются в `releases/`.
- База: `/var/lib/fot-manager-training/completions.sqlite3`.
- Ключ HMAC IP: `/var/lib/fot-manager-training/visitor-hash.key`; создаётся при первом запуске и не меняется при обновлениях.
- Резервные копии конфигурации и базы: `/var/backups/fot-manager-training/`.
- Логи приложения: `journalctl -u fot-manager-training`.

Счётчик сохраняет один зачёт на IP отдельно для каждого сегмента. В базе нет исходных IP, имён или переписки. Проверяется завершение всех вопросов и обязательного квиза. Повторные и одновременные запросы не увеличивают число повторно. Nginx передаёт реальный IP в backend, который доступен только через loopback.

API: `GET /api/training/completions` — числа по сегментам; `GET /api/health` — проверка backend. Endpoint чат-бота отсутствует.

## Сборка вручную

```bash
python3 self-hosted/build.py --source dist --output /tmp/fot-without-ai
cp self-hosted/server.py /tmp/fot-without-ai/
FOT_DATA_DIR=/tmp/fot-test-data FOT_PORT=8766 python3 /tmp/fot-without-ai/server.py
```

Для производственного сервера используйте Nginx: он обслуживает статику, видео/аудио с перемоткой, HTTPS и передаёт API на `127.0.0.1:8766`. Если на сервере уже используется другой reverse proxy, перенесите аналогичные правила в него; не устанавливайте второй процесс на занятые порты.
