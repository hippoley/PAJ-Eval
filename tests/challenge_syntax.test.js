const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/challenge.html', 'utf8');
const packsSource = fs.readFileSync('docs/challenge-packs.js', 'utf8');

test('golden challenge market packs are valid JavaScript', () => {
  assert.doesNotThrow(() => new vm.Script(packsSource));
});

test('golden challenge inline script is syntactically valid', () => {
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(m => m[1])
    .filter(Boolean);
  assert.ok(scripts.length >= 1, 'expected inline challenge script');
  for (const source of scripts) assert.doesNotThrow(() => new vm.Script(source));
});

test('golden challenge exposes exactly ten explicit market packs', () => {
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  const packs = sandbox.window.PAJ_CHALLENGE_PACKS;
  assert.deepEqual(Object.keys(packs).sort(), ['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  const markets = Object.values(packs).map(p => p.market).sort();
  assert.deepEqual(markets, ['BR','CN','DE','ES','FR','JP','KR','RU','TW','US'].sort());
  for (const [locale, pack] of Object.entries(packs)) {
    assert.ok(pack.shop.products.length >= 2, `${locale} needs real product options`);
    assert.ok(pack.shop.devices.length >= 4, `${locale} needs inspectable owned devices`);
    assert.ok(pack.career.offers.length >= 2, `${locale} needs two offer worlds`);
    assert.ok(pack.travel.options.length >= 2, `${locale} needs two travel options`);
    assert.equal(pack.shop.nav.length, 5, `${locale} shop needs five ordinary navigation objects`);
    assert.equal(pack.career.nav.length, 6, `${locale} offer world needs six ordinary navigation objects`);
    assert.equal(pack.travel.nav.length, 5, `${locale} travel world needs five ordinary navigation objects`);
  }
});

test('market packs vary real-world surfaces rather than only language strings', () => {
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  new vm.Script(packsSource).runInContext(sandbox);
  const packs = sandbox.window.PAJ_CHALLENGE_PACKS;
  assert.notEqual(packs.en.travel.title, packs.zh-CN.travel.title);
  assert.notEqual(packs.ja.travel.nav[0], packs.ko.travel.nav[0]);
  assert.notEqual(packs.pt.currency, packs.es.currency);
  assert.match(packs.zh-TW.travel.title, /高雄/);
  assert.match(packs.de.travel.title, /Berlin/);
  assert.match(packs.ru.travel.title, /Москва/);
});
