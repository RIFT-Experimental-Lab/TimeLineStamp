/* The public page renders fixed records from data/status.json and data/initial.json. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const sources = [
    ['nist', 'NIST Beacon', 288, 'QUANTUM BEACON · 5 MIN'],
    ['nqsn', 'NQSN Beacon', 288, 'QUANTUM BEACON · 5 MIN'],
    ['noaa_mag', 'NOAA Magnetic', 1440, 'SOLAR WIND · 1 MIN'],
    ['noaa_wind', 'NOAA Plasma', 1440, 'SOLAR WIND · 1 MIN'],
  ];
  const dictionary = {
    en: {
      connecting:'CONNECTING TO THE RECORD', waiting:'COLLECTING THE FIRST DAY', updated:'RECORD UPDATED', delayed:'PUBLICATION DELAYED', unavailable:'RECORD UNAVAILABLE',
      noSnapshot:'No public snapshot yet', published:'Published', day:'DAY', state:'STATUS', collecting:'COLLECTING', sealed:'SEALED', record:'RECORD', daily:'DAILY RECORD', first:'FIRST UTC DAY',
      period:'PERIOD', next:'FIXED AT', quantum:'QUANTUM PULSES', firstDay:'First full day', nextNote:'UTC · fixed record', quantumNote:'Two quantum beacons',
      today:'Collection in progress today, UTC. Counts are provisional.', shown:'Measurements in the sealed UTC record. Missing entries remain visible.',
      empty:'Records will appear after the first full UTC day.', count:'RECORDS SHOWN', last30:'LATEST RECORDS',
      photos:'Photographs show instruments and the observation site, not readings from the displayed day.',
      introWaiting:'Each day leaves a digital trace: two streams of quantum pulses and two streams of solar wind measurements. The first full UTC day is being collected.',
      introSealed:'Each day leaves a digital trace: two streams of quantum pulses and two streams of solar wind measurements. This is the sealed record of one day.',
      introSealedV2:'This sealed record combines quantum pulses, solar wind, and additional fixed measurements and activity traces from multiple locations.',
      shadowNote:'An expanded set of {count} fixed streams and areas is being collected in shadow mode. These inputs do not affect the number shown for this day.',
      extraInputs:'ADDITIONAL INPUTS', fixedSeries:'FIXED SERIES',
      coefficient:'Coefficient', noCoefficient:'No sealed daily coefficient yet', waitingSeal:'AWAITING FIRST DAILY SEAL',
      mailSubject:'TimeLineStamp — discrepancy', mailDay:'UTC date', mailRemembered:'Number I remember', mailShown:'Number shown now', mailWhen:'When I noticed the difference',
      good:'● COMPLETE DATA', partial:'● INCOMPLETE DATA', noQuantum:'● QUANTUM DATA UNAVAILABLE',
      initial:'INITIAL SNAPSHOT', initialState:'CAPTURED · INCOMPLETE', initialIntro:'An initial fingerprint from the measurements collected so far. This fixed snapshot covers only part of a UTC day; the first daily coefficient will be sealed separately.',
      initialLock:'INITIAL SNAPSHOT · NOT A DAILY RECORD', initialStreams:'Measurements included in this fixed initial snapshot.', initialMail:'Record type: initial incomplete snapshot',
      initialNumber:'SHORT MARKER FOR THE INITIAL SNAPSHOT', dailyNumber:'SHORT MARKER FOR THE DAILY RECORD', initialPeriod:'PARTIAL UTC WINDOW', initialInstrument:'TS-01 / INITIAL SNAPSHOT', dailyInstrument:'TS-01 / DAILY COEFFICIENT',
      initialUpdated:'INITIAL SNAPSHOT PUBLISHED',
    },
    ru: {
      connecting:'ПОДКЛЮЧЕНИЕ К ЗАПИСИ', waiting:'СБОР ПЕРВЫХ СУТОК', updated:'ЗАПИСЬ ОБНОВЛЕНА', delayed:'ПУБЛИКАЦИЯ ЗАДЕРЖИВАЕТСЯ', unavailable:'ЗАПИСЬ НЕДОСТУПНА',
      noSnapshot:'Публичного снимка пока нет', published:'Опубликовано', day:'СУТКИ', state:'СОСТОЯНИЕ', collecting:'СБОР', sealed:'ЗАКРЫТО', record:'ЗАПИСЬ', daily:'ЗАПИСЬ СУТОК', first:'ПЕРВЫЕ СУТКИ UTC',
      period:'ПЕРИОД', next:'ЗАФИКСИРОВАНО', quantum:'КВАНТОВЫЕ ПУЛЬСЫ', firstDay:'Первые полные сутки', nextNote:'UTC · неизменяемая запись', quantumNote:'Два квантовых маяка',
      today:'Сегодня идёт сбор по UTC. Счётчики предварительные.', shown:'Измерения за закрытые сутки UTC. Пропуски видны в итоговой записи.',
      empty:'Записи появятся после первых полных суток UTC.', count:'ПОКАЗАНО ЗАПИСЕЙ', last30:'ПОСЛЕДНИЕ ЗАПИСИ',
      photos:'Фотографии показывают приборы и место наблюдения, а не измерения за показанные сутки.',
      introWaiting:'Каждые сутки оставляют цифровой след: два потока квантовых пульсов и два потока измерений солнечного ветра. Сейчас идёт сбор первых полных суток UTC.',
      introSealed:'Каждые сутки оставляют цифровой след: два потока квантовых пульсов и два потока измерений солнечного ветра. Перед вами зафиксированная запись одного дня.',
      introSealedV2:'Эта запись объединяет квантовые пульсы, солнечный ветер и дополнительные фиксированные измерения и следы активности из разных мест.',
      shadowNote:'Параллельно в теневом режиме собираются данные из {count} закреплённых рядов и областей. Они пока не влияют на показанное число за сутки.',
      extraInputs:'ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ', fixedSeries:'ЗАКРЕПЛЁННЫХ РЯДОВ',
      coefficient:'Коэффициент', noCoefficient:'Суточный коэффициент ещё не зафиксирован', waitingSeal:'ОЖИДАНИЕ ПЕРВОЙ СУТОЧНОЙ ФИКСАЦИИ',
      mailSubject:'TimeLineStamp — расхождение', mailDay:'Дата UTC', mailRemembered:'Число, которое я помню', mailShown:'Число на странице сейчас', mailWhen:'Когда заметил расхождение',
      good:'● ПОЛНЫЕ ДАННЫЕ', partial:'● НЕПОЛНЫЕ ДАННЫЕ', noQuantum:'● НЕТ КВАНТОВЫХ ДАННЫХ',
      initial:'ПЕРВИЧНЫЙ СНИМОК', initialState:'ЗАФИКСИРОВАН · НЕПОЛНЫЙ', initialIntro:'Первичный отпечаток из уже собранных измерений. Этот неизменяемый снимок охватывает лишь часть суток UTC; первый суточный коэффициент будет зафиксирован отдельно.',
      initialLock:'ПЕРВИЧНЫЙ СНИМОК · НЕ СУТОЧНАЯ ЗАПИСЬ', initialStreams:'Измерения, вошедшие в зафиксированный первичный снимок.', initialMail:'Тип записи: первичный неполный снимок',
      initialNumber:'КОРОТКАЯ МЕТКА ПЕРВИЧНОГО СНИМКА', dailyNumber:'КОРОТКАЯ МЕТКА ЗАПИСИ ЗА СУТКИ', initialPeriod:'НЕПОЛНЫЙ ПЕРИОД UTC', initialInstrument:'TS-01 / ПЕРВИЧНЫЙ СНИМОК', dailyInstrument:'TS-01 / СУТОЧНЫЙ КОЭФФИЦИЕНТ',
      initialUpdated:'ПЕРВИЧНЫЙ СНИМОК ОПУБЛИКОВАН',
    },
    zh: {
      connecting:'正在连接记录', waiting:'正在采集首个完整日期', updated:'记录已更新', delayed:'发布延迟', unavailable:'记录不可用',
      noSnapshot:'尚无公开快照', published:'发布时间', day:'日期', state:'状态', collecting:'采集中', sealed:'已封存', record:'记录', daily:'每日记录', first:'首个 UTC 日期',
      period:'周期', next:'记录时间', quantum:'量子脉冲', firstDay:'首个完整日期', nextNote:'UTC · 已固定记录', quantumNote:'两个量子信标',
      today:'正在采集今天的 UTC 数据，计数尚未确定。', shown:'已封存 UTC 日期的测量值。缺失项会保留在记录中。',
      empty:'首个完整 UTC 日期结束后，记录将显示在这里。', count:'显示记录数', last30:'最近记录',
      photos:'照片展示仪器和观测地点，并非当前日期的测量结果。',
      introWaiting:'每个 UTC 日期都会留下数字痕迹：两路量子脉冲和两路太阳风测量。目前正在采集首个完整日期。',
      introSealed:'每个 UTC 日期都会留下数字痕迹：两路量子脉冲和两路太阳风测量。这是某一天的封存记录。',
      introSealedV2:'这份封存记录结合了量子脉冲、太阳风，以及来自多个地点的固定测量和活动记录。',
      shadowNote:'另有 {count} 个固定数据序列和区域正在影子模式下采集；这些数据目前不影响页面显示的每日数字。',
      extraInputs:'其他输入', fixedSeries:'固定数据序列',
      coefficient:'系数', noCoefficient:'尚无已封存的每日系数', waitingSeal:'等待首次每日封存',
      mailSubject:'TimeLineStamp — 读数差异', mailDay:'UTC 日期', mailRemembered:'我记得的数字', mailShown:'页面当前显示的数字', mailWhen:'发现差异的时间',
      good:'● 数据完整', partial:'● 数据不完整', noQuantum:'● 量子数据不可用',
      initial:'初始快照', initialState:'已记录 · 数据不完整', initialIntro:'根据目前已采集的测量值生成的初始指纹。这份固定快照只覆盖 UTC 日期的一部分；首个每日系数将另行封存。',
      initialLock:'初始快照 · 非每日记录', initialStreams:'此固定初始快照包含的测量值。', initialMail:'记录类型：初始不完整快照',
      initialNumber:'初始快照的简短标记', dailyNumber:'每日记录的简短标记', initialPeriod:'UTC 日期的部分时段', initialInstrument:'TS-01 / 初始快照', dailyInstrument:'TS-01 / 每日系数',
      initialUpdated:'初始快照已发布',
    },
  };
  const periodWords = {
    en: {title:'Period codes', intro:'Short marks for smaller UTC intervals. Compare a remembered mark with the same period here. They narrow a difference in measurements; they cannot establish the exact time of an intervention.',
      day:'DAY', week:'WEEK', month:'MONTH', year:'YEAR', pending:'awaiting seal', unavailable:'no complete record', sealed:'sealed',
      risk:'One changed interval can retain the same short mark with probability', legend:'A solid mark is sealed. A moving mark is only a placeholder. A dash means no complete record for that period.', noDay:'The first daily record is still being collected.',
      format:'Format', weekDay:'UTC day', monthBlock:'UTC dates', monthName:'UTC month'},
    ru: {title:'Коды периодов', intro:'Короткие метки для меньших интервалов UTC. Сравните метку, которую помните, с тем же периодом здесь. Они сужают расхождение в измерениях, но не устанавливают точное время вмешательства.',
      day:'ДЕНЬ', week:'НЕДЕЛЯ', month:'МЕСЯЦ', year:'ГОД', pending:'ожидает фиксации', unavailable:'нет полной записи', sealed:'зафиксировано',
      risk:'Вероятность совпадения короткой метки при изменении одного интервала', legend:'Постоянная метка зафиксирована. Перебирающийся знак — только заглушка. Прочерк означает отсутствие полной записи за период.', noDay:'Первые полные сутки ещё собираются.',
      format:'Формат', weekDay:'Сутки UTC', monthBlock:'Даты UTC', monthName:'Месяц UTC'},
    zh: {title:'时段代码', intro:'较短 UTC 时段的简短标记。请将记忆中的标记与此处同一时段比较。它们可缩小测量差异所在的时段，但无法确定干预发生的确切时间。',
      day:'日', week:'周', month:'月', year:'年', pending:'等待封存', unavailable:'无完整记录', sealed:'已封存',
      risk:'一个时段改变后简短标记仍相同的概率', legend:'固定标记已封存。跳动字符只是占位符。横线表示该时段没有完整记录。', noDay:'首个完整 UTC 日期仍在采集中。',
      format:'格式', weekDay:'UTC 日期', monthBlock:'UTC 日期', monthName:'UTC 月份'},
  };
  const periodAlphabets = {hex:'0123456789ABCDEF', base32:'0123456789ABCDEFGHJKMNPQRSTVWXYZ', base58:'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'};
  const rawWords = {
    en:{title:'RAW DATA / UTC DAY',description:'Request a compressed snapshot of stored observations and the sealed daily manifest. Late shadow inputs may appear in a newer snapshot.',date:'UTC date',button:'Download day archive',hint:'Availability is checked when you request an archive.',checking:'Checking the archive server…',offline:'The archive server is temporarily unavailable. Please try again later.',notConnected:'The archive service has not been connected yet.',missing:'Raw data for this date are unavailable on the current server.',sent:'Download requested. If no file appears, try again.'},
    ru:{title:'СЫРЫЕ ДАННЫЕ / СУТКИ UTC',description:'Сжатый снимок сохранённых измерений и зафиксированный суточный манифест. Поздние теневые данные могут появиться в новой версии снимка.',date:'Дата UTC',button:'Скачать архив за сутки',hint:'Доступность проверяется при запросе архива.',checking:'Проверяем сервер архивов…',offline:'Сервер архивов временно недоступен. Попробуйте позже.',notConnected:'Сервис архивов ещё не подключён.',missing:'На текущем сервере нет сырых данных за эту дату.',sent:'Скачивание запрошено. Если файл не появился, попробуйте ещё раз.'},
    zh:{title:'原始数据 / UTC 日期',description:'下载已保存观测数据和已封存每日清单的压缩快照。延迟到达的影子数据可能出现在更新版本中。',date:'UTC 日期',button:'下载每日档案',hint:'请求档案时将检查可用性。',checking:'正在检查档案服务器…',offline:'档案服务器暂时不可用，请稍后重试。',notConnected:'档案服务尚未连接。',missing:'当前服务器没有该日期的原始数据。',sent:'已请求下载。如果未出现文件，请重试。'},
  };
  let rawMessage = 'hint';
  let periodFormat = 'hex';
  let snapshot = null;
  let initial = null;
  let failed = false;
  const lang = () => document.documentElement.lang === 'ru' ? 'ru' : document.documentElement.lang.startsWith('zh') ? 'zh' : 'en';
  const t = () => dictionary[lang()];
  const put = (id, value) => { $(id).textContent = value; };
  function dateLabel(day) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day || '')) return '—';
    const [year, month, date] = day.split('-');
    return `${date}.${month}.${year}`;
  }
  function utcStamp(value) {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toISOString().slice(0,16).replace('T',' ') + ' UTC' : '—';
  }
  function sealDue(day, daysAfter) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day || '')) return null;
    const due = new Date(`${day}T00:15:00Z`);
    due.setUTCDate(due.getUTCDate() + daysAfter);
    return due;
  }
  function add(parent, tag, value, className) {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    parent.appendChild(node);
    return node;
  }
  function renderNumber(value) {
    const meter = $('meter');
    meter.replaceChildren();
    if (!/^\d\.\d{6}$/.test(String(value || ''))) {
      meter.textContent = '—.——————';
      meter.setAttribute('aria-label', t().noCoefficient);
      return;
    }
    for (const char of value) add(meter, 'span', char, char === '.' ? 'point' : 'digit').setAttribute('aria-hidden', 'true');
    meter.setAttribute('aria-label', `${t().coefficient} ${value}`);
  }
  function renderHash(hash) {
    put('digest', /^[a-f0-9]{64}$/i.test(hash || '') ? hash : '—');
    const graph = document.querySelector('.signature-graph svg g');
    graph.replaceChildren();
    if (!/^[a-f0-9]{64}$/i.test(hash || '')) return;
    [...hash.toLowerCase()].forEach((digit, index) => {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      const x = 2 + index * 4;
      const height = 7 + parseInt(digit, 16) * 2.1;
      for (const [name, value] of Object.entries({x1:x, y1:(43-height).toFixed(1), x2:x, y2:43})) line.setAttribute(name, String(value));
      graph.appendChild(line);
    });
  }
  function renderRawLabels() {
    const words = rawWords[lang()];
    put('raw-title', words.title); put('raw-description', words.description);
    put('raw-date-label', words.date); put('raw-button', words.button); put('raw-status', words[rawMessage]);
    const input = $('raw-day');
    if (!input.value && snapshot?.current?.day) input.value = snapshot.current.day;
    if (snapshot?.first_full_day) input.min = snapshot.first_full_day;
    if (snapshot?.current?.day) input.max = snapshot.current.day;
  }
  async function downloadDay(event) {
    event.preventDefault();
    const button = $('raw-button');
    if (button.disabled) return;
    button.disabled = true; rawMessage = 'checking'; renderRawLabels();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`./data/downloads.json?t=${Date.now()}`, {cache:'no-store',signal:controller.signal});
      if (!response.ok) throw new Error('metadata');
      const metadata = await response.json();
      if (metadata.format !== 'timelinestamp-downloads-v1' || !metadata.base_url) { rawMessage = 'notConnected'; return; }
      if (!/^https:\/\/[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com$/.test(metadata.base_url)) throw new Error('endpoint');
      const catalogResponse = await fetch(metadata.base_url + '/v1/catalog', {cache:'no-store',signal:controller.signal});
      if (!catalogResponse.ok) throw new Error('catalog');
      const catalog = await catalogResponse.json();
      const day = $('raw-day').value;
      if (catalog.format !== 'timelinestamp-archive-catalog-v1' || !Array.isArray(catalog.days)) throw new Error('catalog');
      if (!catalog.days.some(record => record.day === day)) { rawMessage = 'missing'; return; }
      const link = document.createElement('a');
      link.href = `${metadata.base_url}/v1/day/${encodeURIComponent(day)}.tar.gz`;
      link.rel = 'noopener'; document.body.appendChild(link); link.click(); link.remove();
      rawMessage = 'sent';
    } catch (_) { rawMessage = 'offline'; }
    finally { clearTimeout(timeout); button.disabled = false; renderRawLabels(); }
  }
  function renderPeriodCodes(data) {
    const words = periodWords[lang()];
    put('pc-title', words.title);
    put('pc-intro', words.intro);
    put('pc-legend', words.legend);
    $('pc-formats').setAttribute('aria-label', words.format);
    document.querySelectorAll('[data-pc-format]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.pcFormat === periodFormat));
      button.setAttribute('aria-label', `${words.format}: ${button.textContent}`);
    });
    const base = periodAlphabets[periodFormat].length;
    put('pc-format-note', `${periodFormat.toUpperCase()} · ${base} ${lang() === 'zh' ? '个字符' : lang() === 'ru' ? 'символов' : 'symbols'}`);
    const registers = $('pc-registers');
    registers.replaceChildren();
    const periods = data?.period_codes;
    if (periods?.format !== 'timelinestamp-period-v1') {
      add(registers, 'p', words.noDay, 'pc-intro');
      return;
    }
    for (const scope of ['day','week','month','year']) {
      const record = periods[scope];
      const section = add(registers, 'section', '', 'pc-register');
      const head = add(section, 'div', '', 'pc-register-head');
      add(head, 'span', words[scope], 'pc-register-name');
      add(head, 'span', record ? `${record.label} · UTC` : '—', 'pc-register-date');
      const positions = record?.positions || [];
      add(head, 'span', `${positions.filter(position => position.state === 'sealed').length}/${positions.length || (scope === 'day' ? 6 : scope === 'week' ? 7 : scope === 'month' ? 4 : 12)} ${words.sealed}`, 'pc-register-state');
      if (scope === 'day' && !record) { add(section, 'p', words.noDay, 'pc-intro'); continue; }
      const probability = (100 / base ** (scope === 'month' ? 2 : 1)).toLocaleString(lang(), {maximumFractionDigits:4});
      add(section, 'p', `${words.risk}: ${probability}%`, 'pc-risk');
      const scroller = add(section, 'div', '', 'pc-code-scroll');
      const code = add(scroller, 'div', '', 'pc-code');
      positions.forEach((position, index) => {
        if (index) add(code, 'span', '.', 'pc-dot').setAttribute('aria-hidden', 'true');
        const group = add(code, 'div', '', scope === 'month' ? 'pc-group pc-group--pair' : 'pc-group');
        const start = new Date(position.start_utc);
        const end = new Date(new Date(position.end_utc).getTime() - 1);
        const label = scope === 'day' ? `${String(start.getUTCHours()).padStart(2,'0')}–${String((end.getUTCHours()+1) % 24 || 24).padStart(2,'0')}` :
          scope === 'week' ? new Intl.DateTimeFormat(lang(), {timeZone:'UTC', day:'2-digit', month:'2-digit'}).format(start) :
          scope === 'month' ? `${String(start.getUTCDate()).padStart(2,'0')}–${String(end.getUTCDate()).padStart(2,'0')}` :
          new Intl.DateTimeFormat(lang(), {timeZone:'UTC', month:'short'}).format(start);
        add(group, 'span', label, 'pc-period');
        const state = position.state === 'sealed' ? 'sealed' : position.state === 'unavailable' ? 'unavailable' : 'pending';
        const glyphs = add(group, 'div', '', 'pc-pair-digits');
        const value = state === 'sealed' ? position.codes?.[periodFormat] : null;
        for (let i = 0; i < (scope === 'month' ? 2 : 1); i++) {
          const glyph = add(glyphs, 'span', value?.[i] || (state === 'unavailable' ? '—' : '?'), 'pc-glyph');
          glyph.dataset.state = state;
          glyph.setAttribute('aria-hidden', 'true');
        }
        group.setAttribute('aria-label', `${label} UTC: ${state === 'sealed' ? value : words[state]}`);
        if (position.sha256) group.title = `SHA-256 ${position.sha256}`;
      });
    }
  }
  function renderStreams(data, record, isInitial) {
    const container = $('streams');
    container.replaceChildren();
    const base = isInitial ? t().initialStreams : record ? t().shown : t().today;
    const hasExtraInputs = Object.keys(record?.counts || {}).some(key => !sources.some(([source]) => source === key));
    const shadowCount = Number(data.v2_enabled_source_count);
    const shadow = data.v2_shadow_start_day_utc && !hasExtraInputs && Number.isInteger(shadowCount) && shadowCount > 0;
    put('streams-description', base + (shadow ? ` ${t().shadowNote.replace('{count}', shadowCount)}` : ''));
    sources.forEach(([key, name, expected, subtitle], index) => {
      const raw = record?.counts?.[key]?.received;
      const count = Number.isFinite(Number(raw)) ? Math.max(0, Number(raw)) : 0;
      const total = Number(record?.counts?.[key]?.expected) || expected;
      const row = add(container, 'div', '', 'stream');
      add(row, 'span', String(index+1).padStart(2,'0'), 'stream-no');
      const label = add(row, 'div', '', 'stream-name');
      add(label, 'strong', name); add(label, 'small', subtitle);
      add(row, 'span', `${count.toLocaleString(lang())} / ${total.toLocaleString(lang())}`, 'stream-count');
      const bar = add(row, 'div', '', 'stream-bar');
      const percent = Math.min(100, 100*count/total);
      bar.style.setProperty('--fill', `${percent.toFixed(1)}%`);
      add(bar, 'i', ''); add(bar, 'small', `${percent.toFixed(1)}%`);
    });
    const extras = Object.entries(record?.counts || {}).filter(([key]) => !sources.some(([source]) => source === key));
    if (extras.length) {
      const received = extras.reduce((sum, [, value]) => sum + (Number(value?.received) || 0), 0);
      const expected = extras.reduce((sum, [, value]) => sum + (Number(value?.expected) || 0), 0);
      const row = add(container, 'div', '', 'stream');
      add(row, 'span', '05+', 'stream-no');
      const label = add(row, 'div', '', 'stream-name');
      add(label, 'strong', t().extraInputs); add(label, 'small', `${extras.length} ${t().fixedSeries}`);
      add(row, 'span', `${received.toLocaleString(lang())} / ${expected.toLocaleString(lang())}`, 'stream-count');
      const bar = add(row, 'div', '', 'stream-bar');
      const percent = expected ? Math.min(100, 100*received/expected) : 0;
      bar.style.setProperty('--fill', `${percent.toFixed(1)}%`);
      add(bar, 'i', ''); add(bar, 'small', `${percent.toFixed(1)}%`);
    }
  }
  function renderArchive(history, initialRecord) {
    const body = $('history');
    body.replaceChildren();
    const entries = Array.isArray(history) ? history.slice(0,30) : [];
    for (const item of entries) {
      const row = add(body, 'tr', '');
      add(row, 'td', dateLabel(item.day));
      add(row, 'td', String(item.coefficient || '—'), 'row-value');
      const state = item.quality === 'good' ? t().good : item.quality === 'partial' ? t().partial : t().noQuantum;
      add(row, 'td', state, item.quality === 'good' ? 'row-state' : 'row-state partial');
      const hash = add(row, 'td', String(item.digest || '—').slice(0,16) + '…', 'row-hash');
      hash.title = String(item.digest || '');
    }
    if (initialRecord) {
      const row = add(body, 'tr', '');
      add(row, 'td', `${dateLabel(initialRecord.day)} · ${t().initial}`);
      add(row, 'td', String(initialRecord.coefficient || '—'), 'row-value');
      add(row, 'td', t().initialState, 'row-state partial');
      const hash = add(row, 'td', String(initialRecord.digest || '—').slice(0,16) + '…', 'row-hash');
      hash.title = String(initialRecord.digest || '');
    }
    if (!entries.length && !initialRecord) {
      const row = add(body, 'tr', '');
      add(row, 'td', t().empty).colSpan = 4;
    }
    put('archive-count', `${t().count}: ${entries.length + (initialRecord ? 1 : 0)}`);
    put('archive-note', t().last30);
  }
  function renderMail(record, isInitial) {
    const word = t();
    const date = record?.day || '';
    const number = record?.coefficient || '';
    const subject = date ? `${word.mailSubject} ${date}` : word.mailSubject;
    const body = `${isInitial ? word.initialMail + '\n' : ''}${word.mailDay}: ${date}\n${word.mailRemembered}: \n${word.mailShown}: ${number}\n${word.mailWhen}: `;
    document.querySelector('[data-mailto="discrepancy"]').href = `mailto:rift.research@outlook.com?${new URLSearchParams({subject, body})}`;
  }
  function render() {
    const data = snapshot || {};
    const current = data.current && typeof data.current === 'object' ? data.current : null;
    const isInitial = !current && !!initial;
    const record = current || initial;
    const word = t();
    const published = data.published_at ? new Date(data.published_at) : null;
    const valid = published && Number.isFinite(published.getTime());
    const nextDay = current && /^\d{4}-\d{2}-\d{2}$/.test(current.day) ?
      new Date(`${current.day}T00:00:00Z`) : null;
    if (nextDay) nextDay.setUTCDate(nextDay.getUTCDate() + 1);
    const nextDayText = nextDay ? nextDay.toISOString().slice(0, 10) : data.first_full_day;
    const nextIsV2 = !!data.v2_start_day_utc && nextDayText >= data.v2_start_day_utc;
    const due = current ? sealDue(current.day, nextIsV2 ? 4 : 2) :
      sealDue(data.first_full_day, nextIsV2 ? 3 : 1);
    const stale = valid && due && Date.now() - due.getTime() > 3*3600_000;
    put('live-label', failed ? word.unavailable : !valid ? snapshot ? word.waiting : word.connecting : stale ? word.delayed : current ? word.updated : isInitial ? word.initialUpdated : word.waiting);
    put('last-published', valid ? `${word.published}: ${utcStamp(data.published_at)}` : word.noSnapshot);
    const day = record?.day || data.first_full_day || '';
    const shownDay = dateLabel(day);
    put('record-node', `${word.record} ${day || '—'} / UTC`);
    put('rail-status', `${word.day}: ${shownDay}\nUTC\n${word.state}: ${isInitial ? word.initialState : current ? word.sealed : word.collecting}`);
    $('rail-status').style.whiteSpace = 'pre-line';
    put('day-kicker', isInitial ? `${word.initial} / ${shownDay}` : current ? `${word.daily} / ${shownDay}` : `${word.first} / ${shownDay}`);
    const hasExtraInputs = current && Object.keys(current.counts || {}).some(key => !sources.some(([source]) => source === key));
    put('page-intro', isInitial ? word.initialIntro : current ? hasExtraInputs ? word.introSealedV2 : word.introSealed : word.introWaiting);
    document.querySelector('.instrument').setAttribute('aria-label', isInitial ? word.initial : word.daily);
    put('instrument-label', isInitial ? word.initialInstrument : word.dailyInstrument);
    put('lock-status', isInitial ? `${word.initialLock} · ${utcStamp(initial.created_at)}` : current ? `${word.sealed} · ${utcStamp(current.created_at)}` : word.waitingSeal);
    put('display-day', `${shownDay} · UTC`);
    renderNumber(record?.coefficient);
    if (isInitial) $('meter').setAttribute('aria-label', `${word.initial} ${record.coefficient}`);
    put('number-note', isInitial ? word.initialNumber : word.dailyNumber);
    put('quality', isInitial ? word.initialState : current ? current.quality === 'good' ? word.good : current.quality === 'partial' ? word.partial : word.noQuantum : word.collecting);
    renderHash(record?.digest);
    renderPeriodCodes(data);
    renderRawLabels();
    put('period-label', word.period);
    put('period', isInitial ? shownDay : current ? shownDay : data.first_full_day ? `${word.firstDay}: ${shownDay}` : '—');
    put('period-note', isInitial ? `${word.initialPeriod}: ${utcStamp(initial.period_start)} – ${utcStamp(initial.created_at)}` : '00:00–24:00 UTC');
    put('next-lock-label', word.next);
    put('next-lock', record?.created_at ? utcStamp(record.created_at) : '—');
    put('next-lock-note', word.nextNote);
    put('quantum-label', word.quantum);
    const nist = Number(record?.counts?.nist?.received ?? 0);
    const nqsn = Number(record?.counts?.nqsn?.received ?? 0);
    put('quantum-count', `${Math.max(0, nist+nqsn)} / 576`);
    put('quantum-note', word.quantumNote);
    renderStreams(data, record, isInitial);
    renderArchive(data.history, initial);
    put('library-endnote', word.photos);
    renderMail(record, isInitial);
  }
  async function refresh() {
    try {
      const [response, initialResponse] = await Promise.all([
        fetch(`./data/status.json?t=${Date.now()}`, {cache:'no-store'}),
        fetch(`./data/initial.json?t=${Date.now()}`, {cache:'no-store'}).catch(() => null),
      ]);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.format !== 'timelinestamp-status-v1') throw new Error('Unsupported status format');
      snapshot = data;
      if (initialResponse?.ok) {
        const candidate = await initialResponse.json();
        initial = candidate.format === 'timelinestamp-initial-v1' ? candidate : null;
      }
      failed = false;
    } catch (error) {
      failed = true;
      console.error(error);
    }
    render();
  }
  document.querySelectorAll('.language-switch [data-lang]').forEach(button => button.addEventListener('click', render));
  $('raw-download-form').addEventListener('submit', downloadDay);
  document.querySelectorAll('[data-pc-format]').forEach(button => button.addEventListener('click', () => {
    periodFormat = button.dataset.pcFormat;
    renderPeriodCodes(snapshot);
  }));
  setInterval(() => {
    if (!$('period-codes').open || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const alphabet = periodAlphabets[periodFormat];
    document.querySelectorAll('#period-codes .pc-glyph[data-state="pending"]').forEach(glyph => {
      glyph.textContent = alphabet[Math.floor(Math.random() * alphabet.length)];
    });
  }, 90);
  render();
  refresh();
  setInterval(refresh, 5*60_000);
})();
