const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const index = fs.readFileSync('docs/index.html', 'utf8');
const worldLocales = fs.readFileSync('docs/world-locales.js', 'utf8');

test('world locale catalog is valid JavaScript', () => {
  assert.doesNotThrow(() => new vm.Script(worldLocales));
});

test('canonical player inline script is syntactically valid', () => {
  const scripts = [...index.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(m => m[1])
    .filter(Boolean);
  assert.ok(scripts.length >= 1, 'expected inline player script');
  for (const source of scripts) {
    assert.doesNotThrow(() => new vm.Script(source));
  }
});

test('world locales expose exactly the ten supported locale keys', () => {
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  new vm.Script(worldLocales).runInContext(sandbox);
  const keys = Object.keys(sandbox.window.PAJ_WORLD_LOCALES).sort();
  assert.deepEqual(keys, ['de','en','es','fr','ja','ko','pt','ru','zh-CN','zh-TW'].sort());
  const baseline = Object.keys(sandbox.window.PAJ_WORLD_LOCALES.en).sort();
  for (const locale of keys) {
    assert.deepEqual(Object.keys(sandbox.window.PAJ_WORLD_LOCALES[locale]).sort(), baseline,
      `world locale ${locale} must expose the same keys as en`);
  }
});
