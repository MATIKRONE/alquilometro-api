const main = document.querySelector('#main');
const account = document.querySelector('#account');
const dialog = document.querySelector('#dialog');
const dialogBody = document.querySelector('#dialog-body');
let token = sessionStorage.getItem('alquilometro-token');
let user;
let routeVersion = 0;
let filters = new URLSearchParams();
const canPublish = () => ['INMOBILIARIA', 'ADMIN'].includes(user?.rol);

const h = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[c]);
const number = (value) => Number(value).toLocaleString('es-AR', { maximumFractionDigits: 2 });
const money = (value) => value ? new Intl.NumberFormat('es-AR', {
  style: 'currency', currency: value.moneda, maximumFractionDigits: 2, minimumFractionDigits: 0,
}).format(Number(value.monto)) : '—';
const pct = (value) => value == null ? '—' : number(value) + '%';
const date = (value) => value ? value.slice(0, 10).split('-').reverse().join('/') : '—';
const labels = {
  alquiler: 'Alquiler', expensas: 'Expensas', abl: 'ABL', deposito: 'Depósito',
  seguro_caucion: 'Seguro de caución', seguro_caucion_prorrateado: 'Seguro prorrateado',
  comision: 'Comisión', primer_mes: 'Primer mes', otros_gastos_entrada: 'Otros gastos de entrada',
  duracion_contrato_meses: 'Duración del contrato',
};
const label = (key) => labels[key] ?? key.replaceAll('_', ' ');
const note = (message, type = '') => `<p class="notice ${type}" role="status">${h(message)}</p>`;
const missing = (keys) => keys?.length ? note('Datos faltantes: ' + keys.map(label).join(', '), 'warn') : '';
const result = (element, html) => { element.innerHTML = html; };

async function api(path, method = 'GET', body) {
  const headers = {};
  if (token) headers.Authorization = 'Bearer ' + token;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api' + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && token) setUser(null);
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.loc.at(-1) + ': ' + item.msg).join(' · ')
      : data.detail;
    throw new Error(detail || 'La API devolvió un error (' + response.status + ').');
  }
  return data;
}

function setUser(profile, accessToken = null) {
  user = profile;
  token = accessToken;
  if (token) sessionStorage.setItem('alquilometro-token', token);
  else sessionStorage.removeItem('alquilometro-token');
  account.textContent = profile ? profile.nombre : 'Ingresar';
  document.querySelector('#publish-link').hidden = !canPublish();
}

function submit(form, handler) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = event.submitter;
    const output = form.querySelector('[data-output]');
    if (button) button.disabled = true;
    if (output) result(output, '');
    try {
      await handler(new FormData(form), output);
    } catch (error) {
      if (output) result(output, note(error.message, 'error'));
    } finally {
      if (button) button.disabled = false;
    }
  });
}

function input(title, name, attrs = '') {
  return `<label>${title}<input name="${name}" ${attrs}></label>`;
}
function select(title, name, choices) {
  return `<label>${title}<select name="${name}">${choices.map(([value, text]) =>
    `<option value="${value}">${text}</option>`).join('')}</select></label>`;
}
const currency = [['ARS', 'ARS'], ['USD', 'USD']];
const submitButton = (text) => `<div class="actions"><button class="btn" type="submit">${text}</button></div><div class="full" data-output aria-live="polite"></div>`;
const metadata = (p) => [
  p.ambientes + (p.ambientes === 1 ? ' ambiente' : ' ambientes'),
  p.metros_cuadrados && number(p.metros_cuadrados) + ' m²',
  p.permite_mascotas === true ? 'Acepta mascotas' : null,
].filter(Boolean).join(' · ');
const adjustment = (p) => p.tipo_ajuste === 'INDICE' ? p.serie_codigo :
  p.tipo_ajuste === 'FIJO' ? 'Fijo ' + pct(p.tasa_ajuste) : 'Ajuste sin informar';
