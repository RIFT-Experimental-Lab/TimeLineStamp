# Публикация GitHub Pages

**Сайт опубликован:** [rift-experimental-lab.github.io/TimeLineStamp/](https://rift-experimental-lab.github.io/TimeLineStamp/). GitHub Pages берёт файлы из `main/docs`. Страница читает закрытые суточные записи и коды периодов из `data/status.json`, а отдельный фиксированный первичный снимок — из `data/initial.json`. Сервер публикует новый статус один раз после каждой суточной фиксации. Демо собирается отдельно в `../local/TimeLineStamp-demo.html`. Файл `.nojekyll` отключает обработку Jekyll.

После изменения макета в `demo/` пересоберите оба файла командой `python3 demo/build_public.py` из корня репозитория. Она обновляет локальное демо и `docs/index.html`; измеренные числа в страницу подставляет `docs/app.js` из `docs/data/status.json`.

Сделано:

1. Создан публичный репозиторий `RIFT-Experimental-Lab/TimeLineStamp`. В него отправлена только папка `repository/`. База измерений и локальные черновики находятся в соседней папке `local/`, вне Git.
2. GitHub Pages настроен на ветку `main` и папку `/docs`. Проверены публичная страница и `data/status.json`.
3. На сервере установлен ограниченный токен для одного репозитория и включена автоматическая публикация статуса.

Если потребуется заменить токен:

1. Под аккаунтом `AntonKreighoff` создать fine-grained personal access token, ограниченный этим репозиторием, с правом **Contents: Read and write**. Хранить его только в `~/.config/timelinestamp/github-token` на сервере с режимом `0600`. Не добавлять токен в репозиторий. Публикатор указывает для обоих полей коммита псевдоним и GitHub `noreply`.
2. Проверить [публичный JSON](https://rift-experimental-lab.github.io/TimeLineStamp/data/status.json): `published_at` должен обновиться после следующей суточной фиксации. Первая суточная запись появится после первых полных суток UTC.

Страница публична. GitHub Pages может показывать новую публикацию с задержкой в несколько минут. Сбор и суточная фиксация не зависят от этой задержки. Для обновления файла телефон использует GitHub Contents API и исходящее HTTPS-соединение; входящий доступ к телефону не нужен.

После подключения телефона он будет добавлять коммиты с обновлением `docs/data/status.json` в `main`. Перед последующей отправкой изменений с Mac нужно сначала получить эти коммиты (`git pull --rebase`), чтобы не столкнуться с расхождением веток.

Источники: [настройка публикации Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [GitHub Contents API](https://docs.github.com/en/rest/repos/contents), [ограничения Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
