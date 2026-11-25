import {fmt} from './ui.js';

const factoryId = 1;
const deviceId = 3;
const deviceCode = 'EQ-03';
const buildRoot = '/factory-3d/FactoryCampus';
const buildFile = buildRoot + '/Build/FactoryCampus';
const pollInterval = 3000;
const actionKeys = {'prepare-defense': 'prepare', fault: 'fault', recover: 'recover', resume: 'resume', stop: 'stop'};
let loaderPromise;
let unityLifecycle = Promise.resolve();

function unavailable(message) {
  return {view: {valid: false, running: false}, expiresIn: 0, message};
}

export function projectWorkshopView(snapshot, factory, elapsed = 0) {
  if (factory !== factoryId) return unavailable('三维演示使用星铸工厂的装配三线');
  const {demo, device, readings} = snapshot || {};
  if (!demo?.running) return unavailable('等待准备答辩场景');
  if (demo.mode !== 'defense') return unavailable('当前为普通演示，停止后可准备答辩场景');
  if (demo.factory_id !== factory || demo.device_id !== deviceId || device?.id !== deviceId ||
      device.factory_id !== factory || device.code !== deviceCode) {
    return unavailable('本轮设备与三维工位 EQ-03 不匹配');
  }
  const order = demo.order;
  if (!order || order.id !== demo.order_id || order.factory_id !== factory || order.device_id !== deviceId ||
      !order.code || !order.batch || !Number.isInteger(order.completed) || !Number.isInteger(order.quantity) ||
      order.completed < 0 || order.quantity < 1 || order.completed > order.quantity) {
    return unavailable('等待核对当前工单与批次');
  }
  if (!readings?.length || readings.at(-1).device_id !== deviceId || !device.simulated) {
    return unavailable('等待本轮设备采集');
  }
  const expiresIn = (device.freshness_limit - device.age_seconds) * 1000 - elapsed;
  if (!device.fresh || !Number.isFinite(device.age_seconds) || !Number.isFinite(expiresIn) || expiresIn <= 0 ||
      ![device.temperature, device.pressure, device.vibration].every(Number.isFinite)) {
    return unavailable('设备采集已过期，三维画面已暂停');
  }
  const running = demo.phase === 'producing' && !demo.resume_required && device.status === '运行' && order.status === '生产中';
  return {
    view: {
      valid: true, runId: demo.id, deviceId, orderId: order.id, deviceCode, orderCode: order.code, batch: order.batch,
      completed: order.completed, quantity: order.quantity, phase: demo.phase, running,
      temperature: device.temperature, pressure: device.pressure, vibration: device.vibration, status: device.status,
    },
    expiresIn,
    message: demo.phase_label || device.status,
  };
}

export function workshopControls(snapshot, view, role) {
  const canControl = Boolean(snapshot) && ['admin', 'engineer'].includes(role);
  const active = Boolean(snapshot?.demo?.running);
  const linked = canControl && active && view.valid;
  return {
    prepare: canControl && !active,
    fault: linked && view.running,
    recover: linked && view.phase === 'fault',
    resume: linked && view.phase === 'awaiting_resume',
    stop: canControl && active,
  };
}

const launchButton = '<button type="button" class="btn primary" data-workshop-open data-live-preserve>进入三维车间</button>';

export function workshop3DLauncher(factory) {
  return Number(factory) === factoryId ? launchButton : '';
}

export function renderWorkshop3D(factory, role) {
  if (Number(factory) !== factoryId) return '';
  const showActions = ['admin', 'engineer'].includes(role);
  return `<section class="card workshop-3d mb16" data-live-preserve data-open="false" data-scene="idle" hidden aria-labelledby="workshop-3d-title">
    <header class="workshop-3d-head">
      <h2 id="workshop-3d-title">装配三线</h2>
      <button class="btn ghost small" type="button" data-workshop-close>返回设备示意图</button>
    </header>
    <div class="workshop-3d-grid">
      <div class="workshop-3d-viewport">
        <canvas id="workshop-unity-canvas" tabindex="0" aria-label="装配三线三维车间" hidden></canvas>
        <p data-workshop-load role="status">正在加载三维车间…</p>
      </div>
      <div class="workshop-3d-details">
        <p data-workshop-status role="status">正在读取演示工况…</p>
        <dl class="workshop-3d-facts">
          <div><dt>设备</dt><dd data-workshop-device>—</dd></div>
          <div><dt>工单</dt><dd data-workshop-order>—</dd></div>
          <div><dt>批次</dt><dd data-workshop-batch>—</dd></div>
          <div><dt>当前批次报工</dt><dd data-workshop-output>—</dd></div>
          <div><dt>温度</dt><dd data-workshop-temperature>—</dd></div>
        </dl>
        ${showActions ? `<div class="workshop-3d-actions" aria-label="答辩演示控制">
          <button type="button" class="btn primary" data-workshop-action="prepare-defense" disabled>准备答辩场景</button>
          <button type="button" class="btn" data-workshop-action="fault" disabled>注入温控故障</button>
          <button type="button" class="btn" data-workshop-action="recover" disabled>恢复温控</button>
          <button type="button" class="btn primary" data-workshop-action="resume" hidden disabled>确认复产</button>
          <button type="button" class="btn ghost" data-workshop-action="stop" disabled>停止演示</button>
        </div><p class="workshop-3d-error" data-workshop-error role="alert" hidden></p>` : ''}
        <a class="workshop-3d-link" href="#monitor" data-page="monitor">生产监控大屏 →</a>
      </div>
    </div>
  </section>`;
}