const query = (data) => new URLSearchParams([...data].filter(([, value]) => value !== ''));
const table = (headers, rows) => `<div class="table-wrap"><table><thead><tr>${headers.map((s) =>
  `<th scope="col">${s}</th>`).join('')}</tr></thead><tbody>${rows.map((row) =>
  '<tr>' + row.map((cell) => '<td>' + h(cell) + '</td>').join('') + '</tr>').join('')}</tbody></table></div>`;
const loginPrompt = (text) => `<p>${text}</p><button class="quiet" data-login>Ingresar</button>`;

function openAccount(register = false) {
  if (user) {
    result(dialogBody, `<h2 id="dialog-title">Mi cuenta</h2><p>${h(user.nombre)} · ${h(user.email)}<br>
      <span class="tag">${user.rol === 'INMOBILIARIA' ? 'Inmobiliaria' : user.rol === 'ADMIN' ? 'Administración' : 'Buscador'}</span></p>
      <form id="income-form">${input('Ingreso mensual de referencia', 'monto', `type="number" min="0.01" step="0.01" required value="${h(user.ingreso_referencia?.monto)}"`)}
      ${select('Moneda', 'moneda', currency)}${submitButton('Guardar ingreso')}</form>
      <button class="quiet" id="logout">Cerrar sesión</button>`);
    const form = dialogBody.querySelector('#income-form');
    form.elements.moneda.value = user.ingreso_referencia?.moneda || 'ARS';
    submit(form, async (data) => {
      setUser(await api('/usuarios/me/ingreso-referencia', 'PUT', Object.fromEntries(data)), token);
      dialog.close();
      await route();
    });
    dialogBody.querySelector('#logout').onclick = () => { setUser(null); dialog.close(); route(); };
  } else {
    result(dialogBody, `<h2 id="dialog-title">${register ? 'Crear cuenta' : 'Ingresar'}</h2><form id="login-form">
      ${register ? input('Nombre', 'nombre', 'required maxlength="100" autocomplete="name"') : ''}
      ${register ? select('Tipo de cuenta', 'rol', [['BUSCADOR','Busco alquilar'], ['INMOBILIARIA','Soy una inmobiliaria']]) : ''}
      ${input('Correo', 'email', 'type="email" required autocomplete="email"')}
      <div class="password-field">
        <label for="account-password">Contraseña</label>
        <div class="password-control">
          <input id="account-password" name="password" type="password" required
            ${register ? 'minlength="8"' : ''} autocomplete="${register ? 'new-password' : 'current-password'}">
          <button class="password-toggle" type="button" aria-controls="account-password" aria-label="Mostrar contraseña" title="Mostrar contraseña">
            <span class="password-eye" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      ${submitButton(register ? 'Crear cuenta e ingresar' : 'Ingresar')}</form>
      <button class="quiet" id="toggle-account">${register ? 'Ya tengo cuenta' : 'Crear cuenta'}</button>`);
    const form = dialogBody.querySelector('#login-form');
    const password = form.elements.password;
    const toggle = form.querySelector('.password-toggle');
    toggle.onclick = () => {
      const show = password.type === 'password';
      password.type = show ? 'text' : 'password';
      const label = show ? 'Ocultar contraseña' : 'Mostrar contraseña';
      toggle.setAttribute('aria-label', label);
      toggle.title = label;
    };
    submit(form, async (data) => {
      const credentials = { email: data.get('email'), password: data.get('password') };
      if (register) await api('/auth/registro', 'POST', {
        ...credentials, nombre: data.get('nombre'), rol: data.get('rol'),
      });
      token = (await api('/auth/login', 'POST', credentials)).access_token;
      setUser(await api('/usuarios/me'), token);
      dialog.close();
      await route();
    });
    dialogBody.querySelector('#toggle-account').onclick = () => openAccount(!register);
  }
  if (!dialog.open) dialog.showModal();
}
account.onclick = () => openAccount();
dialog.querySelector('.close').onclick = () => dialog.close();
main.addEventListener('click', (e) => { if (e.target.closest('[data-login]')) openAccount(); });

