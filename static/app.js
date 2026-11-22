// Gudu Bites POS — mobile web app (no build step).
const app = document.getElementById("app");
const APP_NAME = "POS & Stock";
const state = {
  device: localStorage.getItem("gudu_device"),
  token: localStorage.getItem("gudu_token"),
  authMode: "signin", week: null,
  me: null, business: null, demo: null,
  menu: [], categories: [], cart: [],
  cat: "all", search: "", pay: "cash", cash: "",
  loginStaff: null, pin: "",
  salesDay: null, salesFilter: "all", dashDay: null, stockFilter: "all",
  poll: null, sheetOnClose: null,
};

// ------------------------------------------------------------ utils
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const ksh = (n) => "KSh " + Number(n || 0).toLocaleString("en-KE");
const qn = (n) => Number(n).toLocaleString("en-KE", { maximumFractionDigits: 2 });
const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "Africa/Nairobi" });
const time = (iso) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Africa/Nairobi" });
const dateTime = (iso) => new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Africa/Nairobi" });
const dayLabel = (d) => d === today() ? "Today" : new Date(d + "T12:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
const initials = (s) => String(s || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
const phoneFmt = (p) => /^254\d{9}$/.test(p || "") ? `0${p.slice(3, 6)} ${p.slice(6, 9)} ${p.slice(9)}` : (p || "");
const roleName = { owner: "Owner", cashier: "Cashier", storekeeper: "Storekeeper" };

const I = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>',
  cart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h8.6a2 2 0 0 0 2-1.6L22 7H6"/></svg>',
  receipt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 2v20l3-2 2 2 2-2 2 2 2-2 3 2V2l-3 2-2-2-2 2-2-2-2 2z"/><path d="M9 8h6M9 12h6M9 16h4"/></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/></svg>',
  more: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
  chev: '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 7"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
};

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = "Bearer " + state.token;
  if (state.device) headers["X-Device"] = state.device;
  const res = await fetch("/api" + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (res.status === 401 && !["/login", "/auth/signin"].includes(path)) {
    if (["/device", "/login-list"].includes(path)) { clearDevice(); setTimeout(render, 0); throw new Error("Please sign in to your business"); }
    clearSession(); go("#/login"); throw new Error("Please log in again");
  }
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map((d) => `${d.loc?.at(-1) ?? ""}: ${d.msg}`).join(", ");
    throw new Error(msg || "Something went wrong");
  }
  return data;
}

function toast(msg, err = false) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), err ? 4000 : 2400);
}

function openSheet(title, html, onClose = null) {
  closeSheet(false);
  state.sheetOnClose = onClose;
  const scrim = document.createElement("div");
  scrim.className = "scrim";
  scrim.innerHTML = `<div class="sheet" role="dialog" aria-label="${esc(title)}"><div class="sheet-grab"></div>
    <div class="sheet-head"><h3>${esc(title)}</h3><button class="sheet-close" data-act="close-sheet" aria-label="Close">&times;</button></div>
    <div class="sheet-body">${html}</div></div>`;
  document.body.appendChild(scrim);
  const first = scrim.querySelector("input[autofocus], select[autofocus]");
  if (first) setTimeout(() => first.focus(), 60);
}
function setSheet(html) { const b = document.querySelector(".sheet-body"); if (b) b.innerHTML = html; }
function closeSheet(runHook = true) {
  document.querySelectorAll(".scrim").forEach((s) => s.remove());
  if (runHook && state.sheetOnClose) { const f = state.sheetOnClose; state.sheetOnClose = null; f(); }
}
function stopPoll() { if (state.poll) { clearInterval(state.poll); state.poll = null; } }

function go(hash) { if (location.hash === hash) render(); else location.hash = hash; }
function clearSession() { state.token = null; state.me = null; localStorage.removeItem("gudu_token"); }
function clearDevice() { clearSession(); state.device = null; state.business = null; localStorage.removeItem("gudu_device"); }
function setDevice(token) { state.device = token; localStorage.setItem("gudu_device", token); }
function setSession(token, staff) { state.token = token; localStorage.setItem("gudu_token", token); state.me = staff; }

async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try { await fn(); } catch (e) { toast(e.message, true); } finally { if (btn && btn.isConnected) btn.disabled = false; }
}

// ------------------------------------------------------------ routing & shell
const NAV = {
  owner: [["dashboard", "Home", I.home], ["sell", "Sell", I.cart], ["sales", "Sales", I.receipt], ["stock", "Stock", I.box], ["more", "More", I.more]],
  cashier: [["sell", "Sell", I.cart], ["sales", "My sales", I.receipt], ["mpesa", "M-Pesa", I.phone]],
  storekeeper: [["stock", "Stock", I.box]],
};
const ACCESS = {
  owner: ["dashboard", "sell", "sales", "stock", "stock-item", "more", "menu", "staff", "mpesa", "settings", "recon", "mpesa-week"],
  cashier: ["sell", "sales", "mpesa"],
  storekeeper: ["stock", "stock-item"],
};
const HOME = { owner: "dashboard", cashier: "sell", storekeeper: "stock" };

function shell(active, content) {
  const me = state.me, nav = NAV[me.role];
  return `<header class="topbar">
      <div class="brand"><div class="brand-mark">${esc(initials(state.business?.name))}</div>
        <div style="min-width:0"><div class="brand-name">${esc(state.business?.name || "POS")}</div>
        <div class="brand-sub">${esc(me.name)} · ${roleName[me.role]}</div></div></div>
      <button class="icon-btn" data-act="logout" aria-label="Log out" title="Log out">${I.logout}</button>
    </header>
    <main>${content}</main>
    ${nav.length > 1 ? `<nav class="bottomnav">${nav.map(([r, label, ico]) => `<a href="#/${r}" class="${active === r || (active === "stock-item" && r === "stock") || (["menu", "staff", "settings"].includes(active) && r === "more") || (["mpesa", "recon", "mpesa-week"].includes(active) && r === "more" && me.role === "owner") ? "on" : ""}"><span class="nav-ico">${ico}</span>${label}</a>`).join("")}</nav>` : ""}`;
}

