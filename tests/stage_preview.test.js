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
  for(const id of ['01','02','03','04','05','06','07','08']) assert.ok(s.includes("{id:'"+id+"'"),id);
  for(const locale of ['zh-CN','zh-TW','en','ja','ko','es','fr','de','pt','ru']) assert.ok(s.includes("['"+locale+"'"),locale);
  assert.ok(s.includes('run.html?journey='));
  assert.ok(s.includes("'study.html?journey='+j.id"));
  assert.ok(s.includes("+'&preview=1'"));
});

test('stage page clearly separates preview from formal participant entry',()=>{
  assert.match(html,/直接玩。/);
  assert.match(html,/Stage 只是一个试验台/);
  assert.match(html,/真正要打磨的东西/);
  assert.match(html,/Browser → replay smoke/);
  assert.match(html,/Stage preview 本身不写正式研究数据/);
});

test('stage page does not turn its dev copy into a participant research surface',()=>{
  const s=inlineSource();
  assert.ok(!s.includes('PAJTransport'));
  assert.ok(!s.includes('ingest-probe'));
  assert.ok(!s.includes('sessionStorage.setItem'));
  assert.ok(!s.includes('indexedDB'));
});


test('stage embeds the real journey instead of a static card catalog',()=>{
  const source=inlineSource();
  assert.ok(html.includes('id="frame" class="frame"'));
  assert.ok(source.includes("$('frame').src=previewUrl(j)"));
  assert.ok(source.includes("const previewRoutes="));
  assert.ok(source.includes('fitFrame()'));
  assert.ok(source.includes("$('reload').addEventListener"));
  assert.ok(source.includes("$('next').addEventListener"));
  assert.ok(source.includes("document.querySelectorAll('.journeyBtn')"));
});
