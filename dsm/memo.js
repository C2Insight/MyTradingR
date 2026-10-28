// 투자 리서치 허브 — 잠금 해제와 메모 저장소. 허브(index.html)와 리포트(dsm/YYYY/DSM_*.html)가 함께 쓴다.
//
//   잠금 해제  dsm/auth.json = 잠금 화면 비밀번호로 암호화한 메모 저장소 접근 정보
//              (PBKDF2-SHA256 → AES-256-GCM, tools/make_auth.py 로 만든다). 풀리면 비밀번호가 맞은 것이고,
//              풀린 접근 정보는 이 탭의 sessionStorage 에만 둔다 (탭을 닫으면 다시 잠김).
//   메모       비공개 저장소의 memos/YYYY.json = {"YYYYMMDD": {"종목코드": {"t": 내용, "at": 저장 시각 ms}}}
//              같은 날짜·종목은 at 이 늦은 쪽이 이긴다 (지운 메모는 t="" 로 남김).
//              저장 전 입력은 localStorage 에 보관했다가 저장에 성공하면 지운다 → 창을 닫아도 다음에 다시 보낸다.

const AUTH_URL = new URL("auth.json", import.meta.url);
const SS_AUTH = "hub_auth", SS_MEMO = "dsm_memo";
const LS_PENDING = "dsm-memo-pending";
const API = "https://api.github.com";
const SAVE_DELAY = 2000;      // 입력이 멈춘 뒤 저장까지
const RETRY_DELAY = 30000;    // 저장 실패 후 다시 시도까지

// ── 인코딩 ───────────────────────────────────────────────
const bytes = b64 => Uint8Array.from(atob(b64.replace(/\s/g, "")), c => c.charCodeAt(0));
function toB64(str) {
  const b = new TextEncoder().encode(str);
  let bin = "";
  for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
  return btoa(bin);
}
const fromB64 = b64 => new TextDecoder().decode(bytes(b64));

