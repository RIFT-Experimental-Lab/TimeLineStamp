const $ = (id) => document.getElementById(id);
const qualityText = {good: 'ПОЛНЫЕ ДАННЫЕ', partial: 'НЕПОЛНЫЕ ДАННЫЕ', unavailable: 'НЕТ КВАНТОВЫХ ДАННЫХ'};
const sourceTypes = {nist: 'QUANTUM · PHOTON', nqsn: 'QUANTUM · VACUUM', noaa_mag: 'SOLAR WIND · MAG', noaa_wind: 'SOLAR WIND · PLASMA'};

function appendText(parent, tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.appendChild(element);
  return element;
}

function renderMeter(value) {
  const meter = $('meter');
  meter.replaceChildren();
  meter.classList.toggle('waiting', !value);
  if (!value) { meter.textContent = '—.——————'; return; }
  for (const char of value) appendText(meter, 'span', char, char === '.' ? 'decimal' : 'digit');
  meter.setAttribute('aria-label', `Коэффициент ${value}`);
}

function formatDate(day) {
  if (!day) return '—';
  const [year, month, date] = day.split('-');
  return `${date}.${month}.${year}`;
}

function nextLock(nowString, firstFullDay, hasCurrent) {
  const now = new Date(nowString);
  const target = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 15));
  if (now >= target) target.setUTCDate(target.getUTCDate() + 1);
  if (!hasCurrent) {
    const first = new Date(`${firstFullDay}T00:15:00Z`);
    first.setUTCDate(first.getUTCDate() + 1);
    if (target < first) target.setTime(first.getTime());
  }
  return new Intl.DateTimeFormat('ru-RU', {timeZone:'Europe/Moscow', day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'}).format(target) + ' МСК';
}

function renderSources(data) {
  const container = $('sources');
  container.replaceChildren();
  for (const source of ['nist', 'nqsn', 'noaa_mag', 'noaa_wind']) {
    const progress = data.progress[source] || {count:0, last_received:null};
    const card = appendText(container, 'article', '', 'source');
    appendText(card, 'div', data.source_names[source], 'source-name');
    appendText(card, 'div', sourceTypes[source], 'source-type');
    const stat = appendText(card, 'div', '', 'source-stat');
    appendText(stat, 'span', 'Сегодня, UTC');
    appendText(stat, 'strong', String(progress.count));
    appendText(card, 'div', progress.last_received ? `Получено ${progress.last_received.slice(11,16)} UTC` : 'Пока нет данных', 'source-time');
  }
}

function renderHistory(items) {
  const body = $('history');
  body.replaceChildren();
  if (!items.length) {
    const row = appendText(body, 'tr', '');
    const cell = appendText(row, 'td', 'Записи появятся после первых полных суток.', 'empty');
    cell.colSpan = 4;
    return;
  }
  for (const item of items) {
    const row = appendText(body, 'tr', '');
    appendText(row, 'td', formatDate(item.day));
    appendText(row, 'td', item.coefficient || '—', 'coefficient-cell');
    appendText(row, 'td', qualityText[item.quality], `quality-${item.quality}`);
    const hash = appendText(row, 'td', item.digest.slice(0,16) + '…', 'hash-cell');
    hash.title = item.digest;
  }
}

function render(data) {
  $('live-label').textContent = 'СБОР АКТИВЕН';
  document.querySelector('.live').classList.remove('offline');
  const current = data.current;
  renderMeter(current?.coefficient || null);
  $('day-label').textContent = current ? `${formatDate(current.day)} · UTC` : 'ПЕРВЫЙ ПЕРИОД';
  $('period').textContent = current ? `${formatDate(current.day)} · 00:00–24:00 UTC` : `С ${formatDate(data.first_full_day)} · UTC`;
  $('next-lock').textContent = nextLock(data.now_utc, data.first_full_day, !!current);
  $('digest-short').textContent = current ? current.digest.slice(0,20) + '…' : '—';
  $('digest-short').title = current?.digest || '';
  $('quality').textContent = current ? qualityText[current.quality] : 'ОЖИДАНИЕ';
  $('quality').className = current ? `quality-${current.quality}` : '';
  $('meter-note').textContent = current ? `Зафиксировано ${current.created_at.slice(0,16).replace('T',' ')} UTC` : 'Ожидание первого полного периода измерений';
  renderSources(data);
  renderHistory(data.history);
}

async function refresh() {
  try {
    const response = await fetch('/api/status', {cache:'no-store'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    $('live-label').textContent = 'НЕТ СОЕДИНЕНИЯ';
    document.querySelector('.live').classList.add('offline');
    console.error(error);
  }
}

refresh();
setInterval(refresh, 30_000);
