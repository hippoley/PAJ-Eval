const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/stage.html','utf8');

function inlineSource(){
  const start=html.lastIndexOf('<script>');
  const end=html.lastIndexOf('</script>');
  assert.ok(start>=0&&end>start);
  return html.slice(start+'<script>'.length,end);
}

test('stage preview script is valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(inlineSource()));
});

test('stage preview exposes all eight neutral journeys and ten locales',()=>{
  const s=inlineSource();
  for(const id of ['01','02','03','04','05','06','07','08']) assert.ok(s.includes("['"+id+"'"),id);
  for(const locale of ['zh-CN','zh-TW','en','ja','ko','es','fr','de','pt','ru']) assert.ok(s.includes("['"+locale+"'"),locale);
  assert.ok(s.includes('run.html?journey='));
  assert.ok(s.includes('study.html?journey=01'));
});

test('stage page clearly separates preview from formal participant entry',()=>{
  assert.match(html,/阶段性可玩版本/);
  assert.match(html,/这个页面是给我们看研发阶段的/);
  assert.match(html,/真正发给参与者的入口/);
  assert.match(html,/Operational release · BLOCKED/);
});

test('stage page does not turn its dev copy into a participant research surface',()=>{
  const s=inlineSource();
  assert.ok(!s.includes('PAJTransport'));
  assert.ok(!s.includes('ingest-probe'));
  assert.ok(!s.includes('sessionStorage.setItem'));
  assert.ok(!s.includes('indexedDB'));
});