function listingCard(listing, cost) {
  const p = listing.propiedad;
  return `<article class="card">
    <p class="eyebrow">${h(p.zona)} · ${h(p.tipo)}</p>
    <h3>${h(p.direccion)}</h3><p class="muted meta">${h(metadata(p))}</p>
    <div class="row"><small>Alquiler publicado</small><strong class="money">${h(money(listing.precio_alquiler))}</strong></div>
    <div class="row"><small>Costo mensual informado</small><strong class="money cost">${h(money(cost?.total))}</strong></div>
    <p><span class="tag">${h(adjustment(listing))}</span>${cost?.faltantes.length ? ' <small>Con datos faltantes</small>' : ''}</p>
    <div class="actions"><a class="quiet" href="#publicacion/${listing.id}">Ver costos y proyección</a></div>
  </article>`;
}

async function search(version) {
  result(main, `<section class="hero"><div class="wrap hero-inner">
    <div><p class="eyebrow">Costos de alquiler</p><h1>¿Cuánto cuesta<br><em>vivir acá?</em></h1>
    <p>Compará alquileres por su costo mensual, revisá cuánto necesitás para entrar y proyectá el próximo ajuste.</p></div>
    <aside class="hero-data" id="featured" aria-live="polite"><small>Cargando publicación de ejemplo…</small></aside>
  </div></section>
  <section class="wrap content"><div class="filters">
    <div class="section-head"><h2>Buscar publicaciones</h2></div>
    <form id="filters">
      ${input('Barrio', 'zona', 'placeholder="Ej. Caballito" minlength="2" maxlength="100"')}
      ${input('Ambientes', 'ambientes', 'type="number" min="1" max="10" placeholder="Todos"')}
      ${select('Mascotas', 'permite_mascotas', [['','Indistinto'],['true','Acepta mascotas'],['false','No acepta mascotas']])}
      ${select('Moneda', 'moneda', [['','Todas'], ...currency])}
      <details><summary>Rangos y orden</summary><div class="fields">
        ${input('Garantía', 'tipo_garantia', 'minlength="2"')}
        ${input('Alquiler mínimo', 'alquiler_min', 'type="number" min="0" step="0.01"')}
        ${input('Alquiler máximo', 'alquiler_max', 'type="number" min="0" step="0.01"')}
        ${input('Costo mensual mínimo', 'costo_real_min', 'type="number" min="0" step="0.01"')}
        ${input('Costo mensual máximo', 'costo_real_max', 'type="number" min="0" step="0.01"')}
        ${select('Ordenar por', 'orden', [['','Predeterminado'],['alquiler','Alquiler'],['costo_real','Costo mensual'],['precio_m2','Precio por m²']])}
        ${select('Sentido', 'descendente', [['false','Menor a mayor'],['true','Mayor a menor']])}
        <small class="full">Para filtrar u ordenar montos, elegí una moneda.</small>
      </div></details>
      <div class="actions"><button class="btn">Buscar</button><button class="quiet" type="reset">Limpiar</button></div>
    </form>
  </div><div id="results" aria-live="polite"></div></section>`);
  const form = main.querySelector('#filters');
  const results = main.querySelector('#results');
  const featured = main.querySelector('#featured');
  for (const [key, value] of filters) form.elements[key].value = value;
  if ([...filters].some(([key, value]) => form.elements[key].closest('details') && value !== 'false')) {
    form.querySelector('details').open = true;
  }
  let revision = 0;
  async function load() {
    const current = ++revision;
    result(results, note('Buscando publicaciones…'));
    try {
      const listings = await api('/publicaciones?' + filters);
      const costs = await Promise.allSettled(listings.map((p) => api('/publicaciones/' + p.id + '/costo-real')));
      if (version !== routeVersion || current !== revision) return;
      result(results, `<div class="section-head"><h2>Resultados</h2><small>${listings.length} publicaciones</small></div>` +
        (listings.length ? `<div class="cards">${listings.map((p, i) => listingCard(p, costs[i].value)).join('')}</div>` :
          '<p class="empty">No encontramos publicaciones con esos filtros.</p>'));
      if (costs.some((item) => item.status === 'rejected')) {
        results.insertAdjacentHTML('afterbegin', note('Algunos costos no se pudieron consultar.', 'warn'));
      }
    } catch (error) {
      if (current === revision) result(results, note(error.message, 'error'));
    }
  }
  form.onsubmit = (event) => { event.preventDefault(); filters = query(new FormData(form)); load(); };
  form.onreset = () => { filters = new URLSearchParams(); load(); };
  const featuredLoad = (async () => {
    try {
      const listings = await api('/publicaciones?zona=Caballito&moneda=ARS');
      const p = listings.find((item) => item.tipo_ajuste === 'INDICE') || listings[0];
      if (!p) { result(featured, '<small>Consultá el desglose de cada publicación en los resultados.</small>'); return; }
      const cost = await api('/publicaciones/' + p.id + '/costo-real');
      result(featured, `<p class="eyebrow">${h(p.propiedad.zona)} · ${h(p.propiedad.tipo)}</p>
        <div class="row"><span>Alquiler publicado</span><strong>${h(money(p.precio_alquiler))}</strong></div>
        <div class="row"><span>Costo mensual informado<strong class="value">${h(money(cost.total))}</strong></span></div>
        <a href="#publicacion/${p.id}">Ver publicación de ejemplo</a>`);
    } catch {
      result(featured, '<small>El costo mensual se muestra en cada publicación.</small>');
    }
  })();
  await Promise.all([load(), featuredLoad]);
}

