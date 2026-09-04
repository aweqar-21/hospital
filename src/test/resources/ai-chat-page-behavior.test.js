'use strict';

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const pagePath = process.argv[2];
const page = fs.readFileSync(pagePath, 'utf8');
const scriptMatch = page.match(/<script>\s*([\s\S]*?)\s*<\/script>/);
assert(scriptMatch, 'embedded page script should exist');

class Element {
  constructor(id) {
    this.id = id;
    this.children = [];
    this.listeners = {};
    this.disabled = false;
    this.value = '';
    this.textContent = '';
    this.className = '';
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.focused = false;
    this.selected = false;
    this.firstChild = null;
  }

  addEventListener(name, listener) {
    this.listeners[name] = listener;
  }

  appendChild(child) {
    this.children.push(child);
    this.firstChild = this.children[0] || null;
    this.scrollHeight = this.children.length;
  }

  removeChild(child) {
    this.children.splice(this.children.indexOf(child), 1);
    this.firstChild = this.children[0] || null;
  }

  focus() {
    this.focused = true;
  }

  select() {
    this.selected = true;
  }
}

function createStorage(values, options) {
  const data = Object.assign({}, values);
  const operations = [];
  const blocked = options && options.blocked;
  function fail() {
    if (blocked) throw new Error('storage unavailable');
  }
  return {
    operations,
    getItem(key) { fail(); operations.push(['get', key]); return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null; },
    setItem(key, value) { fail(); operations.push(['set', key, String(value)]); data[key] = String(value); },
    removeItem(key) { fail(); operations.push(['remove', key]); delete data[key]; },
    value(key) { return data[key]; }
  };
}

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, text: () => Promise.resolve(body) };
}

function createApp(options) {
  const elements = {
    messages: new Element('messages'),
    'chat-form': new Element('chat-form'),
    message: new Element('message'),
    send: new Element('send'),
    'new-session': new Element('new-session'),
    status: new Element('status')
  };
  const storage = createStorage(options.storage || {}, options.storageOptions);
  const calls = [];
  const timers = { scheduled: [], cleared: [] };
  let nextTimerId = 1;
  const fetchImpl = options.fetch || (() => Promise.resolve(response(200, JSON.stringify({ code: 200, data: { session_id: 'session-1', reply: 'ok' } }))));
  class AbortController {
    constructor() { this.signal = { aborted: false, abortHandlers: [] }; }
    abort() {
      this.aborted = true;
      this.signal.aborted = true;
      this.signal.abortHandlers.slice().forEach(handler => handler());
    }
  }
  const window = {
    location: { pathname: options.path || '/hospital/ai-chat.html' },
    localStorage: storage,
    AbortController,
    setTimeout(callback, delay) {
      const id = nextTimerId++;
      timers.scheduled.push({ id, callback, delay });
      return id;
    },
    clearTimeout(id) { timers.cleared.push(id); },
    fetch(url, request) { calls.push({ url, request }); return fetchImpl(url, request); }
  };
  const document = {
    getElementById(id) { return elements[id]; },
    createElement() { return new Element('dynamic'); }
  };
  vm.runInNewContext(scriptMatch[1], { window, document, JSON, Error, Promise, console, AbortController });
  return { elements, storage, calls, timers, window };
}

async function settle() {
  for (let index = 0; index < 8; index++) await Promise.resolve();
}

function submit(app, value) {
  app.elements.message.value = value;
  app.elements['chat-form'].listeners.submit({ preventDefault() {} });
}

function textMessages(app) {
  return app.elements.messages.children.map(item => item.textContent);
}

