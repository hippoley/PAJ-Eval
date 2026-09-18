const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/challenge.html', 'utf8');
const packsSource = fs.readFileSync('docs/challenge-packs.js', 'utf8');
const depthSource = fs.readFileSync('docs/challenge-depth.js', 'utf8');

function load() {
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  new vm.Script(depthSource).runInContext(sandbox);
  return sandbox.window;
}

function digits(s) { return String(s).replace(/\D/g, ''); }

test('golden depth catalog is valid JavaScript', () => {
  assert.doesNotThrow(() => new vm.Script(depthSource));
});

test('depth catalog exactly matches the ten market-pack locales', () => {
  const win = load();
  const packKeys = Object.keys(win.PAJ_CHALLENGE_PACKS).sort();
  const depthKeys = Object.keys(win.PAJ_CHALLENGE_DEPTH).sort();
  assert.deepEqual(depthKeys, packKeys);
  assert.equal(depthKeys.length, 10);
});

test('every market has localized seed and far-transfer consequence copy', () => {
  const win = load();
  for (const [locale, d] of Object.entries(win.PAJ_CHALLENGE_DEPTH)) {
    assert.ok(d.marketNote.length > 8, `${locale}: market note`);
    assert.ok(d.checkout.proConsequence.length > 30, `${locale}: Pro consequence`);
    assert.ok(d.checkout.proLine1.length > 10, `${locale}: Pro intervention line`);
    assert.ok(d.career.mobility.length > 2, `${locale}: mobility object`);
    assert.ok(d.career.a.length > 20 && d.career.b.length > 20, `${locale}: mobility details`);
    assert.ok(d.travel.lateNotice.length > 20, `${locale}: late arrival consequence`);
    assert.ok(d.travel.earlyNotice.length > 20, `${locale}: early arrival state`);
    assert.ok(d.travel.transportExtra.length > 30, `${locale}: transport nested evidence`);
    assert.ok(d.travel.hotelExtra.length > 30, `${locale}: hotel nested evidence`);
    assert.ok(d.travel.morningExtra.length > 30, `${locale}: morning nested evidence`);
  }
});

test('localized Pro intervention line names the actual market-pack Pro price', () => {
  const win = load();
  for (const [locale, pack] of Object.entries(win.PAJ_CHALLENGE_PACKS)) {
    const pro = pack.shop.products.find(p => p.kind === 'pro');
    const expected = digits(pro.price);
    const actual = digits(win.PAJ_CHALLENGE_DEPTH[locale].checkout.proLine1);
    assert.ok(actual.includes(expected), `${locale}: ${pro.price} must appear in Pro consequence line`);
  }
});

test('market-specific late-arrival facts remain aligned in non-generic packs', () => {
  const win = load();
  assert.match(win.PAJ_CHALLENGE_DEPTH.ko.travel.lateNotice, /00:07/);
  assert.match(win.PAJ_CHALLENGE_DEPTH.ru.travel.lateNotice, /07:35/);
  assert.match(win.PAJ_CHALLENGE_DEPTH['zh-CN'].travel.lateNotice, /00:35/);
  assert.match(win.PAJ_CHALLENGE_DEPTH.ja.travel.lateNotice, /23:45/);
});

test('PF01 seed exposes consequence on both headline product choices', () => {
  assert.match(html, /p\.kind==='lite'\?'bridge':'delivery'/);
  assert.match(html, /D\.checkout\.proConsequence/);
  assert.match(html, /pickup_option/);
  assert.match(html, /affected_devices/);
});

test('PF01 seed records consequence exposure and a terminal seed commit', () => {
  assert.ok(html.includes("log('consequence_exposed',{world:'shop'"));
  assert.ok(html.includes("log('commit',{world:'shop'"));
});

test('near transfer has nested mobility evidence separate from contract and team', () => {
  assert.match(html, /class="btn mobility"/);
  assert.match(html, /careerDetail\(b\.dataset\.k,'mobility'\)/);
  assert.match(html, /object:type\+'_'\+k/);
});

test('far transfer uses provisional action, consequence, revision, and generated nested evidence', () => {
  for (const token of [
    'provisional_commit',
    'renderTravelHold',
    'arrival_plan',
    'switch_time',
    'finalizeTravel',
    "object:b.dataset.kind+'_nested'",
    'D.travel.transportExtra',
    'D.travel.hotelExtra',
    'D.travel.morningExtra',
  ]) assert.ok(html.includes(token), token);
});

test('golden challenge remains local-only', () => {
  assert.ok(html.includes("instrument:'golden-challenge-v2'"));
  assert.ok(!html.includes('PAJTransport'));
  assert.ok(!html.toLowerCase().includes('supabase'));
  assert.ok(!html.includes('ingest-probe'));
});