function costPanel(title, cost, tone) {
  return `<section class="panel ${tone}"><h2>${title}</h2><strong class="value">${h(money(cost.total))}</strong>
    ${Object.entries(cost.componentes_informados).map(([key, value]) =>
      `<div class="row"><span>${h(label(key))}</span><strong class="money">${h(money(value))}</strong></div>`).join('')}
    ${missing(cost.faltantes)}</section>`;
}

async function publication(id, version) {
  const path = '/publicaciones/' + id;
  const [p, monthly, entry] = await Promise.all([api(path), api(path + '/costo-real'), api(path + '/costo-entrada')]);
  if (version !== routeVersion) return;
  result(main, `<div class="wrap content"><a class="back" href="#buscar">Volver a publicaciones</a>
    <div class="detail-head"><p class="eyebrow">${h(p.propiedad.zona)} · ${h(p.propiedad.tipo)}</p>
    <h1>${h(p.propiedad.direccion)}</h1><p class="muted">${h(metadata(p.propiedad))} · ${h(adjustment(p))}</p></div>
    <div class="pair">${costPanel('Costo mensual real', monthly, 'teal')}${costPanel('Costo de entrada', entry, 'gold')}</div>
    <div class="stack"><section class="panel night" id="income-panel"><h2>Impacto sobre tus ingresos</h2></section>
    <section class="panel"><h2>Proyección a 12 y 24 meses</h2><p class="muted">Estimación según el tipo de ajuste informado y el escenario elegido.</p>
    ${!user ? loginPrompt('Ingresá para consultar la proyección.') : `<form class="fields" id="projection">
      ${input('Ajuste cada (meses)', 'meses_periodicidad', 'type="number" min="1" max="24" value="6" required')}
      ${p.tipo_ajuste === 'INDICE' ? input('Variación mensual del índice (%)', 'tasa_mensual', 'type="number" min="0" step="any" placeholder="Promedio de la serie" value="2.5"') : ''}
      ${submitButton('Proyectar costos')}</form>`}
    </section></div></div>`);
  const form = main.querySelector('#projection');
  if (form) submit(form, async (data, output) => {
    result(output, note('Calculando proyección…'));
    const projection = await api(path + '/proyeccion?' + query(data));
    result(output, (projection.escenario ? note('Variación mensual usada: ' + pct(projection.escenario.tasa_mensual_porcentual) + '.') : '') +
      table(['Horizonte', 'Alquiler', 'Costo mensual', '% del ingreso'], projection.meses.map((m) =>
        ['Mes ' + m.mes, money(m.alquiler), money(m.costo_mensual), pct(m.porcentaje_ingreso)])) +
      projection.meses.map((m) => `<p><small>Mes ${m.mes}: ${h(m.formula)}</small></p>`).join('') + missing(projection.faltantes));
  });
  const income = main.querySelector('#income-panel');
  if (!user || !user.ingreso_referencia) {
    income.insertAdjacentHTML('beforeend', user ?
      '<p>Cargá tu ingreso mensual de referencia para ver qué parte representa este alquiler.</p><button class="quiet" data-login>Cargar ingreso</button>' :
      loginPrompt('Ingresá para comparar el costo mensual con tu ingreso.'));
    return;
  }
  try {
    const analysis = await api(path + '/analisis');
    income.insertAdjacentHTML('beforeend', `<div class="metrics">
      ${metric('Ingreso mensual', money(analysis.ingreso_referencia))}
      ${metric('Costo mensual', money(analysis.costo_real.total))}
      ${metric('Parte de tu ingreso', pct(analysis.porcentaje_ingreso))}
      </div><div class="impact" aria-hidden="true"><span style="width:${Math.max(0, Math.min(100, Number(analysis.porcentaje_ingreso)))}%"></span></div>
      <button class="quiet" data-login>Editar ingreso</button>`);
  } catch (error) {
    income.insertAdjacentHTML('beforeend', note(error.message, 'warn') + '<button class="quiet" data-login>Editar ingreso</button>');
  }
}

