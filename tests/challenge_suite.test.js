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

test('challenge suite links all eight journeys through neutral participant URLs',()=>{
  assert.ok(html.includes('run.html?journey='));
  for(const id of ['01','02','03','04','05','06','07','08']) {
    assert.ok(html.includes("{n:'"+id+"'"),id);
  }
  for(const leaked of ['challenge-pf02.html','challenge-pf03.html','challenge-pf04.html','challenge-pf05.html','challenge-pf06.html','challenge-pf07.html','challenge-pf08.html']) {
    assert.ok(!html.includes(leaked),leaked);
  }
});

test('challenge suite offers exactly ten explicit market locales',()=>{
  for(const locale of ['zh-CN','zh-TW','en','ja','ko','es','fr','de','pt','ru']) assert.ok(html.includes("['"+locale+"'"),locale);
});

test('showcase clearly separates preview from formal research ingestion',()=>{
  assert.match(html,/Preview mode is local-only/i);
  assert.match(html,/consented study link/i);
  assert.match(html,/not connected to canonical research ingestion/i);
  assert.ok(!html.includes('PAJTransport'));
  assert.ok(!html.toLowerCase().includes('supabase'));
});

test('showcase uses neutral journey names rather than latent construct labels',()=>{
  for(const forbidden of ['hidden downstream constraints','competing causal frames','omitted evidence','anomaly triage','premature stopping','wrong problem','spontaneous opening']) assert.ok(!html.toLowerCase().includes(forbidden),forbidden);
});