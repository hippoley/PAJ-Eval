const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/challenge-suite.html','utf8');

test('challenge suite inline script is valid JavaScript',()=>{
  const start=html.lastIndexOf('<script>');
  const end=html.lastIndexOf('</script>');
  assert.ok(start>=0 && end>start);
  const source=html.slice(start+'<script>'.length,end);
  assert.doesNotThrow(()=>new vm.Script(source));
});

test('challenge suite links all eight playable journeys exactly once',()=>{
  const expected=['challenge.html','challenge-pf02.html','challenge-pf03.html','challenge-pf04.html','challenge-pf05.html','challenge-pf06.html','challenge-pf07.html','challenge-pf08.html'];
  for(const path of expected) assert.equal(html.split(path).length-1,1,path);
});

test('challenge suite offers exactly ten explicit market locales',()=>{
  for(const locale of ['zh-CN','zh-TW','en','ja','ko','es','fr','de','pt','ru']) assert.ok(html.includes("['"+locale+"'"),locale);
});

test('showcase clearly separates preview from formal research ingestion',()=>{
  assert.match(html,/Preview mode is local-only/i);
  assert.match(html,/direct journey link/i);
  assert.match(html,/not connected to canonical research ingestion/i);
  assert.ok(!html.includes('PAJTransport'));
  assert.ok(!html.toLowerCase().includes('supabase'));
});

test('showcase uses neutral journey names rather than latent construct labels',()=>{
  for(const forbidden of ['hidden downstream constraints','competing causal frames','omitted evidence','anomaly triage','premature stopping','wrong problem','spontaneous opening']) assert.ok(!html.toLowerCase().includes(forbidden),forbidden);
});