function metric(title, value) {
  return `<div class="metric"><small>${title}</small><strong class="value">${h(value)}</strong></div>`;
}

function publish() {
  if (!canPublish()) {
    result(main, `<div class="wrap content"><h1>Nueva publicación</h1><div class="panel">
      ${user ? '<p>Esta operación está reservada a cuentas inmobiliarias y de administración.</p>' :
        loginPrompt('Ingresá con una cuenta inmobiliaria para publicar.')}
    </div></div>`);
    return;
  }

  const optionalCosts = {
    expensas_mensuales: 'Expensas mensuales',
    abl_mensual: 'ABL mensual',
    seguro_caucion: 'Seguro de caución (total)',
    deposito: 'Depósito',
    comision: 'Comisión',
    otros_gastos_entrada: 'Otros gastos de entrada',
  };
  result(main, `<div class="wrap content"><a class="back" href="#buscar">Volver a publicaciones</a>
    <h1>Nueva publicación</h1>
    <form id="publish-form" class="stack">
      <section class="panel teal"><h2>Datos de la propiedad</h2><div class="fields">
        ${input('Dirección', 'direccion', 'required minlength="5" maxlength="200" placeholder="Ej. Av. Rivadavia 374"')}
        ${input('Barrio', 'zona', 'required minlength="2" maxlength="100" placeholder="Ej. Caballito"')}
        ${select('Tipo de propiedad', 'tipo', [['departamento','Departamento'], ['casa','Casa'], ['ph','PH']])}
        ${input('Ambientes', 'ambientes', 'type="number" min="1" max="10" required')}
        ${input('Superficie (m²)', 'metros_cuadrados', 'type="number" min="0.01" max="999999.99" step="0.01"')}
        ${select('Mascotas', 'permite_mascotas', [['','Sin informar'], ['true','Acepta mascotas'], ['false','No acepta mascotas']])}
      </div></section>
      <section class="panel gold"><h2>Alquiler y gastos</h2>
        <p class="muted">Dejá en blanco los gastos que todavía no conozcas. Usá 0 si el gasto está confirmado en cero.</p>
        <div class="fields">
          ${input('Alquiler mensual', 'precio_alquiler', 'type="number" min="0.01" max="9999999999.99" step="0.01" required')}
          ${select('Moneda de los importes', 'moneda', currency)}
          ${input('Duración del contrato (meses)', 'duracion_contrato_meses', 'type="number" min="1" max="36"')}
          ${Object.entries(optionalCosts).map(([key, title]) =>
            input(title, key, 'type="number" min="0" max="9999999999.99" step="0.01"')).join('')}
          ${input('Garantía aceptada', 'tipo_garantia_aceptada', 'minlength="2" maxlength="100"')}
        </div></section>
      <section class="panel"><h2>Ajuste del alquiler</h2><div class="fields">
        ${select('Tipo de ajuste', 'tipo_ajuste', [['','Sin informar'], ['INDICE','Por índice'], ['FIJO','Porcentaje fijo']])}
        ${input('Código de la serie', 'serie_codigo', 'placeholder="Ej. ICL"')}
        ${input('Tasa fija por ajuste (%)', 'tasa_ajuste', 'type="number" min="0" step="any"')}
      </div></section>
      ${submitButton('Publicar')}
    </form></div>`);

  const form = main.querySelector('#publish-form');
  function updateAdjustmentFields() {
    const adjustmentType = form.elements.tipo_ajuste.value;
    for (const [field, requiredType] of [['serie_codigo', 'INDICE'], ['tasa_ajuste', 'FIJO']]) {
      const control = form.elements[field];
      const enabled = adjustmentType === requiredType;
      control.disabled = !enabled;
      control.required = enabled;
      control.closest('label').hidden = !enabled;
    }
  }
  form.elements.tipo_ajuste.onchange = updateAdjustmentFields;
  updateAdjustmentFields();

  submit(form, async (data) => {
    const value = (name) => data.get(name)?.trim() || null;
    const currency = value('moneda');
    const amount = (name) => value(name) === null ? null : { monto: value(name), moneda: currency };
    const pets = value('permite_mascotas');
    const duration = value('duracion_contrato_meses');
    const publication = await api('/publicaciones', 'POST', {
      propiedad: {
        direccion: value('direccion'), zona: value('zona'), tipo: value('tipo'),
        ambientes: Number(value('ambientes')), metros_cuadrados: value('metros_cuadrados'),
        permite_mascotas: pets === null ? null : pets === 'true',
      },
      precio_alquiler: amount('precio_alquiler'),
      ...Object.fromEntries(Object.keys(optionalCosts).map((key) => [key, amount(key)])),
      duracion_contrato_meses: duration === null ? null : Number(duration),
      tipo_garantia_aceptada: value('tipo_garantia_aceptada'),
      tipo_ajuste: value('tipo_ajuste'), tasa_ajuste: value('tasa_ajuste'),
      serie_codigo: value('serie_codigo')?.toUpperCase() ?? null,
    });
    filters = new URLSearchParams();
    location.hash = '#publicacion/' + publication.id;
  });
}

