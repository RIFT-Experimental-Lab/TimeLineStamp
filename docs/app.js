/* The public page renders measurements only from data/status.json. */
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
      period:'PERIOD', next:'NEXT SEAL', quantum:'QUANTUM PULSES', firstDay:'First full day', nextNote:'UTC, after the next day', quantumNote:'Two quantum beacons',
      today:'Collection in progress today, UTC. Counts are provisional.', shown:'Measurements in the sealed UTC record. Missing entries remain visible.',
      empty:'Records will appear after the first full UTC day.', count:'DAYS SHOWN', last30:'LATEST 30 DAYS',
      photos:'Photographs show instruments and the observation site, not readings from the displayed day.',
      introWaiting:'Each day leaves a digital trace: two streams of quantum pulses and two streams of solar wind measurements. The first full UTC day is being collected.',
      introSealed:'Each day leaves a digital trace: two streams of quantum pulses and two streams of solar wind measurements. This is the sealed record of one day.',
      coefficient:'Coefficient', noCoefficient:'No sealed daily coefficient yet', waitingSeal:'AWAITING FIRST DAILY SEAL',
      mailSubject:'TimeLineStamp — discrepancy', mailDay:'UTC date', mailRemembered:'Number I remember', mailShown:'Number shown now', mailWhen:'When I noticed the difference',
      good:'● COMPLETE DATA', partial:'● INCOMPLETE DATA', noQuantum:'● QUANTUM DATA UNAVAILABLE',
      initial:'INITIAL SNAPSHOT', initialState:'CAPTURED · INCOMPLETE', initialIntro:'An initial fingerprint from the measurements collected so far. This fixed snapshot covers only part of a UTC day; the first daily coefficient will be sealed separately.',
      initialLock:'INITIAL SNAPSHOT · NOT A DAILY RECORD', initialStreams:'Measurements included in this fixed initial snapshot. Collection continues for the first full UTC day.', initialMail:'Record type: initial incomplete snapshot',
      initialNumber:'SHORT MARKER FOR THE INITIAL SNAPSHOT', dailyNumber:'SHORT MARKER FOR THE DAILY RECORD', initialPeriod:'PARTIAL UTC WINDOW', initialInstrument:'TS-01 / INITIAL SNAPSHOT', dailyInstrument:'TS-01 / DAILY COEFFICIENT',
      initialUpdated:'INITIAL SNAPSHOT PUBLISHED',
    },
    ru: {
      connecting:'ПОДКЛЮЧЕНИЕ К ЗАПИСИ', waiting:'СБОР ПЕРВЫХ СУТОК', updated:'ЗАПИСЬ ОБНОВЛЕНА', delayed:'ПУБЛИКАЦИЯ ЗАДЕРЖИВАЕТСЯ', unavailable:'ЗАПИСЬ НЕДОСТУПНА',
      noSnapshot:'Публичного снимка пока нет', published:'Опубликовано', day:'СУТКИ', state:'СОСТОЯНИЕ', collecting:'СБОР', sealed:'ЗАКРЫТО', record:'ЗАПИСЬ', daily:'ЗАПИСЬ СУТОК', first:'ПЕРВЫЕ СУТКИ UTC',
      period:'ПЕРИОД', next:'СЛЕДУЮЩАЯ ФИКСАЦИЯ', quantum:'КВАНТОВЫЕ ПУЛЬСЫ', firstDay:'Первые полные сутки', nextNote:'UTC, после новых суток', quantumNote:'Два квантовых маяка',
      today:'Сегодня идёт сбор по UTC. Счётчики предварительные.', shown:'Измерения за закрытые сутки UTC. Пропуски видны в итоговой записи.',
      empty:'Записи появятся после первых полных суток UTC.', count:'ПОКАЗАНО ДНЕЙ', last30:'ПОСЛЕДНИЕ 30 ДНЕЙ',
      photos:'Фотографии показывают приборы и место наблюдения, а не измерения за показанные сутки.',
      introWaiting:'Каждые сутки оставляют цифровой след: два потока квантовых пульсов и два потока измерений солнечного ветра. Сейчас идёт сбор первых полных суток UTC.',
      introSealed:'Каждые сутки оставляют цифровой след: два потока квантовых пульсов и два потока измерений солнечного ветра. Перед вами зафиксированная запись одного дня.',
      coefficient:'Коэффициент', noCoefficient:'Суточный коэффициент ещё не зафиксирован', waitingSeal:'ОЖИДАНИЕ ПЕРВОЙ СУТОЧНОЙ ФИКСАЦИИ',
      mailSubject:'TimeLineStamp — расхождение', mailDay:'Дата UTC', mailRemembered:'Число, которое я помню', mailShown:'Число на странице сейчас', mailWhen:'Когда заметил расхождение',
      good:'● ПОЛНЫЕ ДАННЫЕ', partial:'● НЕПОЛНЫЕ ДАННЫЕ', noQuantum:'● НЕТ КВАНТОВЫХ ДАННЫХ',
      initial:'ПЕРВИЧНЫЙ СНИМОК', initialState:'ЗАФИКСИРОВАН · НЕПОЛНЫЙ', initialIntro:'Первичный отпечаток из уже собранных измерений. Этот неизменяемый снимок охватывает лишь часть суток UTC; первый суточный коэффициент будет зафиксирован отдельно.',
      initialLock:'ПЕРВИЧНЫЙ СНИМОК · НЕ СУТОЧНАЯ ЗАПИСЬ', initialStreams:'Измерения, вошедшие в первичный снимок. Сбор первых полных суток UTC продолжается.', initialMail:'Тип записи: первичный неполный снимок',
      initialNumber:'КОРОТКАЯ МЕТКА ПЕРВИЧНОГО СНИМКА', dailyNumber:'КОРОТКАЯ МЕТКА ЗАПИСИ ЗА СУТКИ', initialPeriod:'НЕПОЛНЫЙ ПЕРИОД UTC', initialInstrument:'TS-01 / ПЕРВИЧНЫЙ СНИМОК', dailyInstrument:'TS-01 / СУТОЧНЫЙ КОЭФФИЦИЕНТ',
      initialUpdated:'ПЕРВИЧНЫЙ СНИМОК ОПУБЛИКОВАН',
    },
    zh: {
      connecting:'正在连接记录', waiting:'正在采集首个完整日期', updated:'记录已更新', delayed:'发布延迟', unavailable:'记录不可用',
      noSnapshot:'尚无公开快照', published:'发布时间', day:'日期', state:'状态', collecting:'采集中', sealed:'已封存', record:'记录', daily:'每日记录', first:'首个 UTC 日期',
      period:'周期', next:'下次封存', quantum:'量子脉冲', firstDay:'首个完整日期', nextNote:'UTC，下一日结束后', quantumNote:'两个量子信标',
      today:'正在采集今天的 UTC 数据，计数尚未确定。', shown:'已封存 UTC 日期的测量值。缺失项会保留在记录中。',
      empty:'首个完整 UTC 日期结束后，记录将显示在这里。', count:'显示天数', last30:'最近 30 天',
      photos:'照片展示仪器和观测地点，并非当前日期的测量结果。',
      introWaiting:'每个 UTC 日期都会留下数字痕迹：两路量子脉冲和两路太阳风测量。目前正在采集首个完整日期。',
      introSealed:'每个 UTC 日期都会留下数字痕迹：两路量子脉冲和两路太阳风测量。这是某一天的封存记录。',
      coefficient:'系数', noCoefficient:'尚无已封存的每日系数', waitingSeal:'等待首次每日封存',
      mailSubject:'TimeLineStamp — 读数差异', mailDay:'UTC 日期', mailRemembered:'我记得的数字', mailShown:'页面当前显示的数字', mailWhen:'发现差异的时间',
      good:'● 数据完整', partial:'● 数据不完整', noQuantum:'● 量子数据不可用',
      initial:'初始快照', initialState:'已记录 · 数据不完整', initialIntro:'根据目前已采集的测量值生成的初始指纹。这份固定快照只覆盖 UTC 日期的一部分；首个每日系数将另行封存。',
      initialLock:'初始快照 · 非每日记录', initialStreams:'此固定初始快照包含的测量值。首个完整 UTC 日期的数据采集仍在继续。', initialMail:'记录类型：初始不完整快照',
      initialNumber:'初始快照的简短标记', dailyNumber:'每日记录的简短标记', initialPeriod:'UTC 日期的部分时段', initialInstrument:'TS-01 / 初始快照', dailyInstrument:'TS-01 / 每日系数',
      initialUpdated:'初始快照已发布',
    },
  };
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
  function nextSeal(firstDay) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(firstDay || '')) return null;
    const earliest = new Date(`${firstDay}T00:15:00Z`);
    earliest.setUTCDate(earliest.getUTCDate() + 1);
    const now = new Date();
    const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 15));
    if (now >= next) next.setUTCDate(next.getUTCDate() + 1);
    return next > earliest ? next : earliest;
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
  function renderStreams(data, record, isInitial) {
    const container = $('streams');
    container.replaceChildren();
    put('streams-description', isInitial ? t().initialStreams : record ? t().shown : t().today);
    sources.forEach(([key, name, expected, subtitle], index) => {
      const raw = record ? record.counts?.[key]?.received : data.progress?.[key]?.count;
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
    const stale = valid && Date.now() - published.getTime() > 3*3600_000;
    put('live-label', failed ? word.unavailable : !valid ? snapshot ? word.waiting : word.connecting : stale ? word.delayed : current ? word.updated : isInitial ? word.initialUpdated : word.waiting);
    put('last-published', valid ? `${word.published}: ${utcStamp(data.published_at)}` : word.noSnapshot);
    const day = record?.day || data.first_full_day || '';
    const shownDay = dateLabel(day);
    put('record-node', `${word.record} ${day || '—'} / UTC`);
    put('rail-status', `${word.day}: ${shownDay}\nUTC\n${word.state}: ${isInitial ? word.initialState : current ? word.sealed : word.collecting}`);
    $('rail-status').style.whiteSpace = 'pre-line';
    put('day-kicker', isInitial ? `${word.initial} / ${shownDay}` : current ? `${word.daily} / ${shownDay}` : `${word.first} / ${shownDay}`);
    put('page-intro', isInitial ? word.initialIntro : current ? word.introSealed : word.introWaiting);
    put('instrument-label', isInitial ? word.initialInstrument : word.dailyInstrument);
    put('lock-status', isInitial ? `${word.initialLock} · ${utcStamp(initial.created_at)}` : current ? `${word.sealed} · ${utcStamp(current.created_at)}` : word.waitingSeal);
    put('display-day', `${shownDay} · UTC`);
    renderNumber(record?.coefficient);
    put('number-note', isInitial ? word.initialNumber : word.dailyNumber);
    put('quality', isInitial ? word.initialState : current ? current.quality === 'good' ? word.good : current.quality === 'partial' ? word.partial : word.noQuantum : word.collecting);
    renderHash(record?.digest);
    put('period-label', word.period);
    put('period', isInitial ? shownDay : current ? shownDay : data.first_full_day ? `${word.firstDay}: ${shownDay}` : '—');
    put('period-note', isInitial ? `${word.initialPeriod}: ${utcStamp(initial.period_start)} – ${utcStamp(initial.created_at)}` : '00:00–24:00 UTC');
    put('next-lock-label', word.next);
    const seal = nextSeal(data.first_full_day);
    put('next-lock', seal ? utcStamp(seal.toISOString()) : '—');
    put('next-lock-note', word.nextNote);
    put('quantum-label', word.quantum);
    const nist = Number(record?.counts?.nist?.received ?? data.progress?.nist?.count ?? 0);
    const nqsn = Number(record?.counts?.nqsn?.received ?? data.progress?.nqsn?.count ?? 0);
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
        fetch(`./data/initial.json?t=${Date.now()}`, {cache:'no-store'}),
      ]);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.format !== 'timelinestamp-status-v1') throw new Error('Unsupported status format');
      snapshot = data;
      if (initialResponse.ok) {
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
  render();
  refresh();
  setInterval(refresh, 5*60_000);
})();
