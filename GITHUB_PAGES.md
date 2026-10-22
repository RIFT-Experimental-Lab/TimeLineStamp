# Настройка GitHub Pages

**Пока ничего не опубликовано.** В папке `docs/` лежит техническая версия статического сайта с пустым `data/status.json`. Она читает JSON по относительному пути, поэтому подходит для адреса проекта `https://OWNER.github.io/REPO/`. Согласованный новый дизайн и переключение языков собираются локально командой `python3 demo/build.py` в `../local/TimeLineStamp-demo.html`; перед публикацией их нужно перенести в рабочую страницу и связать с настоящими данными. Файл `.nojekyll` отключает обработку Jekyll.

Когда будем публиковать:

1. Создать отдельный **публичный** репозиторий на GitHub и отправить в него содержимое папки `repository/`. База измерений и локальные черновики находятся в соседней папке `local/`, вне Git. Перед первой отправкой проверить список файлов. Токен телефона никогда не хранить в репозитории.
2. В репозитории открыть **Settings → Pages → Build and deployment**. Выбрать **Deploy from a branch**, ветку **main**, папку **/docs**, нажать **Save**. GitHub Pages будет публиковать содержимое `docs/` после изменений в этой папке.
3. Проверить `https://OWNER.github.io/REPO/`: до подключения телефона страница честно показывает ожидание данных. После создания токена и настройки телефона проверить `https://OWNER.github.io/REPO/data/status.json` и время `published_at`.
4. Под аккаунтом `AntonKreighoff` создать на GitHub fine-grained personal access token, ограниченный этим репозиторием, с правом **Contents: Read and write**. Хранить его только в `~/.config/timelinestamp/github-token` на телефоне с режимом `0600`. Публикатор указывает для обоих полей коммита псевдоним и GitHub `noreply`.

Страница публична. GitHub Pages может показывать новую публикацию с задержкой в несколько минут. Сбор и суточная фиксация не зависят от этой задержки. Для обновления файла телефон использует GitHub Contents API и исходящее HTTPS-соединение; входящий доступ к телефону не нужен.

После подключения телефона он будет добавлять коммиты с обновлением `docs/data/status.json` в `main`. Перед последующей отправкой изменений с Mac нужно сначала получить эти коммиты (`git pull --rebase`), чтобы не столкнуться с расхождением веток.

Источники: [настройка публикации Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [GitHub Contents API](https://docs.github.com/en/rest/repos/contents), [ограничения Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