async function contracts(version) {
  if (!user) {
    result(main, `<div class="wrap content"><h1>Mis contratos</h1><div class="panel">${loginPrompt('Ingresá para registrar un contrato o verificar un ajuste.')}</div></div>`);
    return;
  }
  const records = await api('/contratos');
  if (version !== routeVersion) return;
  result(main, `<div class="wrap content"><h1>Mis contratos</h1><p class="muted">Consultá el calendario y compará un importe informado con el ajuste calculado.</p>
    <div class="stack"><section class="panel"><details ${records.length ? '' : 'open'}>
      <summary>Registrar contrato</summary><form id="contract-form" class="fields">
      ${input('Fecha de inicio', 'fecha_inicio', 'type="date" required')}
      ${input('Duración (meses)', 'duracion_meses', 'type="number" min="1" max="120" value="12" required')}
      ${input('Alquiler inicial', 'monto', 'type="number" min="0.01" step="0.01" placeholder="500000" required')}
      ${select('Moneda', 'moneda', currency)}
      ${select('Tipo de ajuste', 'tipo_ajuste', [['INDICE','Por índice'], ['FIJO','Porcentaje fijo']])}
      ${input('Ajuste cada (meses)', 'meses_periodicidad', 'type="number" min="1" max="60" value="3" required')}
      ${input('Serie', 'serie_codigo', 'value="ICL" required')}
      ${input('Tasa fija por ajuste (%)', 'tasa_ajuste', 'type="number" min="0" step="0.01" required')}
      ${submitButton('Registrar contrato')}</form></details></section>
    <section><h2>Contratos registrados</h2>${records.length ? '<div class="cards">' + records.map((c) =>
      `<article class="card"><p class="eyebrow">Contrato #${c.id}</p><h3>${h(money(c.monto_base))}</h3>
      <p class="muted">${h(date(c.fecha_inicio))} al ${h(date(c.fecha_fin))}<br>${h(adjustment(c))} cada ${c.meses_periodicidad} meses</p>
      <a class="quiet" href="#contrato/${c.id}">Ver contrato</a></article>`).join('') + '</div>' :
      '<p class="empty">Todavía no hay contratos registrados.</p>'}</section></div></div>`);
  const form = main.querySelector('#contract-form');
  function toggleAdjustment() {
    const byIndex = form.elements.tipo_ajuste.value === 'INDICE';
    for (const [field, show] of [['serie_codigo', byIndex], ['tasa_ajuste', !byIndex]]) {
      const input = form.elements[field];
      input.disabled = !show;
      input.closest('label').hidden = !show;
    }
  }
  form.elements.tipo_ajuste.onchange = toggleAdjustment;
  toggleAdjustment();
  submit(form, async (data) => {
    const c = await api('/contratos', 'POST', {
      fecha_inicio: data.get('fecha_inicio'), duracion_meses: Number(data.get('duracion_meses')),
      monto_base: { monto: data.get('monto'), moneda: data.get('moneda') },
      tipo_ajuste: data.get('tipo_ajuste'), meses_periodicidad: Number(data.get('meses_periodicidad')),
      tasa_ajuste: data.get('tasa_ajuste'), serie_codigo: data.get('serie_codigo'),
    });
    location.hash = '#contrato/' + c.id;
  });
}

