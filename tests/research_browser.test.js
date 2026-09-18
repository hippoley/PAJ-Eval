const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const html=fs.readFileSync('docs/research.html','utf8');

function inlineSource(){
  const start=html.lastIndexOf('<script>');
  const end=html.lastIndexOf('</script>');
  assert.ok(start>=0&&end>start);
  return html.slice(start+'<script>'.length,end);
}

test('research browser inline script is valid JavaScript',()=>{
  assert.doesNotThrow(()=>new vm.Script(inlineSource()));
});

test('researcher link generator exposes neutral journey numbers and ten locales',()=>{
  const source=inlineSource();
  assert.ok(source.includes("const JOURNEYS=['01','02','03','04','05','06','07','08']"));
  for(const locale of ['en','zh-CN','zh-TW','ja','ko','es','fr','de','pt','ru']) assert.ok(source.includes("'"+locale+"'"),locale);
  assert.ok(source.includes("new URL('study.html',location.href)"));
  assert.ok(source.includes("u.searchParams.set('journey'"));
  assert.ok(source.includes("u.searchParams.set('locale'"));
  assert.ok(!source.includes("searchParams.set('family'"));
  assert.ok(!source.includes('?family=PF'));
});

test('neutral link generator is researcher-only UI',()=>{
  assert.ok(html.includes('id="browser" class="hidden"'));
  assert.ok(html.includes('id="inviteUrl" readonly'));
  assert.ok(html.includes('Formal study link'));
  assert.ok(html.includes('Copied neutral study link.'));
});

test('research replay still expands raw payload json',()=>{
  const source=inlineSource();
  assert.ok(source.includes('payload_json'));
  assert.ok(source.includes('JSON.stringify(e.payload_json||{},null,2)'));
  assert.ok(html.includes('app_metadata.role = researcher'));
  assert.ok(source.includes('consented_at_client'));
  assert.ok(source.includes('study_version'));
  assert.ok(source.includes('market'));
});