function loadUnity(canvas, progress) {
  if (!loaderPromise) {
    loaderPromise = new Promise((resolve, reject) => {
      const loader = document.createElement('script');
      loader.src = buildFile + '.loader.js';
      const timeout = setTimeout(() => fail('Unity 加载器响应超时'), 15000);
      function detach() {
        clearTimeout(timeout);
        loader.onload = loader.onerror = null;
        loader.remove();
      }
      function fail(message) { detach(); reject(new Error(message)); }
      loader.onload = () => {
        detach();
        if (typeof window.createUnityInstance === 'function') resolve(window.createUnityInstance);
        else reject(new Error('Unity 加载器无效'));
      };
      loader.onerror = () => fail('未找到浏览器三维构建');
      document.head.append(loader);
    }).catch(error => { loaderPromise = undefined; throw error; });
  }
  return loaderPromise.then(create => create(canvas, {
    dataUrl: buildFile + '.data', frameworkUrl: buildFile + '.framework.js', codeUrl: buildFile + '.wasm',
    streamingAssetsUrl: buildRoot + '/StreamingAssets', companyName: '全景可视化数字工厂', productName: '三维车间',
    productVersion: '1.0', devicePixelRatio: Math.min(window.devicePixelRatio || 1, 1.5),
    showBanner(message, kind) { if (kind === 'error') console.error(message); },
  }, progress));
}

async function withDeadline(task, duration, message) {
  let timer;
  const deadline = new Promise((resolve, reject) => { timer = setTimeout(() => reject(new Error(message)), duration); });
  try { return await Promise.race([task, deadline]); }
  finally { clearTimeout(timer); }
}

async function quitUnity(instance) {
  try { await withDeadline(instance.Quit(), 5000, '三维实例结束超时'); }
  catch (error) { console.warn('三维实例结束失败', error); }
}