async function contract(id, version) {
  if (!user) return contracts(version);
  const path = '/contratos/' + id;
  const c = await api(path);
  if (version !== routeVersion) return;
  result(main, `<div class="wrap content"><a class="back" href="#contratos">Volver a mis contratos</a>
    <p class="eyebrow">Seguimiento de alquiler</p><h1>Contrato #${c.id}</h1>
    <div class="stack"><section class="panel teal"><div class="metrics">
      ${metric('Alquiler inicial', money(c.monto_base))}${metric('Inicio', date(c.fecha_inicio))}
      ${metric('Ajuste', adjustment(c))}</div><p class="muted">Cada ${c.meses_periodicidad} meses · Fin del contrato: ${h(date(c.fecha_fin))}</p></section>
    <section class="panel"><h2>Calendario de ajustes</h2><div id="calendar" aria-live="polite"></div>
      <form id="adjustment" class="fields">${input('Consultar ajuste vigente al', 'fecha', 'type="date" required')}${submitButton('Consultar ajuste')}</form></section>
    <section class="panel night"><h2>Verificar un ajuste</h2><p>Compará el importe informado con el que calcula Alquilómetro.</p>
      <form id="verification" class="fields">
        ${input('Fecha a verificar', 'fecha_ajuste', 'type="date" required')}
        ${input('Importe informado (' + h(c.monto_base.moneda) + ')', 'monto', 'type="number" min="0.01" step="0.01" required')}
        ${submitButton('Verificar')}</form></section>
    <section class="panel"><h2>Historial de verificaciones</h2><div id="history" aria-live="polite"></div></section></div></div>`);
  const history = main.querySelector('#history');
  const calendar = main.querySelector('#calendar');
  async function historyLoad() {
    try {
      const entries = await api(path + '/verificaciones');
      result(history, entries.length ? table(['Fecha', 'Resultado', 'Informado', 'Esperado', 'Diferencia'],
        entries.map((v) => [date(v.fecha_ajuste), v.resultado, money(v.informado), money(v.esperado), money(v.diferencia)])) :
        '<p class="muted">Todavía no hay verificaciones.</p>');
    } catch (error) { result(history, note(error.message, 'error')); }
  }
  submit(main.querySelector('#adjustment'), async (data, output) => {
    const a = await api(path + '/ajuste?' + query(data));
    result(output, metric('Alquiler ajustado', money(a.monto_ajustado)) + note(a.formula));
  });
  submit(main.querySelector('#verification'), async (data, output) => {
    const v = await api(path + '/verificaciones', 'POST', {
      fecha_ajuste: data.get('fecha_ajuste'),
      monto_informado: { monto: data.get('monto'), moneda: c.monto_base.moneda },
    });
    result(output, note(v.resultado + ' · ' + v.explicacion, v.resultado === 'CORRECTO' ? '' : 'warn') +
      `<div class="metrics">${metric('Informado', money(v.informado))}
      ${metric('Esperado', money(v.esperado))}
      ${metric('Diferencia (' + pct(v.diferencia_porcentual) + ')', money(v.diferencia))}</div>
      <p><small>${h(v.formula)}</small></p>`);
    await historyLoad();
  });
  async function calendarLoad() {
    try {
      const entries = await api(path + '/calendario');
      result(calendar, entries.length ? table(['Fecha', 'Estado', 'Alquiler ajustado'], entries.map((a) =>
        [date(a.fecha), a.estado, money(a.resultado?.monto_ajustado)])) : '<p>No hay ajustes programados.</p>');
      if (entries.length) {
        const usable = entries.filter((item) => item.resultado);
        const example = usable[1] ?? usable[0] ?? entries[0];
        if (version === routeVersion) {
          main.querySelector('#adjustment').elements.fecha.value ||= example.fecha;
          main.querySelector('#verification').elements.fecha_ajuste.value ||= example.fecha;
        }
      }
    } catch (error) { result(calendar, note(error.message, 'error')); }
  }
  await Promise.all([calendarLoad(), historyLoad()]);
}

async function route() {
  const version = ++routeVersion;
  const [page, id] = location.hash.slice(1).split('/');
  const tab = ['contrato', 'contratos'].includes(page) ? 'contratos' : page === 'publicar' ? 'publicar' : 'buscar';
  for (const link of document.querySelectorAll('[data-view]')) {
    if (link.dataset.view === tab) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  result(main, '<div class="wrap content"><p role="status">Cargando…</p></div>');
  window.scrollTo(0, 0);
  try {
    if (page === 'publicacion' && /^\d+$/.test(id)) await publication(id, version);
    else if (page === 'contrato' && /^\d+$/.test(id)) await contract(id, version);
    else if (page === 'contratos') await contracts(version);
    else if (page === 'publicar') publish();
    else await search(version);
  } catch (error) {
    if (version === routeVersion) result(main, `<div class="wrap content">${note(error.message, 'error')}
      <a class="quiet" href="#buscar">Ir a publicaciones</a></div>`);
  }
}

if (token) {
  try { setUser(await api('/usuarios/me'), token); }
  catch { setUser(null); }
}
window.addEventListener('hashchange', route);
await route();
