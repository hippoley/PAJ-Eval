const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/run.html','utf8');

function inlineSource(){
  const start=html.lastIndexOf('<script>');
  const end=html.lastIndexOf('</script>');
  assert.ok(start>=0&&end>start);
  return html.slice(start+'<script>'.length,end);
}

test('neutral run router script is valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(inlineSource()));
});

test('neutral run router covers all eight journeys and ten locales',()=>{
  const source=inlineSource();
  for(const id of ['01','02','03','04','05','06','07','08']) assert.ok(source.includes("'"+id+"':"),id);
  for(const locale of ['en','zh-CN','zh-TW','ja','ko','es','fr','de','pt','ru']) assert.ok(source.includes("'"+locale+"'"),locale);
});

test('participant-visible router copy contains no PF identifiers or construct labels',()=>{
  const visible=html.replace(/<script[\s\S]*?<\/script>/gi,' ').replace(/<style[\s\S]*?<\/style>/gi,' ').replace(/<[^>]+>/g,' ');
  assert.ok(!/PF0[1-8]/i.test(visible));
  for(const forbidden of ['hidden downstream constraints','competing causal frames','omitted evidence','premature stopping','wrong problem','spontaneous opening']){
    assert.ok(!visible.toLowerCase().includes(forbidden),forbidden);
  }
});

test('router forwards study mode only when explicitly requested',()=>{
  const source=inlineSource();
  assert.ok(source.includes("study=p.get('study')==='1'"));
  assert.ok(source.includes("if(study)q.set('study','1')"));
  assert.ok(source.includes("document.getElementById('frame').src=ROUTES[journey]+'?'+q.toString()"));
});