async function run() {
  let app = createApp({
    storage: { token: 'raw-token' },
    fetch: () => Promise.resolve(response(200, JSON.stringify({ code: 200, data: { session_id: 'saved-session', reply: 'first reply' } })))
  });
  submit(app, 'first turn');
  await settle();
  assert.strictEqual(app.calls[0].url, '/hospital/ai/chat');
  assert.deepStrictEqual(JSON.parse(app.calls[0].request.body), { message: 'first turn' });
  assert.strictEqual(app.calls[0].request.headers.Authorization, 'Bearer raw-token');
  assert.strictEqual(app.storage.value('hospitalAiSessionId'), 'saved-session');
  assert.deepStrictEqual(app.storage.operations.filter(item => item[0] === 'set').map(item => item[1]), ['hospitalAiSessionId']);
  assert.strictEqual(textMessages(app).includes('first reply'), true);
  assert.deepStrictEqual(app.timers.cleared, [app.timers.scheduled[0].id], 'successful request should clear its timer');

  submit(app, 'second turn');
  await settle();
  assert.deepStrictEqual(JSON.parse(app.calls[1].request.body), { message: 'second turn', session_id: 'saved-session' });

  let resolvePending;
  app = createApp({ fetch: () => new Promise(resolve => { resolvePending = resolve; }) });
  submit(app, 'once only');
  submit(app, 'should not send');
  assert.strictEqual(app.calls.length, 1);
  resolvePending(response(200, JSON.stringify({ code: 200, data: { session_id: 's', reply: 'done' } })));
  await settle();

  app = createApp({
    storageOptions: { blocked: true },
    fetch: () => Promise.resolve(response(200, JSON.stringify({ code: 200, data: { session_id: 'ignored', reply: '<img src=x onerror=alert(1)>' } })))
  });
  submit(app, 'works without storage');
  await settle();
  assert.strictEqual(app.calls.length, 1);
  assert.strictEqual(textMessages(app).includes('<img src=x onerror=alert(1)>'), true);
  assert.strictEqual(page.includes('innerHTML'), false);
  assert.doesNotThrow(() => app.elements['new-session'].listeners.click());
  assert.strictEqual(app.elements.message.focused, true);

  for (const failure of [
    { name: 'http 503', fetch: () => Promise.resolve(response(503, '')) },
    { name: 'network', fetch: () => Promise.reject(new TypeError('offline')) },
    { name: 'abort', fetch: () => Promise.reject({ name: 'AbortError' }) },
    { name: 'malformed', fetch: () => Promise.resolve(response(200, 'not-json')) }
  ]) {
    app = createApp({ fetch: failure.fetch });
    submit(app, 'retry ' + failure.name);
    await settle();
    assert.strictEqual(app.elements.message.value, 'retry ' + failure.name, failure.name + ' should restore input');
    assert.strictEqual(app.elements.message.focused, true, failure.name + ' should focus input');
    assert.strictEqual(app.elements.message.selected, true, failure.name + ' should select input');
    const publicMessage = textMessages(app).slice(-1)[0];
    assert.strictEqual(/offline|AbortError|not-json|TypeError/.test(publicMessage), false, failure.name + ' should not expose internals');
    assert.strictEqual(/服务|网络|超时/.test(publicMessage), true, failure.name + ' should show a retryable public error');
    assert.deepStrictEqual(app.timers.cleared, [app.timers.scheduled[0].id], failure.name + ' should clear its timer');
  }

  app = createApp({ fetch: () => Promise.resolve(response(200, JSON.stringify({ code: 200, data: { session_id: 's', reply: 'keyboard' } }))) });
  app.elements.message.value = 'enter sends';
  app.elements.message.listeners.keydown({ key: 'Enter', shiftKey: false, isComposing: false, keyCode: 13, preventDefault() {} });
  await settle();
  assert.strictEqual(app.calls.length, 1);
  app.elements.message.value = 'shift stays';
  app.elements.message.listeners.keydown({ key: 'Enter', shiftKey: true, isComposing: false, keyCode: 13, preventDefault() { throw new Error('shift should not prevent'); } });
  app.elements.message.listeners.keydown({ key: 'Enter', shiftKey: false, isComposing: true, keyCode: 13, preventDefault() { throw new Error('composition should not prevent'); } });
  app.elements.message.listeners.keydown({ key: 'Enter', shiftKey: false, isComposing: false, keyCode: 229, preventDefault() { throw new Error('229 should not prevent'); } });
  assert.strictEqual(app.calls.length, 1);

  app = createApp({
    fetch: (url, request) => new Promise((resolve, reject) => {
      assert(request.signal, 'timeout request should pass an abort signal');
      request.signal.abortHandlers.push(() => reject({ name: 'AbortError' }));
    })
  });
  submit(app, 'timeout retry');
  assert.strictEqual(app.timers.scheduled.length, 1, 'request should schedule a timeout');
  const timeout = app.timers.scheduled[0];
  timeout.callback();
  await settle();
  assert.strictEqual(app.calls[0].request.signal.aborted, true, 'timeout should abort the active request');
  assert.strictEqual(app.elements.message.value, 'timeout retry');
  assert.strictEqual(app.elements.message.focused, true);
  assert.strictEqual(app.elements.message.selected, true);
  assert.strictEqual(app.elements.message.disabled, false);
  assert.strictEqual(app.elements.send.disabled, false);
  assert.strictEqual(textMessages(app).slice(-1)[0].indexOf('超时') >= 0, true);
  assert.deepStrictEqual(app.timers.cleared, [timeout.id], 'timeout should be cleared after abort handling');
}

run().then(() => {
  process.stdout.write('AI chat page behavior assertions passed.\n');
}).catch(error => {
  process.stderr.write((error && error.stack) || String(error));
  process.exitCode = 1;
});