async function render() {
  stopPoll();
  const [name, arg] = location.hash.replace(/^#\/?/, "").split("/");
  try {
    if (!state.device) return renderAuth();
    if (state.demo === null) state.demo = (await api("/status")).demo_mode;
    if (!state.business) state.business = (await api("/device")).business;
    if (!state.token) return renderLogin();
    if (!state.me) {
      const me = await api("/me");
      state.me = me.staff; state.business = me.business; state.demo = me.demo_mode;
    }
    if (["login", "setup", "signup", "signin"].includes(name)) return go("#/" + HOME[state.me.role]);
    const route = ACCESS[state.me.role].includes(name) ? name : HOME[state.me.role];
    if (route !== name) return go("#/" + route);
    const html = await PAGES[route](arg);
    app.innerHTML = shell(route, html);
    window.scrollTo(0, 0);
    AFTER[route]?.();
  } catch (e) {
    if (state.device) app.innerHTML = `<div class="auth"><div class="card"><div class="error">${esc(e.message)}</div><button class="btn block" data-act="reload">Try again</button></div></div>`;
  }
}

// ------------------------------------------------------------ setup & login
function renderAuth() {
  const up = state.authMode === "signup";
  app.innerHTML = `<div class="auth">
    <div class="auth-logo"><div class="brand-mark">${I.cart}</div><h1>${APP_NAME}</h1><p>Sales, stock and M-Pesa for your business</p></div>
    <div class="card">
      <div class="seg" style="margin-bottom:16px"><button class="${up ? "" : "on"}" data-act="auth-mode" data-m="signin">Sign in</button><button class="${up ? "on" : ""}" data-act="auth-mode" data-m="signup">Create account</button></div>
      ${up ? `<form data-form="signup">
        <label class="field"><span>Business name</span><input class="input" name="business_name" required placeholder="e.g. Gudu Bites"></label>
        <label class="field"><span>M-Pesa till number</span><input class="input" name="till_number" inputmode="numeric" placeholder="e.g. 5123456"><small>Customers pay to this number. You can change it later.</small></label>
        <label class="field"><span>Your name</span><input class="input" name="owner_name" required></label>
        <div class="grid-2"><label class="field"><span>Phone</span><input class="input" name="phone" inputmode="tel" required placeholder="0712 345 678"></label>
          <label class="field"><span>Email (optional)</span><input class="input" name="email" type="email" placeholder="you@example.com"></label></div>
        <label class="field"><span>Password</span><input class="input" name="password" type="password" minlength="8" required autocomplete="new-password"><small>At least 8 characters. You sign in with your phone or email and this password.</small></label>
        <div class="grid-2"><label class="field"><span>Till screen PIN</span><input class="input" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="4 digits"></label>
          <label class="field"><span>Repeat PIN</span><input class="input" name="pin2" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required></label></div>
        <label class="check"><input type="checkbox" name="starter_menu" checked><span>Start with a sample hotel menu (from the Gudu Bites menu). You can edit or delete it.</span></label>
        <button class="btn gold block">Create account</button></form>`
      : `<form data-form="signin">
        <label class="field"><span>Phone or email</span><input class="input" name="identifier" required autocomplete="username" placeholder="0712 345 678 or you@example.com"></label>
        <label class="field"><span>Password</span><input class="input" name="password" type="password" required autocomplete="current-password"></label>
        <button class="btn gold block">Sign in</button>
        <div class="faint" style="margin-top:12px;text-align:center">For business owners. Staff log in with their PIN once the owner has signed in on this phone.</div></form>`}
    </div></div>`;
}

async function renderLogin() {
  const list = await api("/login-list");
  const s = state.loginStaff;
  if (!s) {
    app.innerHTML = `<div class="auth">
      <div class="auth-logo"><div class="brand-mark">${esc(initials(state.business?.name))}</div><h1>${esc(state.business?.name || "")}</h1><p>Who is working?</p></div>
      ${list.length ? "" : `<div class="faint">No staff yet.</div>`}
      <div class="who">${list.map((x) => `<button data-act="pick-staff" data-id="${x.id}" data-name="${esc(x.name)}" data-role="${x.role}">
        <div class="avatar">${esc(initials(x.name))}</div><div class="name">${esc(x.name)}</div><div class="role">${roleName[x.role]}</div></button>`).join("")}</div>
      <button class="link-btn" data-act="signout-device">Sign this phone out of ${esc(state.business?.name || "the business")}</button>
    </div>`;
    return;
  }
  app.innerHTML = `<div class="auth">
    <div class="auth-logo"><div class="avatar" style="width:62px;height:62px;font-size:24px">${esc(initials(s.name))}</div><h1>${esc(s.name)}</h1><p>Enter your 4-digit PIN</p></div>
    <div class="pin-wrap"><div class="pin-dots" id="dots">${[0, 1, 2, 3].map(() => "<i></i>").join("")}</div>
      <div class="keypad">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((k) => `<button data-act="pin" data-k="${k}">${k}</button>`).join("")}
        <button class="blank"></button><button data-act="pin" data-k="0">0</button><button data-act="pin" data-k="del" aria-label="Delete">&#9003;</button></div>
      <button class="link-btn" data-act="not-me">Not ${esc(s.name)}?</button></div></div>`;
}

function updateDots() { document.querySelectorAll("#dots i").forEach((d, i) => d.classList.toggle("on", i < state.pin.length)); }

// ------------------------------------------------------------ SELL (POS)
async function pageSell() {
  [state.menu, state.categories] = await Promise.all([api("/menu"), api("/categories")]);
  // drop cart lines for items that were removed from the menu
  state.cart = state.cart.filter((l) => state.menu.some((m) => m.id === l.id));
  return `<div class="search">${I.search}<input class="input" placeholder="Search the menu" value="${esc(state.search)}" data-input="search"></div>
    <div class="chips" id="chips">${chipsHtml()}</div>
    <div id="tiles">${tilesHtml()}</div>
    <div id="cartbar-slot">${cartbarHtml()}</div>`;
}
function chipsHtml() {
  const used = state.categories.filter((c) => state.menu.some((m) => m.category_id === c.id));
  return [`<button class="chip ${state.cat === "all" ? "on" : ""}" data-act="cat" data-id="all">All</button>`,
    ...used.map((c) => `<button class="chip ${state.cat == c.id ? "on" : ""}" data-act="cat" data-id="${c.id}">${esc(c.name)}</button>`)].join("");
}
function tileHtml(m) {
  const n = state.cart.filter((l) => l.id === m.id).reduce((a, l) => a + l.qty, 0);
  return `<button class="tile ${n ? "in" : ""}" data-act="add" data-id="${m.id}">
    ${n ? `<span class="badge">${n}</span>` : ""}
    <div><div class="t-name">${esc(m.name)}</div>${m.choice_options.length ? `<div class="t-opt">${esc(m.choice_options.join(" / "))}</div>` : ""}</div>
    <div class="t-price"><small>KSh</small>${m.price.toLocaleString("en-KE")}</div></button>`;
}
function tilesHtml() {
  const q = state.search.trim().toLowerCase();
  let items = state.menu.filter((m) => (state.cat === "all" || m.category_id == state.cat) && (!q || m.name.toLowerCase().includes(q)));
  if (!state.menu.length) return `<div class="card empty"><b>No menu items yet</b>${state.me.role === "owner" ? `Add your menu under <a href="#/menu">More → Menu</a>.` : "Ask the owner to add the menu."}</div>`;
  if (!items.length) return `<div class="empty"><b>Nothing found</b>Try another word.</div>`;
  if (state.cat !== "all" || q) return `<div class="tiles">${items.map(tileHtml).join("")}</div>`;
  return state.categories.map((c) => {
    const its = items.filter((m) => m.category_id === c.id);
    return its.length ? `<div class="cat-title">${esc(c.name)}</div><div class="tiles">${its.map(tileHtml).join("")}</div>` : "";
  }).join("");
}
const cartCount = () => state.cart.reduce((a, l) => a + l.qty, 0);
const cartTotal = () => state.cart.reduce((a, l) => a + l.qty * l.price, 0);
function cartbarHtml() {
  if (!state.cart.length) return "";
  return `<button class="cartbar" data-act="open-cart"><span class="count">${cartCount()}</span><span class="label">View order</span><span class="total">${ksh(cartTotal())}</span></button>`;
}
function refreshSell() {
  const t = document.getElementById("tiles"); if (t) t.innerHTML = tilesHtml();
  const c = document.getElementById("cartbar-slot"); if (c) c.innerHTML = cartbarHtml();
  const ch = document.getElementById("chips"); if (ch) ch.innerHTML = chipsHtml();
}
function addLine(m, choice) {
  const key = m.id + "|" + choice;
  const line = state.cart.find((l) => l.key === key);
  if (line) line.qty++; else state.cart.push({ key, id: m.id, name: m.name, price: m.price, choice, qty: 1 });
  refreshSell();
  if (navigator.vibrate) navigator.vibrate(12);
}

function cartSheetHtml() {
  if (!state.cart.length) return `<div class="empty"><b>The order is empty</b>Tap items on the menu to add them.</div>`;
  const total = cartTotal();
  const cashNum = Number(state.cash || 0);
  const quick = [...new Set([total, Math.ceil(total / 100) * 100, 500, 1000, 2000].filter((v) => v >= total))].slice(0, 4);
  const till = state.business?.till_number;
  return `<div class="list">${state.cart.map((l) => `<div class="row">
      <div class="row-main"><div class="row-title">${esc(l.name)}</div><div class="row-sub">${l.choice ? esc(l.choice) + " · " : ""}${ksh(l.price)} each</div></div>
      <div class="qty"><button data-act="cart-qty" data-key="${esc(l.key)}" data-d="-1" aria-label="Less">&minus;</button><span class="num">${l.qty}</span><button data-act="cart-qty" data-key="${esc(l.key)}" data-d="1" aria-label="More">+</button></div>
    </div>`).join("")}</div>
    <div class="total-row"><span class="muted">${cartCount()} item${cartCount() === 1 ? "" : "s"} · Total</span><b>${ksh(total)}</b></div>
    <div class="seg" style="margin-bottom:14px">
      <button class="${state.pay === "cash" ? "on" : ""}" data-act="pay" data-m="cash">Cash</button>
      <button class="${state.pay === "mpesa" ? "on" : ""}" data-act="pay" data-m="mpesa">M-Pesa</button></div>
    ${state.pay === "cash" ? `
      <label class="field"><span>Cash received (optional)</span><input class="input num" type="number" inputmode="numeric" min="0" placeholder="${total}" value="${esc(state.cash)}" data-input="cash"></label>
      <div class="quick">${quick.map((v) => `<button data-act="cash-quick" data-v="${v}">${v === total ? "Exact" : v.toLocaleString("en-KE")}</button>`).join("")}</div>
      <div class="change" id="change"${cashNum > total ? "" : ' style="display:none"'}><span>Change to give</span><span class="num">${ksh(Math.max(0, cashNum - total))}</span></div>`
    : `<div class="till-box">${till ? `<div class="t1">Customer pays to Till number</div><div class="t2">${esc(till)}</div><div class="t3">Amount <b>${ksh(total)}</b></div>` : `<div class="t1">No till number yet. The owner can add it in More → Business settings.</div>`}</div>
       <div class="faint" style="margin:-4px 2px 12px">The sale is marked <b>paid</b> only when the till payment arrives.</div>`}
    <button class="btn gold block" data-act="checkout">${state.pay === "cash" ? "Complete cash sale" : "Record sale and wait for payment"} · ${ksh(total)}</button>
    <button class="btn ghost block" style="margin-top:8px" data-act="clear-cart">Clear order</button>`;
}

function receiptHtml(s) {
  return `<div class="receipt"><div class="r-line faint"><span>${s.number} · ${esc(s.staff_name)}</span><span>${time(s.created_at)}</span></div>
    ${s.lines.map((l) => `<div class="r-line"><span>${l.qty} × ${esc(l.name)}${l.choice ? ` <span class="faint">(${esc(l.choice)})</span>` : ""}</span><span class="num">${l.line_total.toLocaleString("en-KE")}</span></div>`).join("")}
    <div class="r-line r-total"><span>Total</span><span class="num">${ksh(s.total)}</span></div>
    ${s.payment_method === "cash" ? `<div class="r-line faint"><span>Cash ${ksh(s.cash_tendered)}</span><span>Change ${ksh(s.change)}</span></div>` : ""}
    ${s.payment ? `<div class="r-line faint"><span>M-Pesa ${esc(s.payment.trans_id)}</span><span>${esc(s.payment.payer_name)}</span></div>` : ""}
  </div>`;
}

function resultHtml(s) {
  if (s.status === "paid") {
    return `<div class="result"><div class="big-ico ok">${I.check}</div><h3>${s.payment_method === "cash" ? "Cash sale saved" : "M-Pesa payment received"}</h3>
      <div class="muted">${s.payment_method === "cash" && s.change ? `Give change: <b>${ksh(s.change)}</b>` : `Sale ${s.number} is paid`}</div>
      ${receiptHtml(s)}<button class="btn gold block" data-act="close-sheet">New sale</button></div>`;
  }
  return `<div class="result"><div class="big-ico wait"><div class="spinner"></div></div><h3>Waiting for M-Pesa</h3>
    <div class="muted">Ask the customer to pay <b>${ksh(s.total)}</b> to Till <b>${esc(state.business?.till_number || "—")}</b></div>
    ${receiptHtml(s)}
    ${state.demo ? `<button class="btn green block" data-act="sim-pay" data-amount="${s.total}">Simulate customer paying (demo)</button>
      <div class="demo-note">Demo only: this acts like Safaricom telling the system a till payment has come in.</div>` : ""}
    <button class="btn ghost block" style="margin-top:10px" data-act="close-sheet">New sale (match payment later)</button></div>`;
}

function watchSale(id) {
  stopPoll();
  state.poll = setInterval(async () => {
    try {
      const s = await api("/sales/" + id);
      if (s.status === "paid") { stopPoll(); setSheet(resultHtml(s)); toast("Payment received"); }
    } catch { /* keep polling */ }
  }, 2500);
}

// ------------------------------------------------------------ SALES
async function pageSales() {
  const day = state.salesDay || today();
  const all = await api(`/sales?day=${day}`);
  const f = state.salesFilter;
  const rows = all.filter((s) => f === "all" || s.status === f);
  const live = all.filter((s) => s.status !== "void");
  const owner = state.me.role === "owner";
  return `<div class="page-head"><h1>${owner ? "Sales" : "My sales"}</h1><input type="date" class="date-pick" value="${day}" max="${today()}" data-change="sales-day"></div>
    <div class="card" style="display:flex;justify-content:space-between;align-items:center">
      <div><div class="faint">${dayLabel(day)}</div><div class="amount" style="font-size:24px">${ksh(live.reduce((a, s) => a + s.total, 0))}</div></div>
      <div class="row-end"><div class="amount">${live.length}</div><div class="faint">sales</div></div></div>
    <div class="chips">${[["all", "All"], ["paid", "Paid"], ["awaiting_payment", "Waiting for M-Pesa"], ["void", "Voided"]].map(([k, l]) => `<button class="chip ${f === k ? "on" : ""}" data-act="sales-filter" data-f="${k}">${l}${k !== "all" ? ` (${all.filter((s) => s.status === k).length})` : ""}</button>`).join("")}</div>
    ${rows.length ? `<div class="list">${rows.map(saleRow).join("")}</div>` : `<div class="card empty"><b>No sales here</b>Sales show up as soon as they are recorded.</div>`}`;
}
function statusPill(s) {
  return s.status === "paid" ? '<span class="pill paid">Paid</span>' : s.status === "void" ? '<span class="pill void">Void</span>' : '<span class="pill awaiting">Waiting</span>';
}
function saleRow(s) {
  return `<button class="row" data-act="sale" data-id="${s.id}">
    <div class="row-main"><div class="row-title">${s.number} <span class="pill ${s.payment_method}">${s.payment_method === "mpesa" ? "M-Pesa" : "Cash"}</span></div>
    <div class="row-sub">${time(s.created_at)} · ${s.item_count} item${s.item_count === 1 ? "" : "s"}${state.me.role === "owner" ? " · " + esc(s.staff_name) : ""}</div></div>
    <div class="row-end"><div class="amount">${ksh(s.total)}</div>${statusPill(s)}</div></button>`;
}
async function openSale(id) {
  const s = await api("/sales/" + id);
  const owner = state.me.role === "owner";
  openSheet(`Sale ${s.number}`, `${statusPill(s)} <span class="faint">${dateTime(s.created_at)}</span>
    ${receiptHtml(s)}
    ${s.status === "void" ? `<div class="faint">Voided: ${esc(s.void_reason)}</div>` : ""}
    ${s.status === "awaiting_payment" ? `<div class="alert">${I.alert}<span>Waiting for a till payment of ${ksh(s.total)}.</span></div><a class="btn block" href="#/mpesa" data-act="close-sheet-go" data-href="#/mpesa">Match an M-Pesa payment</a>` : ""}
    ${owner && s.status !== "void" ? `<button class="btn danger block" style="margin-top:10px" data-act="void-open" data-id="${s.id}">Void this sale</button>` : ""}`);
}

// ------------------------------------------------------------ M-PESA
async function pageMpesa() {
  const owner = state.me.role === "owner";
  const [unmatched, awaiting, todays, checks] = await Promise.all([api("/mpesa/payments?unmatched_only=true"), api("/sales/awaiting"), api("/mpesa/payments"), owner ? api("/mpesa/statements") : Promise.resolve([])]);
  const till = state.business?.till_number;
  return `<div class="page-head">${state.me.role === "owner" ? `<a class="back" href="#/more">${I.back}</a>` : ""}<h1>M-Pesa till</h1></div>
    <div class="card" style="display:flex;justify-content:space-between;align-items:center">
      <div><div class="faint">Till number</div><div class="amount" style="font-size:22px">${esc(till || "Not set")}</div></div>
      <div class="row-end"><div class="faint">Received today</div><div class="amount">${ksh(todays.reduce((a, p) => a + p.amount, 0))}</div></div></div>
    ${owner ? `<div class="card"><h2>Check against the M-Pesa statement</h2>
      <div class="muted" style="margin-bottom:12px">Upload the till statement PDF. Every payment on it is compared with the sales recorded here, so you see money with no sale, and M-Pesa sales with no money.</div>
      <div class="btn-row"><button class="btn gold" data-act="statement-open">Upload statement</button><a class="btn ghost" href="#/mpesa-week">Weekly analytics</a></div>
      ${checks.length ? `<div class="list" style="box-shadow:none;margin:12px -16px -16px;border-radius:0;border-top:1px solid var(--line)">${checks.slice(0, 5).map((c) => `<a class="row" href="#/recon/${c.id}" style="color:inherit;text-decoration:none">
        <div class="row-main"><div class="row-title">${periodLabel(c.first_day, c.last_day)}</div><div class="row-sub">${c.incoming_count} payments · checked ${dateTime(c.uploaded_at)}</div></div>${I.chev}</a>`).join("")}</div>` : ""}</div>` : ""}
    ${state.demo ? `<div class="demo-banner"><b>Demo mode.</b> Safaricom hasn't connected the till yet, so you can simulate a customer paying. <button class="btn small gold" style="margin-top:8px" data-act="sim-open">Simulate a till payment</button></div>` : ""}
    <div class="section-label">Payments not matched to a sale <span>${unmatched.length}</span></div>
    ${unmatched.length ? `<div class="list">${unmatched.map((p) => `<div class="row">
        <div class="row-main"><div class="row-title">${ksh(p.amount)} · ${esc(p.payer_name || "Customer")}</div><div class="row-sub">${esc(p.trans_id)} · ${time(p.received_at)}${p.simulated ? " · demo" : ""}</div></div>
        <button class="btn small" data-act="match-open" data-id="${p.id}" data-amount="${p.amount}">Match</button></div>`).join("")}</div>`
      : `<div class="card empty" style="padding:18px">Every payment is matched.</div>`}
    <div class="section-label">Sales waiting for payment <span>${awaiting.length}</span></div>
    ${awaiting.length ? `<div class="list">${awaiting.map(saleRow).join("")}</div>` : `<div class="card empty" style="padding:18px">No sales are waiting.</div>`}
    <div class="section-label">Today's till payments</div>
    ${todays.length ? `<div class="list">${todays.map((p) => `<div class="row"><div class="row-main"><div class="row-title">${esc(p.payer_name || "Customer")} <span class="faint">${esc(p.msisdn)}</span></div>
        <div class="row-sub">${esc(p.trans_id)} · ${time(p.received_at)}</div></div>
        <div class="row-end"><div class="amount">${ksh(p.amount)}</div>${p.sale_id ? `<span class="pill paid">Sale ${p.sale_number}</span>` : '<span class="pill awaiting">Unmatched</span>'}</div></div>`).join("")}</div>`
      : `<div class="card empty" style="padding:18px">No till payments yet today.</div>`}`;
}
async function openMatch(pid, amount) {
  const awaiting = await api("/sales/awaiting?days=62");
  const same = awaiting.filter((s) => s.total === amount), other = awaiting.filter((s) => s.total !== amount);
  openSheet(`Match ${ksh(amount)}`, `<p class="muted" style="margin-top:0">Pick the sale this payment belongs to. Only sales with the same amount can be matched.</p>
    ${same.length ? `<div class="list">${same.map((s) => `<button class="row" data-act="match-do" data-p="${pid}" data-s="${s.id}">
      <div class="row-main"><div class="row-title">${s.number} · ${esc(s.staff_name)}</div><div class="row-sub">${time(s.created_at)} · ${s.item_count} items</div></div>
      <div class="row-end"><div class="amount">${ksh(s.total)}</div></div>${I.chev}</button>`).join("")}</div>`
      : `<div class="card empty"><b>No waiting sale of ${ksh(amount)}</b>Record the sale first, choosing M-Pesa as the payment.</div>`}
    ${other.length ? `<div class="faint" style="margin:6px 4px">${other.length} other waiting sale${other.length === 1 ? "" : "s"} with different amounts.</div>` : ""}`);
}

// ------------------------------------------------------------ STOCK
async function pageStock() {
  const items = await api("/stock");
  const low = items.filter((s) => s.active && s.low);
  const f = state.stockFilter;
  const rows = items.filter((s) => f === "all" ? true : f === "low" ? s.active && s.low : s.kind === f);
  return `<div class="page-head"><h1>Stock</h1></div>
    ${low.length ? `<div class="alert">${I.alert}<span>${low.length} item${low.length === 1 ? " is" : "s are"} low: ${low.slice(0, 3).map((s) => esc(s.name)).join(", ")}${low.length > 3 ? "…" : ""}</span></div>` : ""}
    <div class="chips">${[["all", "All"], ["low", "Low"], ["direct", "Sold as is"], ["ingredient", "Ingredients"]].map(([k, l]) => `<button class="chip ${f === k ? "on" : ""}" data-act="stock-filter" data-f="${k}">${l}</button>`).join("")}</div>
    ${items.length ? (rows.length ? `<div class="list">${rows.map((s) => `<a class="row" href="#/stock-item/${s.id}" style="color:inherit;text-decoration:none;${s.active ? "" : "opacity:.5"}">
        <div class="row-main"><div class="row-title">${esc(s.name)}</div><div class="row-sub">${s.kind === "direct" ? "Sold as is" : "Ingredient"}${s.reorder_level ? ` · reorder at ${qn(s.reorder_level)}` : ""}</div></div>
        <div class="row-end"><div class="stock-qty">${qn(s.quantity)}<small>${esc(s.unit)}</small></div>${s.active && s.low ? '<span class="pill low">Low</span>' : ""}</div>${I.chev}</a>`).join("")}</div>`
        : `<div class="card empty">Nothing in this filter.</div>`)
      : `<div class="card empty"><b>No stock items yet</b>Add what you buy: sodas, water, sausages, potatoes, flour, cooking oil, meat…</div>`}
    <button class="fab" data-act="stock-new">${I.plus} Stock item</button>`;
}
const REASON = { purchase: "Received", sale: "Sold", count: "Stock count", waste: "Waste", void: "Voided sale returned" };
async function pageStockItem(id) {
  const [items, moves] = await Promise.all([api("/stock"), api(`/stock/${id}/movements`)]);
  const s = items.find((x) => x.id == id);
  if (!s) return `<div class="card empty">Not found</div>`;
  return `<div class="page-head"><a class="back" href="#/stock">${I.back}</a><h1>${esc(s.name)}</h1></div>
    <div class="card"><div class="big-stat"><div class="v">${qn(s.quantity)}</div><div class="u">${esc(s.unit)} in stock ${s.low && s.active ? '<span class="pill low">Low</span>' : ""}</div>
      ${s.last_unit_cost ? `<div class="faint" style="margin-top:4px">Last bought at ${ksh(Math.round(s.last_unit_cost))} per ${esc(s.unit.replace(/s$/, ""))}</div>` : ""}</div>
      <div class="btn-row"><button class="btn gold" data-act="stock-receive" data-id="${s.id}">Receive</button><button class="btn" data-act="stock-count" data-id="${s.id}">Count</button><button class="btn ghost" data-act="stock-waste" data-id="${s.id}">Waste</button></div>
      <button class="btn ghost block small" style="margin-top:8px" data-act="stock-edit" data-id="${s.id}">Edit details</button></div>
    <div class="section-label">History</div>
    ${moves.length ? `<div class="list">${moves.map((m) => `<div class="row"><div class="row-main"><div class="row-title">${REASON[m.reason] || m.reason}${m.sale_number ? ` <span class="faint">${m.sale_number}</span>` : ""}</div>
      <div class="row-sub">${dateTime(m.created_at)}${m.staff_name ? " · " + esc(m.staff_name) : ""}${m.supplier ? " · " + esc(m.supplier) : ""}${m.total_cost ? " · " + ksh(m.total_cost) : ""}${m.note ? " · " + esc(m.note) : ""}</div></div>
      <div class="row-end"><div class="amount ${m.change >= 0 ? "mv-plus" : "mv-minus"}">${m.change >= 0 ? "+" : ""}${qn(m.change)}</div><div class="faint">left ${qn(m.balance_after)}</div></div></div>`).join("")}</div>`
      : `<div class="card empty">No movements yet.</div>`}`;
}
const UNITS = ["bottles", "pieces", "kg", "litres", "crates", "packets", "trays", "cylinders"];
function stockForm(s) {
  return `<form data-form="stock" data-id="${s?.id || ""}">
    <label class="field"><span>Name</span><input class="input" name="name" value="${esc(s?.name || "")}" required autofocus placeholder="e.g. Soda 350ml, Potatoes"></label>
    <div class="grid-2"><label class="field"><span>Unit</span><input class="input" name="unit" list="units" value="${esc(s?.unit || "")}" required placeholder="bottles, kg…"></label>
      <label class="field"><span>Type</span><select class="input" name="kind"><option value="direct" ${s?.kind !== "ingredient" ? "selected" : ""}>Sold as is</option><option value="ingredient" ${s?.kind === "ingredient" ? "selected" : ""}>Ingredient</option></select></label></div>
    <datalist id="units">${UNITS.map((u) => `<option value="${u}">`).join("")}</datalist>
    <div class="grid-2"><label class="field"><span>Warn me when below</span><input class="input" name="reorder_level" type="number" step="any" min="0" inputmode="decimal" value="${s ? s.reorder_level : ""}" placeholder="0"></label>
      ${s ? `<label class="field"><span>Status</span><select class="input" name="active"><option value="1" ${s.active ? "selected" : ""}>In use</option><option value="0" ${s.active ? "" : "selected"}>Not used</option></select></label>`
        : `<label class="field"><span>How many you have now</span><input class="input" name="opening_qty" type="number" step="any" min="0" inputmode="decimal" placeholder="0"></label>`}</div>
    <small class="faint" style="display:block;margin:-6px 0 14px">"Sold as is" items (sodas, water, sausages) can be linked to a menu item so they go down by themselves when sold.</small>
    <button class="btn gold block">${s ? "Save" : "Add stock item"}</button></form>`;
}

// ------------------------------------------------------------ MENU
async function pageMenu() {
  const [menu, cats, stock] = await Promise.all([api("/menu?include_inactive=true"), api("/categories"), api("/stock")]);
  state.categories = cats; state.allMenu = menu; state.stockList = stock;
  return `<div class="page-head"><a class="back" href="#/more">${I.back}</a><h1>Menu</h1><button class="btn small ghost" data-act="cat-new">${I.plus} Category</button></div>
    ${cats.length ? "" : `<div class="card empty"><b>Start with a category</b>e.g. Beverages, Snacks, Chips, Beef Dishes.</div>`}
    ${cats.map((c) => {
      const its = menu.filter((m) => m.category_id === c.id);
      return `<div class="section-label"><span>${esc(c.name)} · ${its.length}</span><button class="btn small ghost" data-act="cat-edit" data-id="${c.id}">Rename</button></div>
        ${its.length ? `<div class="list">${its.map((m) => `<button class="row" data-act="item-edit" data-id="${m.id}" style="${m.active ? "" : "opacity:.5"}">
          <div class="row-main"><div class="row-title">${esc(m.name)} ${m.active ? "" : '<span class="pill tag">Hidden</span>'}</div>
          <div class="row-sub" style="${m.choice_options.length || m.stock_name ? "" : "display:none"}">${[m.choice_options.length ? `${esc(m.choice_label)}: ${esc(m.choice_options.join(", "))}` : "", m.stock_name ? `Uses ${qn(m.stock_qty)} ${esc(m.stock_unit)} of ${esc(m.stock_name)}` : ""].filter(Boolean).join(" · ")}</div></div>
          <div class="row-end amount">${ksh(m.price)}</div>${I.chev}</button>`).join("")}</div>` : `<div class="card empty" style="padding:16px">No items yet</div>`}`;
    }).join("")}
    ${cats.length ? `<button class="fab" data-act="item-new">${I.plus} Menu item</button>` : ""}`;
}
function itemForm(m) {
  const cats = state.categories, stock = state.stockList.filter((s) => s.active || s.id === m?.stock_item_id);
  return `<form data-form="item" data-id="${m?.id || ""}">
    <label class="field"><span>Item name</span><input class="input" name="name" value="${esc(m?.name || "")}" required placeholder="e.g. Chips Masala"></label>
    <div class="grid-2"><label class="field"><span>Price (KSh)</span><input class="input num" name="price" type="number" min="0" inputmode="numeric" value="${m?.price ?? ""}" required></label>
      <label class="field"><span>Category</span><select class="input" name="category_id">${cats.map((c) => `<option value="${c.id}" ${(m?.category_id ?? state.newItemCat) == c.id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label></div>
    <div class="card" style="background:#fbfaf6;box-shadow:none;border:1px solid var(--line);padding:12px">
      <div style="font-weight:700;margin-bottom:8px">Choice the cashier must pick <span class="faint">(optional)</span></div>
      <div class="grid-2"><label class="field" style="margin-bottom:0"><span>Name</span><input class="input" name="choice_label" value="${esc(m?.choice_label || "")}" placeholder="Accompaniment"></label>
        <label class="field" style="margin-bottom:0"><span>Options, comma separated</span><input class="input" name="choice_options" value="${esc(m?.choice_options?.join(", ") || "")}" placeholder="Ugali, Rice, Chapati"></label></div></div>
    <div class="card" style="background:#fbfaf6;box-shadow:none;border:1px solid var(--line);padding:12px">
      <div style="font-weight:700;margin-bottom:8px">Take from stock when sold <span class="faint">(optional)</span></div>
      <div class="grid-2"><label class="field" style="margin-bottom:0"><span>Stock item</span><select class="input" name="stock_item_id"><option value="">None</option>${stock.map((s) => `<option value="${s.id}" ${m?.stock_item_id === s.id ? "selected" : ""}>${esc(s.name)} (${esc(s.unit)})</option>`).join("")}</select></label>
        <label class="field" style="margin-bottom:0"><span>Amount per sale</span><input class="input" name="stock_qty" type="number" step="any" min="0.001" inputmode="decimal" value="${m?.stock_qty ?? 1}"></label></div>
      ${stock.length ? "" : `<div class="faint" style="margin-top:8px">Add stock items first under Stock.</div>`}</div>
    <label class="check"><input type="checkbox" name="active" ${m?.active === false ? "" : "checked"}><span>Show on the cashier's screen</span></label>
    <button class="btn gold block">${m ? "Save item" : "Add to menu"}</button></form>`;
}

// ------------------------------------------------------------ STAFF
async function pageStaff() {
  const list = await api("/staff");
  state.staffList = list;
  return `<div class="page-head"><a class="back" href="#/more">${I.back}</a><h1>Staff</h1></div>
    <p class="muted" style="margin-top:-6px">Each person logs in by tapping their name and entering their own 4-digit PIN. Cashiers only see their own sales and cannot change prices.</p>
    <div class="list">${list.map((s) => `<button class="row" data-act="staff-edit" data-id="${s.id}" style="${s.active ? "" : "opacity:.5"}">
      <div class="avatar" style="margin:0;width:40px;height:40px;font-size:15px">${esc(initials(s.name))}</div>
      <div class="row-main"><div class="row-title">${esc(s.name)}</div><div class="row-sub">${roleName[s.role]}${s.phone ? " · " + esc(phoneFmt(s.phone)) : ""}${s.active ? "" : " · Not active"}</div></div>${I.chev}</button>`).join("")}</div>
    <button class="fab" data-act="staff-new">${I.plus} Staff</button>`;
}
function staffForm(s) {
  return `<form data-form="staff" data-id="${s?.id || ""}">
    <label class="field"><span>Name</span><input class="input" name="name" value="${esc(s?.name || "")}" required ${s ? "" : "autofocus"}></label>
    <div class="grid-2"><label class="field"><span>Phone</span><input class="input" name="phone" inputmode="tel" value="${esc(s?.phone || "")}" placeholder="07..."></label>
      <label class="field"><span>Role</span><select class="input" name="role">${Object.entries(roleName).map(([k, v]) => `<option value="${k}" ${(s?.role || "cashier") === k ? "selected" : ""}>${v}</option>`).join("")}</select></label></div>
    <label class="field"><span>${s ? "New PIN" : "PIN"}</span><input class="input" name="pin" type="password" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" ${s ? 'placeholder="Leave empty to keep the current PIN"' : 'required placeholder="4 digits"'}></label>
    ${s ? `<label class="check"><input type="checkbox" name="active" ${s.active ? "checked" : ""}><span>Active (can log in)</span></label>` : ""}
    <button class="btn gold block">${s ? "Save" : "Add staff member"}</button></form>`;
}

// ------------------------------------------------------------ MORE & SETTINGS
async function pageMore() {
  const link = (href, ico, title, sub) => `<a class="row" href="${href}" style="color:inherit;text-decoration:none"><div class="more-ico">${ico}</div><div class="row-main"><div class="row-title">${title}</div><div class="row-sub">${sub}</div></div>${I.chev}</a>`;
  return `<div class="page-head"><h1>More</h1></div>
    <div class="list">${link("#/menu", I.menu, "Menu", "Items, prices, choices and stock links")}
      ${link("#/staff", I.users, "Staff", "Cashiers, storekeepers and their PINs")}
      ${link("#/mpesa", I.phone, "M-Pesa till", "Payments received and matching")}
      ${link("#/mpesa-week", I.home, "M-Pesa by week", "Money received, busiest days, top payers")}
      ${link("#/settings", I.gear, "Settings", "Business, till number, password, M-Pesa connection")}</div>
    <div class="list"><button class="row" data-act="logout"><div class="more-ico" style="background:#f1ede4">${I.logout}</div><div class="row-main"><div class="row-title">Log out</div><div class="row-sub">Hand the phone to the next person</div></div></button></div>`;
}
async function pageSettings() {
  const b = state.business || {}, me = state.me;
  const base = location.origin;
  return `<div class="page-head"><a class="back" href="#/more">${I.back}</a><h1>Settings</h1></div>
    <form class="card" data-form="business"><h2>Business</h2>
      <label class="field"><span>Business name</span><input class="input" name="name" value="${esc(b.name || "")}" required></label>
      <label class="field"><span>M-Pesa till number</span><input class="input" name="till_number" inputmode="numeric" value="${esc(b.till_number || "")}"><small>Shown to the cashier on every M-Pesa sale.</small></label>
      <button class="btn gold block">Save</button></form>
    ${me.has_password ? `<form class="card" data-form="password"><h2>Account <span class="faint">${esc(phoneFmt(me.phone))}${me.email ? " · " + esc(me.email) : ""}</span></h2>
      <label class="field"><span>Current password</span><input class="input" name="current" type="password" required autocomplete="current-password"></label>
      <div class="grid-2"><label class="field"><span>New password</span><input class="input" name="new" type="password" minlength="8" required autocomplete="new-password"></label>
        <label class="field"><span>Repeat new password</span><input class="input" name="new2" type="password" minlength="8" required></label></div>
      <button class="btn block">Change password</button></form>` : ""}
    ${b.callback_key ? `<div class="card"><h2>M-Pesa live connection</h2>
      <div class="muted" style="margin-bottom:10px">When Safaricom approves the till, register these two addresses with the Daraja C2B Register URL API. Keep them private: they identify your business.</div>
      <label class="field"><span>Confirmation URL</span><input class="input" readonly value="${esc(base)}/api/mpesa/c2b/confirmation/${esc(b.callback_key)}" onclick="this.select()"></label>
      <label class="field" style="margin-bottom:0"><span>Validation URL</span><input class="input" readonly value="${esc(base)}/api/mpesa/c2b/validation/${esc(b.callback_key)}" onclick="this.select()"></label></div>` : ""}
    <div class="card"><h2>Put the app on a phone</h2><div class="muted">Open this page in Chrome on the phone, tap the menu (⋮), then <b>Add to Home screen</b>. It opens like an app.</div></div>
    <button class="btn danger block" data-act="signout-device">Sign this phone out of the business</button>`;
}

// ------------------------------------------------------------ WEEKLY M-PESA ANALYTICS
const shortDate = (d) => new Date(d + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
async function pageMpesaWeek() {
  const d = await api(`/mpesa/analytics${state.week ? "?week=" + state.week : ""}`);
  const thisWeek = (() => { const t = new Date(today() + "T12:00:00"); t.setDate(t.getDate() - ((t.getDay() + 6) % 7)); return t.toLocaleDateString("en-CA"); })();
  const isCurrent = d.week_start >= thisWeek;
  const maxDay = Math.max(1, ...d.by_day.map((x) => x.total));
  const hrs = d.hours.slice(6, 24), maxH = Math.max(1, ...hrs);
  const maxPayer = Math.max(1, ...d.top_payers.map((x) => x.total));
  const pctM = d.total ? (d.matched_total / d.total) * 100 : 0;
  const change = d.change_pct === null ? (d.total ? "First week with payments" : "") : `${d.change_pct >= 0 ? "▲" : "▼"} ${Math.abs(d.change_pct)}% vs last week (${ksh(d.previous_total)})`;
  const hourLabel = (h) => h === 0 ? "midnight" : h < 12 ? `${h}am` : h === 12 ? "noon" : `${h - 12}pm`;
  return `<div class="page-head"><a class="back" href="#/mpesa">${I.back}</a><h1>M-Pesa by week</h1></div>
    <div class="card" style="display:flex;align-items:center;gap:8px;padding:10px">
      <button class="back" data-act="week-move" data-d="-1" aria-label="Previous week">${I.back}</button>
      <div style="flex:1;text-align:center"><div style="font-weight:700">${shortDate(d.week_start)} – ${shortDate(d.week_end)}</div><div class="faint">${isCurrent ? "This week" : "Monday to Sunday"}</div></div>
      <button class="back" data-act="week-move" data-d="1" aria-label="Next week" ${isCurrent ? "disabled style=\"opacity:.3\"" : ""}><span style="display:grid;transform:rotate(180deg)">${I.back}</span></button></div>
    ${!d.count && d.latest_week && d.latest_week !== d.week_start ? `<button class="alert" style="width:100%;border:0" data-act="week-jump" data-w="${d.latest_week}">${I.alert}<span>No till payments this week. Jump to the latest week with payments (${shortDate(d.latest_week)}).</span></button>` : ""}
    <div class="hero"><div class="h-label">Received on M-Pesa</div><div class="h-value">${ksh(d.total)}</div>
      <div class="h-stats"><div><b>${d.count}</b>payments</div><div><b>${d.count ? ksh(d.average) : "—"}</b>average</div><div><b>${d.count ? ksh(d.largest) : "—"}</b>largest</div></div>
      ${change ? `<div style="margin-top:12px;font-size:13px;color:#d9cdb2">${change}</div>` : ""}</div>
    <div class="dash-grid">
      <div class="card"><h2>By day ${d.busiest_day ? `<span class="faint">Busiest: ${d.busiest_day}</span>` : ""}</h2>
        ${d.by_day.map((x) => `<div class="bar-row"><div class="top"><span>${x.label} <span class="faint">${shortDate(x.date)}</span></span><span class="num"><b>${ksh(x.total)}</b> <span class="faint">· ${x.count}</span></span></div><div class="track"><div class="fill" style="width:${(x.total / maxDay) * 100}%;background:var(--mpesa)"></div></div></div>`).join("")}</div>
      <div class="card"><h2>Time of day ${d.peak_hour !== null ? `<span class="faint">Peak: ${hourLabel(d.peak_hour)}</span>` : ""}</h2>
        <div class="hours">${hrs.map((v, i) => `<div class="${v ? "" : "zero"}" style="height:${(v / maxH) * 100}%;background:${v ? "var(--mpesa)" : ""}" title="${hourLabel(i + 6)} · ${ksh(v)}"></div>`).join("")}</div>
        <div class="hours-axis"><span>6am</span><span>12pm</span><span>6pm</span><span>11pm</span></div></div>
      <div class="card"><h2>Matched to sales</h2>
        <div class="split"><i style="width:${pctM}%;background:var(--mpesa)"></i><i style="width:${d.total ? 100 - pctM : 0}%;background:#f0b44c"></i></div>
        <div class="legend"><div><span class="dot" style="background:var(--mpesa)"></span>Matched to a sale · ${d.matched_count}<span class="v">${ksh(d.matched_total)}</span></div>
          <div><span class="dot" style="background:#f0b44c"></span>No sale recorded · ${d.unmatched_count}<span class="v">${ksh(d.unmatched_total)}</span></div></div>
        ${d.unmatched_count ? `<div class="faint" style="margin-top:10px">Open a statement check on the M-Pesa screen to match these to sales.</div>` : ""}</div>
      <div class="card"><h2>Top payers</h2>${d.top_payers.length ? d.top_payers.map((x) => `<div class="bar-row"><div class="top"><span>${esc(x.name)} <span class="faint">· ${x.count}×</span></span><b class="num">${ksh(x.total)}</b></div><div class="track"><div class="fill" style="width:${(x.total / maxPayer) * 100}%;background:var(--gold)"></div></div></div>`).join("") : `<div class="muted">No payments this week.</div>`}</div>
    </div>
    <div class="faint" style="margin:12px 4px">Includes every till payment the system knows about: from statements (${d.sources.statement}), the live connection (${d.sources.callback}) and demo payments (${d.sources.simulated}).</div>`;
}

// ------------------------------------------------------------ DASHBOARD
async function pageDashboard() {
  const day = state.dashDay || today();
  const d = await api(`/dashboard?day=${day}`);
  const tot = d.total_sales || 0;
  const pct = (v) => (tot ? (v / tot) * 100 : 0).toFixed(1);
  const hrs = d.hours.slice(6, 24), maxH = Math.max(1, ...hrs);
  const maxItem = Math.max(1, ...d.top_items.map((x) => x.qty));
  const maxStaff = Math.max(1, ...d.by_staff.map((x) => x.total));
  return `<div class="page-head"><h1>${dayLabel(day)}</h1><input type="date" class="date-pick" value="${day}" max="${today()}" data-change="dash-day"></div>
    <div class="hero"><div class="h-label">Total sales</div><div class="h-value">${ksh(tot)}</div>
      <div class="h-stats"><div><b>${d.transactions}</b>sales</div><div><b>${d.items_sold}</b>items sold</div><div><b>${d.transactions ? ksh(Math.round(tot / d.transactions)) : "—"}</b>average sale</div></div></div>
    ${d.unmatched_payments ? `<a class="alert" href="#/mpesa">${I.alert}<span>${d.unmatched_payments} M-Pesa payment${d.unmatched_payments === 1 ? " is" : "s are"} not matched to a sale. Tap to check.</span></a>` : ""}
    ${d.mpesa_waiting ? `<a class="alert" href="#/mpesa">${I.alert}<span>${ksh(d.mpesa_waiting)} of M-Pesa sales are still waiting for payment.</span></a>` : ""}
    <div class="dash-grid">
      <div class="card"><h2>How customers paid</h2>
        <div class="split"><i style="width:${pct(d.mpesa_paid)}%;background:var(--mpesa)"></i><i style="width:${pct(d.cash)}%;background:var(--ink)"></i><i style="width:${pct(d.mpesa_waiting)}%;background:#f0b44c"></i></div>
        <div class="legend"><div><span class="dot" style="background:var(--mpesa)"></span>M-Pesa received<span class="v">${ksh(d.mpesa_paid)}</span></div>
          <div><span class="dot" style="background:var(--ink)"></span>Cash<span class="v">${ksh(d.cash)}</span></div>
          <div><span class="dot" style="background:#f0b44c"></span>M-Pesa waiting<span class="v">${ksh(d.mpesa_waiting)}</span></div></div>
        <div class="faint" style="margin-top:10px">Till payments received today: ${ksh(d.mpesa_received)}${d.voided ? ` · ${d.voided} voided sale${d.voided === 1 ? "" : "s"}` : ""}</div></div>
      <div class="card"><h2>Sales by hour <span class="faint">6am – midnight</span></h2>
        <div class="hours">${hrs.map((v, i) => `<div class="${v ? "" : "zero"}" style="height:${(v / maxH) * 100}%" title="${i + 6}:00 · ${ksh(v)}"></div>`).join("")}</div>
        <div class="hours-axis"><span>6am</span><span>12pm</span><span>6pm</span><span>11pm</span></div></div>
      <div class="card"><h2>Best sellers</h2>${d.top_items.length ? d.top_items.map((x) => `<div class="bar-row"><div class="top"><span>${esc(x.name)}</span><span class="num"><b>${x.qty}</b> <span class="faint">· ${ksh(x.total)}</span></span></div><div class="track"><div class="fill" style="width:${(x.qty / maxItem) * 100}%"></div></div></div>`).join("") : `<div class="empty" style="padding:10px">No sales yet</div>`}</div>
      <div class="card"><h2>By cashier</h2>${d.by_staff.length ? d.by_staff.map((x) => `<div class="bar-row"><div class="top"><span>${esc(x.name)} <span class="faint">· ${x.sales} sales</span></span><b class="num">${ksh(x.total)}</b></div><div class="track"><div class="fill" style="width:${(x.total / maxStaff) * 100}%;background:var(--gold)"></div></div></div>`).join("") : `<div class="empty" style="padding:10px">No sales yet</div>`}</div>
      <div class="card"><h2>Stock alerts <a class="faint" href="#/stock">View stock</a></h2>${d.low_stock.length ? d.low_stock.map((s) => `<div class="bar-row" style="display:flex;justify-content:space-between"><span>${esc(s.name)}</span><span><b class="num">${qn(s.quantity)}</b> <span class="faint">${esc(s.unit)}</span> <span class="pill low">Low</span></span></div>`).join("") : `<div class="muted">Nothing is running low.</div>`}</div>
      <div class="card"><h2>Latest sales <a class="faint" href="#/sales">All sales</a></h2>${d.recent.length ? `<div class="list" style="box-shadow:none;margin:0 -16px -16px;border-radius:0">${d.recent.map(saleRow).join("")}</div>` : `<div class="muted">No sales yet.</div>`}</div>
    </div>`;
}


// ------------------------------------------------------------ STATEMENT CHECK
const periodLabel = (a, b) => {
  const f = (d) => new Date(d + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  return a === b ? f(a) : `${f(a)} – ${f(b)}`;
};
function paySourceTag(p) {
  if (!p) return '<span class="pill awaiting">Waiting</span>';
  if (p.source === "simulated") return '<span class="pill tag">Demo payment</span>';
  return `<span class="pill tag">Paid · ${esc(p.trans_id)}</span>`;
}
async function pageRecon(id) {
  const r = await api(`/mpesa/statements/${id}`);
  const diff = r.difference;
  const issues = r.unrecorded.length + r.missing.length;
  const ok = diff === 0 && !issues;
  const diffText = ok ? "The statement and the POS agree." : diff === 0 ? "The totals agree, but some payments and sales don't line up. Check the lists below." : diff > 0 ? `${ksh(diff)} more came in on M-Pesa than the POS shows as M-Pesa sales.` : `The POS shows ${ksh(-diff)} more in M-Pesa sales than came in on the statement.`;
  const payRow = (p, withMatch) => `<div class="row"><div class="row-main"><div class="row-title">${ksh(p.amount)} · ${esc(p.payer_name || "Customer")}</div>
      <div class="row-sub">${esc(p.trans_id)} · ${dateTime(p.received_at)}${p.sale_number ? " · Sale " + p.sale_number : ""}</div></div>
      ${withMatch ? `<button class="btn small" data-act="match-open" data-id="${p.id}" data-amount="${p.amount}">Match</button>` : `<span class="pill paid">Matched</span>`}</div>`;
  return `<div class="page-head"><a class="back" href="#/mpesa">${I.back}</a><h1>Statement check</h1></div>
    <div class="faint" style="margin:-8px 2px 12px">${periodLabel(r.first_day, r.last_day)} · uploaded by ${esc(r.uploaded_by)} ${dateTime(r.uploaded_at)}</div>
    <div class="card">
      <div class="grid-2" style="gap:14px">
        <div><div class="faint">M-Pesa received (statement)</div><div class="amount" style="font-size:22px">${ksh(r.statement_total)}</div></div>
        <div><div class="faint">M-Pesa sales in the POS</div><div class="amount" style="font-size:22px">${ksh(r.pos_mpesa_total)}</div></div></div>
      <div class="change" style="margin:14px 0 0;background:${ok ? "var(--green-soft)" : "var(--amber-soft)"};color:${ok ? "var(--green)" : "#7a4a00"}"><span>Difference</span><span class="num">${diff > 0 ? "+" : ""}${ksh(diff)}</span></div>
      <div class="muted" style="margin-top:10px;font-size:14px">${diffText}</div>
      <div class="faint" style="margin-top:8px">${r.rows_read} lines read · ${r.incoming_count} payments in · ${r.new_count} new · ${r.already_known} already in the system</div></div>

    <div class="section-label"><span>Paid, but no sale recorded</span><span>${r.unrecorded.length} · ${ksh(r.unrecorded_total)}</span></div>
    ${r.unrecorded.length ? `<div class="faint" style="margin:-2px 4px 8px">Money came in but no sale was rung up for it. Match it to a sale, or ask the cashier on duty.</div>
      <div class="list">${r.unrecorded.map((p) => payRow(p, true)).join("")}</div>` : `<div class="card empty" style="padding:16px">None. Every payment on the statement has a sale.</div>`}

    <div class="section-label"><span>M-Pesa sale, but no payment on the statement</span><span>${r.missing.length} · ${ksh(r.missing_total)}</span></div>
    ${r.missing.length ? `<div class="faint" style="margin:-2px 4px 8px">The cashier chose M-Pesa, but this statement has no payment for it. Check these first.</div>
      <div class="list">${r.missing.map((s) => `<button class="row" data-act="sale" data-id="${s.id}"><div class="row-main"><div class="row-title">${s.number} · ${esc(s.staff_name)}</div>
        <div class="row-sub">${dateTime(s.created_at)} · ${s.item_count} item${s.item_count === 1 ? "" : "s"}</div></div>
        <div class="row-end"><div class="amount">${ksh(s.total)}</div>${paySourceTag(s.payment)}</div></button>`).join("")}</div>` : `<div class="card empty" style="padding:16px">None. Every M-Pesa sale has its payment.</div>`}

    <div class="section-label"><span>Matched</span><span>${r.matched.length} · ${ksh(r.matched_total)}</span></div>
    ${r.matched.length ? `<div class="list">${r.matched.map((p) => payRow(p, false)).join("")}</div>` : `<div class="card empty" style="padding:16px">No matches yet.</div>`}`;
}

const PAGES = { sell: pageSell, sales: pageSales, mpesa: pageMpesa, stock: pageStock, "stock-item": pageStockItem, menu: pageMenu, staff: pageStaff, more: pageMore, settings: pageSettings, dashboard: pageDashboard, recon: pageRecon, "mpesa-week": pageMpesaWeek };
const AFTER = {};

// ------------------------------------------------------------ actions
const actions = {
  "close-sheet": () => closeSheet(),
  "close-sheet-go": (el) => { closeSheet(); go(el.dataset.href); },
  reload: () => location.reload(),
  logout: async () => { try { await api("/logout", { method: "POST" }); } catch { /* ignore */ } clearSession(); state.cart = []; state.loginStaff = null; go("#/login"); },
  "auth-mode": (el) => { state.authMode = el.dataset.m; renderAuth(); },
  "signout-device": async () => {
    if (!confirm("Sign this phone out? The owner will need to sign in again with the password.")) return;
    try { await api("/auth/signout-device", { method: "POST" }); } catch { /* ignore */ }
    clearDevice(); state.cart = []; state.loginStaff = null; state.authMode = "signin"; location.hash = ""; render();
  },
  "week-move": (el) => {
    const cur = state.week ? new Date(state.week + "T12:00:00") : new Date();
    cur.setDate(cur.getDate() + 7 * Number(el.dataset.d));
    state.week = cur.toLocaleDateString("en-CA"); render();
  },
  "week-jump": (el) => { state.week = el.dataset.w; render(); },
  "pick-staff": (el) => { state.loginStaff = { id: +el.dataset.id, name: el.dataset.name }; state.pin = ""; renderLogin(); },
  "not-me": () => { state.loginStaff = null; renderLogin(); },
  pin: async (el) => {
    const k = el.dataset.k;
    if (k === "del") state.pin = state.pin.slice(0, -1); else if (state.pin.length < 4) state.pin += k;
    updateDots();
    if (state.pin.length === 4) {
      try {
        const r = await api("/login", { method: "POST", body: { staff_id: state.loginStaff.id, pin: state.pin } });
        setSession(r.token, r.staff); state.loginStaff = null; state.pin = "";
        go("#/" + HOME[r.staff.role]);
      } catch (e) {
        state.pin = ""; const d = document.getElementById("dots");
        d.classList.add("shake"); setTimeout(() => { d.classList.remove("shake"); updateDots(); }, 380); toast("Wrong PIN", true);
      }
    }
  },
  cat: (el) => { state.cat = el.dataset.id === "all" ? "all" : +el.dataset.id; refreshSell(); },
  add: (el) => {
    const m = state.menu.find((x) => x.id === +el.dataset.id);
    if (!m) return;
    if (!m.choice_options.length) return addLine(m, "");
    openSheet(m.name, `<p class="muted" style="margin-top:0">Choose ${esc(m.choice_label.toLowerCase())}</p>
      <div class="choice-grid">${m.choice_options.map((o) => `<button data-act="add-choice" data-id="${m.id}" data-choice="${esc(o)}">${esc(o)}</button>`).join("")}</div>`);
  },
  "add-choice": (el) => { const m = state.menu.find((x) => x.id === +el.dataset.id); closeSheet(); addLine(m, el.dataset.choice); },
  "open-cart": () => openSheet("Order", cartSheetHtml(), refreshSell),
  "cart-qty": (el) => {
    const l = state.cart.find((x) => x.key === el.dataset.key);
    if (!l) return;
    l.qty += +el.dataset.d;
    if (l.qty <= 0) state.cart = state.cart.filter((x) => x !== l);
    setSheet(cartSheetHtml()); refreshSell();
  },
  "clear-cart": () => { state.cart = []; state.cash = ""; closeSheet(); },
  pay: (el) => { state.pay = el.dataset.m; setSheet(cartSheetHtml()); },
  "cash-quick": (el) => { state.cash = el.dataset.v; setSheet(cartSheetHtml()); },
  checkout: (el) => busy(el, async () => {
    const body = { payment_method: state.pay, cash_tendered: state.pay === "cash" ? Number(state.cash || 0) : 0,
      lines: state.cart.map((l) => ({ menu_item_id: l.id, qty: l.qty, choice: l.choice })) };
    const s = await api("/sales", { method: "POST", body });
    state.cart = []; state.cash = "";
    openSheet(s.payment_method === "cash" ? "Sale complete" : `Sale ${s.number}`, resultHtml(s), () => { stopPoll(); refreshSell(); });
    if (s.status === "awaiting_payment") watchSale(s.id);
  }),
  "sim-pay": (el) => busy(el, async () => {
    await api("/mpesa/simulate", { method: "POST", body: { amount: +el.dataset.amount, payer_name: "JOHN KAMAU", phone: "2547 ***** 126" } });
  }),
  "sales-filter": (el) => { state.salesFilter = el.dataset.f; render(); },
  sale: (el) => busy(null, () => openSale(+el.dataset.id)),
  "void-open": (el) => openSheet("Void sale", `<form data-form="void" data-id="${el.dataset.id}"><p class="muted" style="margin-top:0">Voiding cancels the sale and puts any stock it used back.</p>
      <label class="field"><span>Reason</span><input class="input" name="reason" required autofocus placeholder="e.g. Customer changed order"></label><button class="btn danger block">Void sale</button></form>`),
  "sim-open": () => openSheet("Simulate a till payment", `<form data-form="sim"><label class="field"><span>Amount (KSh)</span><input class="input num" name="amount" type="number" min="1" inputmode="numeric" required autofocus></label>
      <label class="field"><span>Customer name</span><input class="input" name="payer_name" value="JOHN KAMAU"></label>
      <button class="btn green block">Send payment</button><div class="demo-note">Acts like Safaricom telling the system a payment came in. If exactly one waiting sale has this amount, it is matched automatically.</div></form>`),
  "statement-open": () => openSheet("Upload M-Pesa statement", `<form data-form="statement">
      <label class="field"><span>Statement PDF</span><input class="input" type="file" name="file" accept="application/pdf,.pdf" required></label>
      <label class="field"><span>PDF password</span><input class="input" name="password" type="password" autocomplete="off" placeholder="The password Safaricom sent with the statement"></label>
      <button class="btn gold block">Check statement</button>
      <div class="demo-note">The PDF is read once and not kept. Only each payment's receipt number, time, amount and payer name are saved. Uploading the same statement again is safe: nothing is counted twice.</div></form>`),
  "match-open": (el) => busy(null, () => openMatch(+el.dataset.id, +el.dataset.amount)),
  "match-do": (el) => busy(el, async () => {
    await api(`/mpesa/payments/${el.dataset.p}/match`, { method: "POST", body: { sale_id: +el.dataset.s } });
    closeSheet(false); toast("Payment matched"); render();
  }),
  "stock-filter": (el) => { state.stockFilter = el.dataset.f; render(); },
  "stock-new": () => openSheet("New stock item", stockForm(null)),
  "stock-edit": async (el) => { const s = (await api("/stock")).find((x) => x.id === +el.dataset.id); openSheet("Edit stock item", stockForm(s)); },
  "stock-receive": async (el) => {
    const s = (await api("/stock")).find((x) => x.id === +el.dataset.id);
    openSheet(`Receive ${s.name}`, `<form data-form="receive" data-id="${s.id}">
      <div class="grid-2"><label class="field"><span>Quantity (${esc(s.unit)})</span><input class="input num" name="qty" type="number" step="any" min="0.001" inputmode="decimal" required autofocus></label>
      <label class="field"><span>Total cost (KSh)</span><input class="input num" name="total_cost" type="number" min="0" inputmode="numeric" placeholder="0"></label></div>
      <label class="field"><span>Supplier</span><input class="input" name="supplier" placeholder="e.g. Coca-Cola distributor, Mama Njeri"></label>
      <button class="btn gold block">Add to stock</button></form>`);
  },
  "stock-count": async (el) => {
    const s = (await api("/stock")).find((x) => x.id === +el.dataset.id);
    openSheet(`Count ${s.name}`, `<form data-form="count" data-id="${s.id}"><p class="muted" style="margin-top:0">The system says <b>${qn(s.quantity)} ${esc(s.unit)}</b>. Enter what you actually counted. Any difference is recorded.</p>
      <label class="field"><span>Counted (${esc(s.unit)})</span><input class="input num" name="counted_qty" type="number" step="any" min="0" inputmode="decimal" required autofocus></label>
      <label class="field"><span>Note</span><input class="input" name="note" placeholder="optional"></label><button class="btn gold block">Save count</button></form>`);
  },
  "stock-waste": async (el) => {
    const s = (await api("/stock")).find((x) => x.id === +el.dataset.id);
    openSheet(`Waste: ${s.name}`, `<form data-form="waste" data-id="${s.id}"><label class="field"><span>Quantity (${esc(s.unit)})</span><input class="input num" name="qty" type="number" step="any" min="0.001" inputmode="decimal" required autofocus></label>
      <label class="field"><span>Reason</span><input class="input" name="note" placeholder="e.g. spoiled, broken bottle"></label><button class="btn danger block">Record waste</button></form>`);
  },
  "cat-new": () => openSheet("New category", `<form data-form="cat"><label class="field"><span>Name</span><input class="input" name="name" required autofocus placeholder="e.g. Beverages"></label><button class="btn gold block">Add category</button></form>`),
  "cat-edit": (el) => {
    const c = state.categories.find((x) => x.id === +el.dataset.id);
    openSheet("Edit category", `<form data-form="cat" data-id="${c.id}"><label class="field"><span>Name</span><input class="input" name="name" value="${esc(c.name)}" required autofocus></label>
      <button class="btn gold block">Save</button></form><button class="btn danger block" style="margin-top:8px" data-act="cat-delete" data-id="${c.id}">Delete category</button>`);
  },
  "cat-delete": (el) => busy(el, async () => { await api(`/categories/${el.dataset.id}`, { method: "DELETE" }); closeSheet(false); toast("Category deleted"); render(); }),
  "item-new": () => { state.newItemCat = state.categories[0]?.id; openSheet("New menu item", itemForm(null)); },
  "item-edit": (el) => openSheet("Edit menu item", itemForm(state.allMenu.find((m) => m.id === +el.dataset.id))),
  "staff-new": () => openSheet("New staff member", staffForm(null)),
  "staff-edit": (el) => openSheet("Edit staff member", staffForm(state.staffList.find((s) => s.id === +el.dataset.id))),
};

const forms = {
  signup: async (d) => {
    if (d.pin !== d.pin2) throw new Error("The two PINs are different");
    const r = await api("/auth/signup", { method: "POST", body: { business_name: d.business_name, till_number: d.till_number, owner_name: d.owner_name,
      phone: d.phone, email: d.email, password: d.password, pin: d.pin, starter_menu: !!d.starter_menu } });
    setDevice(r.device_token); setSession(r.token, r.staff); state.business = r.business; go("#/dashboard");
  },
  signin: async (d) => {
    const r = await api("/auth/signin", { method: "POST", body: { identifier: d.identifier, password: d.password } });
    setDevice(r.device_token); setSession(r.token, r.staff); state.business = r.business; go("#/dashboard");
  },
  password: async (d, f) => {
    if (d.new !== d.new2) throw new Error("The new passwords are different");
    await api("/auth/password", { method: "POST", body: { current: d.current, new: d.new } }); f.reset(); toast("Password changed");
  },
  stock: async (d, f) => {
    const id = f.dataset.id;
    const body = { name: d.name, unit: d.unit, kind: d.kind, reorder_level: Number(d.reorder_level || 0), opening_qty: Number(d.opening_qty || 0), active: id ? d.active === "1" : true };
    await api(id ? `/stock/${id}` : "/stock", { method: id ? "PUT" : "POST", body });
    closeSheet(false); toast(id ? "Saved" : "Stock item added"); render();
  },
  receive: async (d, f) => { await api(`/stock/${f.dataset.id}/receive`, { method: "POST", body: { qty: Number(d.qty), total_cost: Number(d.total_cost || 0), supplier: d.supplier } }); closeSheet(false); toast("Stock received"); render(); },
  count: async (d, f) => {
    const r = await api(`/stock/${f.dataset.id}/count`, { method: "POST", body: { counted_qty: Number(d.counted_qty), note: d.note } });
    closeSheet(false); toast(r.difference === 0 ? "Count matches" : `Difference of ${qn(r.difference)} ${r.unit} recorded`); render();
  },
  waste: async (d, f) => { await api(`/stock/${f.dataset.id}/waste`, { method: "POST", body: { qty: Number(d.qty), note: d.note } }); closeSheet(false); toast("Waste recorded"); render(); },
  cat: async (d, f) => { const id = f.dataset.id; await api(id ? `/categories/${id}` : "/categories", { method: id ? "PUT" : "POST", body: { name: d.name } }); closeSheet(false); toast("Saved"); render(); },
  item: async (d, f) => {
    const id = f.dataset.id;
    const body = { name: d.name, price: Number(d.price), category_id: Number(d.category_id), choice_label: d.choice_label, choice_options: d.choice_options,
      stock_item_id: d.stock_item_id ? Number(d.stock_item_id) : null, stock_qty: Number(d.stock_qty || 1), active: !!d.active };
    await api(id ? `/menu/${id}` : "/menu", { method: id ? "PUT" : "POST", body });
    closeSheet(false); toast(id ? "Item saved" : "Added to menu"); render();
  },
  staff: async (d, f) => {
    const id = f.dataset.id;
    const body = { name: d.name, phone: d.phone, role: d.role, pin: d.pin || null, active: id ? !!d.active : true };
    await api(id ? `/staff/${id}` : "/staff", { method: id ? "PUT" : "POST", body });
    closeSheet(false); toast("Saved"); render();
  },
  business: async (d) => { state.business = await api("/business", { method: "PUT", body: { name: d.name, till_number: d.till_number } }); toast("Saved"); render(); },
  void: async (d, f) => { await api(`/sales/${f.dataset.id}/void`, { method: "POST", body: { reason: d.reason } }); closeSheet(false); toast("Sale voided"); render(); },
  statement: async (d, f) => {
    const fd = new FormData(f);
    const res = await fetch("/api/mpesa/statements", { method: "POST", headers: { Authorization: "Bearer " + state.token }, body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Could not read the statement");
    closeSheet(false);
    toast(`${data.incoming_count} payments read · ${data.new_count} new`);
    go(`#/recon/${data.id}`);
  },
  sim: async (d) => {
    const p = await api("/mpesa/simulate", { method: "POST", body: { amount: Number(d.amount), payer_name: d.payer_name || "Customer", phone: "2547 ***** 126" } });
    closeSheet(false); toast(p.sale_id ? "Payment received and matched to a sale" : "Payment received — match it to a sale"); render();
  },
};

const inputs = {
  search: (el) => { state.search = el.value; const t = document.getElementById("tiles"); if (t) t.innerHTML = tilesHtml(); },
  cash: (el) => {
    state.cash = el.value;
    const total = cartTotal(), box = document.getElementById("change");
    if (!box) return;
    box.style.display = Number(el.value) > total ? "" : "none";
    box.lastElementChild.textContent = ksh(Math.max(0, Number(el.value) - total));
  },
};
const changes = {
  "sales-day": (el) => { state.salesDay = el.value || today(); render(); },
  "dash-day": (el) => { state.dashDay = el.value || today(); render(); },
};

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("scrim")) return closeSheet();
  const el = e.target.closest("[data-act]");
  if (!el) return;
  const fn = actions[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el, e); }
});
document.addEventListener("submit", (e) => {
  const f = e.target.closest("form[data-form]");
  if (!f) return;
  e.preventDefault();
  const data = Object.fromEntries(new FormData(f));
  busy(f.querySelector("button:not([type=button])"), () => forms[f.dataset.form](data, f));
});
document.addEventListener("input", (e) => { const el = e.target.closest("[data-input]"); if (el) inputs[el.dataset.input]?.(el); });
document.addEventListener("change", (e) => { const el = e.target.closest("[data-change]"); if (el) changes[el.dataset.change]?.(el); });
window.addEventListener("hashchange", () => { closeSheet(false); render(); });
window.addEventListener("hashchange", () => document.querySelectorAll(".toast").forEach((t) => t.remove()));

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
render();