export function mountWorkshop3D(parent, factory, role, api) {
  const stage = parent.querySelector('.workshop-3d');
  if (!stage) return () => {};
  const openButton = parent.querySelector('[data-workshop-open]');
  const closeButton = stage.querySelector('[data-workshop-close]');
  const loadStatus = stage.querySelector('[data-workshop-load]');
  const status = stage.querySelector('[data-workshop-status]');
  const errorStatus = stage.querySelector('[data-workshop-error]');
  const buttons = [...stage.querySelectorAll('[data-workshop-action]')];
  const fields = Object.fromEntries(['device', 'order', 'batch', 'output', 'temperature'].map(name =>
    [name, stage.querySelector('[data-workshop-' + name + ']')]));
  let canvas = stage.querySelector('canvas'), unity, snapshot, pollTimer, expiryTimer;
  const canvasTemplate = canvas.cloneNode(false);
  let opened = false, disposed = false, pending = false, generation = 0, request = 0;
  let state = unavailable('正在读取演示工况…');

  function update() {
    const {view, message} = state;
    if (status.textContent !== message) status.textContent = message;
    stage.dataset.phase = view.valid ? view.phase : 'unavailable';
    stage.dataset.motion = view.running ? 'running' : 'stopped';
    fields.device.textContent = view.deviceCode || '—';
    fields.order.textContent = view.orderCode || '—';
    fields.batch.textContent = view.batch || '—';
    fields.output.textContent = view.valid ? fmt(view.completed) + ' / ' + fmt(view.quantity) + ' 件' : '—';
    fields.temperature.textContent = view.valid ? view.temperature.toFixed(1) + ' ℃' : '—';
    const actions = workshopControls(snapshot, view, role);
    for (const button of buttons) {
      const action = button.dataset.workshopAction;
      button.disabled = pending || !actions[actionKeys[action]];
      if (action === 'resume') button.hidden = view.phase !== 'awaiting_resume';
      if (action === 'recover') {
        button.hidden = view.phase === 'awaiting_resume';
        button.textContent = view.phase === 'cooling' ? '降温观察中' : '恢复温控';
      }
    }
    if (unity) {
      try { unity.SendMessage('FactoryWebPresentation', 'ApplySnapshot', JSON.stringify(view)); }
      catch { showSceneFailure(); }
    }
  }

  function releaseUnity() {
    const instance = unity;
    unity = undefined;
    if (instance) unityLifecycle = unityLifecycle.then(() => quitUnity(instance));
  }

  function showSceneFailure() {
    stage.dataset.scene = 'error';
    canvas.hidden = true;
    loadStatus.textContent = '三维车间加载失败，可使用下方设备示意图或监控大屏';
    loadStatus.hidden = false;
    releaseUnity();
  }

  function contextLost(event) {
    if (event.target === canvas && unity) showSceneFailure();
  }

  async function read(expectedGeneration) {
    const version = ++request;
    const started = performance.now();
    let next;
    try { next = await api('/live?factory_id=' + factory + '&device_id=' + deviceId, undefined, {timeout: 6500}); }
    catch { /* Connection status is shown below. */ }
    if (disposed || !opened || generation !== expectedGeneration || version !== request) return;
    snapshot = next;
    state = next ? projectWorkshopView(next, factory, performance.now() - started) : unavailable('连接中断，三维画面已暂停');
    clearTimeout(expiryTimer);
    if (state.view.valid) expiryTimer = setTimeout(() => {
      state = unavailable('设备采集已过期，三维画面已暂停');
      update();
    }, state.expiresIn);
    update();
  }

  async function poll(expectedGeneration) {
    await read(expectedGeneration);
    if (opened && !disposed && generation === expectedGeneration) {
      pollTimer = setTimeout(() => poll(expectedGeneration), pollInterval);
    }
  }

  function open() {
    if (opened || disposed) return;
    const attempt = ++generation;
    opened = true;
    stage.hidden = false;
    stage.dataset.open = 'true';
    stage.dataset.scene = 'loading';
    openButton.disabled = true;
    loadStatus.textContent = '正在加载三维车间…';
    loadStatus.hidden = false;
    state = unavailable('正在读取演示工况…');
    update();
    poll(attempt);
    const active = () => !disposed && opened && generation === attempt;
    const boot = unityLifecycle.then(async () => {
      if (!active()) return;
      canvas.hidden = false;
      let timedOut = false;
      const loading = loadUnity(canvas, progress => {
        if (active()) loadStatus.textContent = '正在加载三维车间… ' + Math.round(progress * 100) + '%';
      }).then(async instance => {
        if (timedOut) await quitUnity(instance);
        return instance;
      });
      const candidate = await withDeadline(loading, 90000, '三维场景启动超时').catch(error => {
        timedOut = true;
        throw error;
      });
      if (!active()) { await quitUnity(candidate); return; }
      unity = candidate;
      stage.dataset.scene = 'ready';
      loadStatus.hidden = true;
      update();
    }).catch(() => { if (active()) showSceneFailure(); });
    unityLifecycle = boot;
  }

  function close() {
    if (!opened) return;
    opened = false;
    generation++;
    clearTimeout(pollTimer);
    clearTimeout(expiryTimer);
    state = unavailable('三维车间已关闭');
    update();
    snapshot = undefined;
    pending = false;
    if (errorStatus) errorStatus.hidden = true;
    stage.hidden = true;
    stage.dataset.open = 'false';
    stage.dataset.scene = 'idle';
    openButton.disabled = false;
    releaseUnity();
    const replacement = canvasTemplate.cloneNode(false);
    canvas.replaceWith(replacement);
    canvas = replacement;
  }

  async function control(event) {
    const button = event.target.closest('[data-workshop-action]');
    if (!button || button.disabled || !opened || pending) return;
    const action = button.dataset.workshopAction;
    const body = {factory_id: factory, action};
    if (action !== 'prepare-defense') body.run_id = snapshot.demo.id;
    const attempt = generation;
    pending = true;
    errorStatus.hidden = true;
    update();
    try {
      await api('/live/demo', body);
      if (generation === attempt && !disposed) await read(attempt);
    } catch (error) {
      if (generation === attempt && !disposed) {
        errorStatus.textContent = error.message;
        errorStatus.hidden = false;
      }
    } finally {
      if (generation === attempt && !disposed) { pending = false; update(); }
    }
  }

  openButton.addEventListener('click', open);
  closeButton.addEventListener('click', close);
  stage.addEventListener('click', control);
  stage.addEventListener('webglcontextlost', contextLost, true);
  return () => {
    disposed = true;
    close();
    openButton.removeEventListener('click', open);
    closeButton.removeEventListener('click', close);
    stage.removeEventListener('click', control);
    stage.removeEventListener('webglcontextlost', contextLost, true);
  };
}