// ── 잠금 해제 ────────────────────────────────────────────
export async function unlock(password) {
  const r = await fetch(`${AUTH_URL}?v=${Date.now()}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`잠금 설정 파일을 읽지 못했습니다 (${r.status})`);
  const a = await r.json();
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: bytes(a.salt), iterations: a.iter },
    base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  let plain;
  try {
    plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: bytes(a.iv) }, key, bytes(a.ct));
  } catch (e) {
    return false;                                     // 인증 태그 불일치 = 비밀번호 틀림
  }
  sessionStorage.setItem(SS_MEMO, new TextDecoder().decode(plain));
  sessionStorage.setItem(SS_AUTH, "1");
  return true;
}

export function isUnlocked() {
  try { return sessionStorage.getItem(SS_AUTH) === "1" && !!sessionStorage.getItem(SS_MEMO); } catch (e) { return false; }
}

function cred() {
  try { return JSON.parse(sessionStorage.getItem(SS_MEMO) || "null"); } catch (e) { return null; }
}

// ── GitHub (메모 저장소) ─────────────────────────────────
async function gh(method, path, body) {
  const c = cred();
  if (!c || !c.token) throw new Error("다시 로그인해 주세요");
  return fetch(`${API}/repos/${c.repo}${path}`, {
    method, cache: "no-store",
    headers: { Authorization: `Bearer ${c.token}`, Accept: "application/vnd.github+json",
      ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
}

function httpError(r) {
  const why = { 401: "메모 저장소 토큰이 만료됐거나 잘못됐습니다", 403: "메모 저장소 권한이 없습니다",
    404: "메모 저장소를 찾을 수 없습니다" }[r.status] || "GitHub 응답 오류";
  return new Error(`${why} (${r.status})`);
}

let repoChecked = false;
async function checkRepo() {               // 파일 404 가 '아직 없음'인지 '저장소 접근 불가'인지 구분
  if (repoChecked) return;
  const r = await gh("GET", "");
  if (!r.ok) throw httpError(r);
  repoChecked = true;
}

async function readYear(y) {
  const r = await gh("GET", `/contents/memos/${y}.json`);
  if (r.status === 404) { await checkRepo(); return { data: {}, sha: null }; }
  if (!r.ok) throw httpError(r);
  const j = await r.json();
  if (j.content) return { data: JSON.parse(fromB64(j.content)), sha: j.sha };
  const raw = await fetch(j.download_url, { cache: "no-store" });   // 1MB 넘는 파일은 content 가 비어 옴
  return { data: await raw.json(), sha: j.sha };
}

// 하루 한 줄 — 저장소 커밋 diff 에서 바뀐 날짜만 보이도록
const dumpYear = data => "{\n" + Object.keys(data).sort()
  .map(d => `${JSON.stringify(d)}:${JSON.stringify(data[d])}`).join(",\n") + "\n}\n";

function mergeInto(dst, src) {
  for (const [d, byCode] of Object.entries(src || {})) {
    for (const [c, m] of Object.entries(byCode || {})) {
      if (!m || typeof m.t !== "string") continue;
      const cur = dst[d] && dst[d][c];
      if (!cur || (m.at || 0) > (cur.at || 0)) (dst[d] ||= {})[c] = { t: m.t, at: m.at || 0 };
    }
  }
  return dst;
}

async function writeYear(y, part) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const { data, sha } = await readYear(y);
    mergeInto(data, part);
    const r = await gh("PUT", `/contents/memos/${y}.json`, {
      message: `메모 ${Object.keys(part).sort().join(", ")}`, content: toB64(dumpYear(data)), ...(sha ? { sha } : {}) });
    if (r.ok) return;
    if (r.status !== 409 && r.status !== 422) throw httpError(r);   // 409·422 = 다른 기기·탭이 먼저 저장 → 다시 읽어 합침
  }
  throw new Error("다른 기기와 저장이 겹쳐 실패했습니다");
}

// ── 저장 전 입력 (localStorage, 탭끼리 공유) ─────────────
function readPending() {
  try { return JSON.parse(localStorage.getItem(LS_PENDING) || "{}"); } catch (e) { return {}; }
}
function writePending(p) {
  try {
    if (Object.keys(p).length) localStorage.setItem(LS_PENDING, JSON.stringify(p));
    else localStorage.removeItem(LS_PENDING);
  } catch (e) { /* 저장소 없음 — 메모리에서만 보냄 */ }
}
function dropSaved(batch) {                // 보낸 뒤 그사이 다시 고친 메모(at 이 다름)는 남긴다
  const p = readPending();
  for (const [d, byCode] of Object.entries(batch)) {
    for (const [c, m] of Object.entries(byCode)) if (p[d] && p[d][c] && p[d][c].at === m.at) delete p[d][c];
    if (p[d] && !Object.keys(p[d]).length) delete p[d];
  }
  writePending(p);
}
const keysOf = b => Object.entries(b).flatMap(([d, byCode]) => Object.keys(byCode).map(c => [d, c]));

// ── 공개 API ─────────────────────────────────────────────
const listeners = new Set();
/** 저장 상태 알림 fn(state "saving"|"saved"|"error", [[날짜, 종목]...], error) */
export const onChange = fn => listeners.add(fn);
const emit = (state, keys, err) => listeners.forEach(fn => { try { fn(state, keys, err); } catch (e) { /* 화면 쪽 오류 무시 */ } });

/** 여러 해의 메모 + 아직 못 보낸 입력 → {YYYYMMDD: {종목: {t, at}}} */
export async function load(years) {
  const files = await Promise.all([...new Set(years.map(String))].map(readYear));
  const out = {};
  files.forEach(f => mergeInto(out, f.data));
  const p = readPending();
  mergeInto(out, p);
  if (Object.keys(p).length) flush();
  return out;
}

export const isPending = (date, code) => !!(readPending()[date] || {})[code];
export const hasPending = () => Object.keys(readPending()).length > 0;

let timer = null, retryTimer = null, chain = Promise.resolve();
/** 메모 입력 — 이 기기에 보관하고, 입력이 멈추면 저장 */
export function set(date, code, text) {
  const p = readPending();
  (p[date] ||= {})[code] = { t: text, at: Date.now() };
  writePending(p);
  clearTimeout(timer);
  timer = setTimeout(flush, SAVE_DELAY);
}

/** 보관 중인 입력을 지금 저장 (한 번에 하나씩) */
export function flush() {
  clearTimeout(timer);
  chain = chain.then(flushNow, flushNow);
  return chain;
}

async function flushNow() {
  const batch = readPending();
  if (!Object.keys(batch).length) return;
  const keys = keysOf(batch);
  emit("saving", keys);
  try {
    const byYear = {};
    for (const [d, byCode] of Object.entries(batch)) (byYear[d.slice(0, 4)] ||= {})[d] = byCode;
    for (const [y, part] of Object.entries(byYear)) await writeYear(y, part);
    dropSaved(batch);
    emit("saved", keys);
  } catch (e) {
    emit("error", keys, e);
    clearTimeout(retryTimer);
    retryTimer = setTimeout(flush, RETRY_DELAY);
  }
}
