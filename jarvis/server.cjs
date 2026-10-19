const http = require('node:http');
const fs = require('node:fs/promises');
const path = require('node:path');
const { execFile } = require('node:child_process');
const port = 4317;
const home = `http://127.0.0.1:${port}`;
const providers = {
  weather: 'https://api.open-meteo.com/v1/forecast',
  city: 'https://geocoding-api.open-meteo.com/v1/search',
  currency: 'https://www.cbr-xml-daily.ru/daily_json.js',
  search: 'https://ru.wikipedia.org/w/api.php'
};
async function body(req) {
  let value = '';
  for await (const chunk of req) {
    value += chunk;
    if (value.length > 20000) throw new Error('Слишком большой запрос');
  }
  return JSON.parse(value);
}
function openTarget(target) {
  if (process.platform !== 'win32') throw new Error('Запуск программ в этой версии поддерживается в Windows.');
  const escaped = target.replace(/'/g, "''");
  const script = `Start-Process -FilePath '${escaped}' -ErrorAction Stop`;
  return new Promise((resolve, reject) => execFile('powershell.exe', [
    '-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(script, 'utf16le').toString('base64')
  ], { windowsHide: true, timeout: 15000 }, (error) => error ? reject(new Error('Windows не смогла открыть указанный путь.')) : resolve()));
}
const server = http.createServer(async (req, res) => {
  function json(value, status = 200) {
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(value));
  }
  try {
    if (req.headers.host !== `127.0.0.1:${port}`) return json({ error: 'Недопустимый адрес' }, 403);
    const url = new URL(req.url, home);
    if (req.method === 'GET' && url.pathname === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'X-Frame-Options': 'DENY', 'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'; base-uri 'none'" });
      return res.end(await fs.readFile(path.join(__dirname, 'index.html')));
    }
    if (url.pathname.startsWith('/api/')) {
      if (req.headers['x-control-panel'] !== '1' || (req.headers.origin && req.headers.origin !== home)) return json({ error: 'Запрос отклонён' }, 403);
      if (url.pathname === '/api/open' && req.method === 'POST') {
        const { target } = await body(req);
        if (typeof target !== 'string' || !target.trim() || /[\r\n\x00]/.test(target)) throw new Error('Некорректный путь');
        if (/^https?:\/\//i.test(target)) {
          const address = new URL(target);
          if (address.username || address.password) throw new Error('Ссылка с паролем не поддерживается');
        } else {
          if (!path.win32.isAbsolute(target)) throw new Error('Укажите полный путь к файлу');
          await fs.access(target);
        }
        await openTarget(target);
        return json({ ok: true });
      }
      if (url.pathname === '/api/info' && req.method === 'GET') {
        const provider = url.searchParams.get('provider');
        if (!Object.hasOwn(providers, provider)) throw new Error('Неизвестный источник');
        const upstream = new URL(providers[provider]);
        for (const [key, value] of url.searchParams) if (key !== 'provider') upstream.searchParams.set(key, value);
        const result = await fetch(upstream, { signal: AbortSignal.timeout(15000), headers: { 'User-Agent': 'LocalJarvis/1.0' } });
        if (!result.ok) throw new Error('Источник временно недоступен');
        return json(await result.json());
      }
    }
    json({ error: 'Не найдено' }, 404);
  } catch (error) { json({ error: error.message === 'fetch failed' ? 'Не удалось связаться с источником данных. Проверьте интернет или повторите запрос позже.' : error.message }, 400); }
});
server.on('error', error => { console.error(error.message); process.exitCode = 1; });
server.listen(port, '127.0.0.1', () => {
  console.log(`Jarvis: ${home}\nОткройте этот адрес в Google Chrome или Microsoft Edge.\nНе закрывайте это окно, пока используете панель.`);
});
