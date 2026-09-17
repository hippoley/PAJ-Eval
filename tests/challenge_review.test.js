const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync('docs/challenge-review.html','utf8');

test('challenge replay inline script is valid JavaScript',()=>{
  const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).filter(Boolean);
  assert.ok(scripts.length>=1);
  for(const s of scripts) assert.doesNotThrow(()=>new vm.Script(s));
});

test('challenge replay is local-only and score-free',()=>{
  for(const forbidden of ['fetch(','XMLHttpRequest','supabase','ingest-probe','PAJTransport']) assert.ok(!html.includes(forbidden),forbidden);
  assert.ok(html.includes('NO NETWORK'));
  assert.ok(html.includes('No score is computed here'));
  assert.ok(html.includes("p.instrument!=='golden-challenge-v2'"));
});

test('challenge replay exposes the planned descriptive transfer features',()=>{
  for(const token of [
    'seed_precommit_evidence_count',
    'seed_nested_evidence_count',
    'seed_revision_after_consequence',
    'near_transfer_nested_count',
    'near_transfer_breadth',
    'far_precommit_breadth',
    'far_arrival_plan_opened',
    'far_nested_count',
    'far_revision_after_consequence',
    'inspection_targetedness',
  ]) assert.ok(html.includes(token),token);
});
