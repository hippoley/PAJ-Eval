(function(root){
  const STUDY_KEY='paj_golden_study_v1';
  const JOURNEY_FAMILY={'01':'PF01','02':'PF02','03':'PF03','04':'PF04','05':'PF05','06':'PF06','07':'PF07','08':'PF08'};
  const ENDPOINT='https://pwdcgfvarudhqezlzwmx.supabase.co/functions/v1/ingest-probe';
  const MAX_AGE_MS=4*60*60*1000;
  const COPY={
    'zh-CN':{saving:'正在保存研究记录…',saved:'研究记录已保存。你现在可以关闭此页面。',queued:'网络暂时不可用。记录已安全排队，恢复联网后会重试。',invalid:'当前页面不是有效的正式研究会话。'},
    'zh-TW':{saving:'正在儲存研究紀錄…',saved:'研究紀錄已儲存。你現在可以關閉此頁面。',queued:'網路暫時不可用。紀錄已安全排隊，恢復連線後會重試。',invalid:'目前頁面不是有效的正式研究工作階段。'},
    en:{saving:'Saving research record…',saved:'Research record saved. You may close this page.',queued:'Network unavailable. The record is safely queued and will retry when connectivity returns.',invalid:'This page is not an active formal research session.'},
    ja:{saving:'研究記録を保存しています…',saved:'研究記録を保存しました。このページを閉じて構いません。',queued:'ネットワークに接続できません。記録は安全にキューされ、接続回復後に再試行します。',invalid:'このページは有効な正式研究セッションではありません。'},
    ko:{saving:'연구 기록을 저장하는 중…',saved:'연구 기록이 저장되었습니다. 이제 이 페이지를 닫아도 됩니다.',queued:'네트워크를 사용할 수 없습니다. 기록은 안전하게 대기열에 저장되며 연결이 복구되면 다시 시도합니다.',invalid:'현재 페이지는 유효한 정식 연구 세션이 아닙니다.'},
    es:{saving:'Guardando el registro de investigación…',saved:'Registro guardado. Ya puedes cerrar esta página.',queued:'Sin red. El registro quedó en una cola segura y se reintentará al recuperar conexión.',invalid:'Esta página no es una sesión formal de investigación activa.'},
    fr:{saving:'Enregistrement de la session de recherche…',saved:'Enregistrement terminé. Vous pouvez fermer cette page.',queued:'Réseau indisponible. La session est mise en file d’attente de façon sûre et sera renvoyée au retour du réseau.',invalid:'Cette page ne correspond pas à une session de recherche formelle active.'},
    de:{saving:'Forschungsdatensatz wird gespeichert…',saved:'Forschungsdatensatz gespeichert. Du kannst diese Seite schließen.',queued:'Kein Netzwerk. Der Datensatz ist sicher in der Warteschlange und wird bei Verbindung erneut gesendet.',invalid:'Diese Seite ist keine aktive formale Forschungssitzung.'},
    pt:{saving:'Salvando o registro de pesquisa…',saved:'Registro salvo. Você já pode fechar esta página.',queued:'Sem rede. O registro foi enfileirado com segurança e será reenviado quando a conexão voltar.',invalid:'Esta página não é uma sessão formal de pesquisa ativa.'},
    ru:{saving:'Сохраняем запись исследования…',saved:'Запись сохранена. Эту страницу можно закрыть.',queued:'Сети нет. Запись безопасно поставлена в очередь и будет отправлена после восстановления связи.',invalid:'Эта страница не является активной формальной исследовательской сессией.'}
  };
  let transport=null,activeWork=null,depsPromise=null;
  function loadScript(src){return new Promise((resolve,reject)=>{const el=document.createElement('script');el.src=src;el.async=false;el.onload=()=>resolve();el.onerror=()=>reject(new Error('dependency_load_failed:'+src));document.head.appendChild(el)})}
  function ensureDeps(){if(depsPromise)return depsPromise;depsPromise=(async()=>{if(!root.PAJGoldenEvents)await loadScript('golden-event-normalizer.js');if(!root.PAJTransport)await loadScript('transport.js')})();return depsPromise}

  function readContext(){
    try{
      if(new URLSearchParams(location.search).get('study')!=='1') return null;
      const raw=sessionStorage.getItem(STUDY_KEY);
      if(!raw) return null;
      const ctx=JSON.parse(raw);
      if(!ctx||ctx.consent_version!=='golden-consent-v1') return null;
      const family=ctx.family||JOURNEY_FAMILY[String(ctx.journey||'')];
      if(!/^PF0[1-8]$/.test(String(family||''))) return null;
      if(!/^[0-9a-f-]{36}$/i.test(String(ctx.client_submission_id||''))) return null;
      if(!Number.isFinite(ctx.issued_at)||Date.now()-ctx.issued_at>MAX_AGE_MS) return null;
      return {...ctx,family};
    }catch{return null}
  }
  function textFor(locale,key){return (COPY[locale]||COPY.en)[key]}
  function lockFormalSurface(ctx){const apply=()=>{const sel=document.getElementById('locale');if(sel){sel.value=ctx.locale;sel.disabled=true;sel.setAttribute('aria-disabled','true')}};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply,{once:true});else apply()}
  function ensureStatus(){
    let el=document.getElementById('goldenStudyStatus');
    if(el)return el;
    el=document.createElement('div');el.id='goldenStudyStatus';
    el.style.cssText='position:fixed;right:16px;bottom:16px;z-index:99999;max-width:360px;padding:13px 15px;border:1px solid #d7d1c6;border-radius:12px;background:#fffefa;box-shadow:0 12px 36px #0002;font:13px/1.45 system-ui,sans-serif;color:#333';
    el.hidden=true;document.body.appendChild(el);return el;
  }
  function setStatus(locale,key,detail=''){
    const el=ensureStatus();el.hidden=false;el.textContent=textFor(locale,key)+(detail?' '+detail:'');
    el.dataset.state=key;
  }
  function getTransport(){
    if(!transport){
      if(!root.PAJTransport)throw new Error('transport_unavailable');
      transport=root.PAJTransport.createBrowserTransport(ENDPOINT,{dbName:'paj-golden-study-queue-v1'});
    }
    return transport;
  }
  function validMeta(meta,ctx){
    if(!meta||meta.family!==ctx.family)throw new Error('study_family_mismatch');
    if(meta.locale!==ctx.locale)throw new Error('study_locale_mismatch');
    if(typeof meta.market!=='string'||!meta.market)throw new Error('study_market_missing');
    if(typeof meta.instrument_version!=='string'||!meta.instrument_version)throw new Error('study_instrument_missing');
    if(!Array.isArray(meta.events)||!meta.events.length)throw new Error('study_events_missing');
  }
  async function complete(meta){
    const ctx=readContext();
    if(!ctx)return {state:'preview'};
    if(ctx.completed&&ctx.session_id){setStatus(ctx.locale,'saved');return {state:'saved',session_id:ctx.session_id,client_submission_id:ctx.client_submission_id}}
    if(activeWork)return activeWork;
    activeWork=(async()=>{
      validMeta(meta,ctx);
      setStatus(ctx.locale,'saving');
      await ensureDeps();
      const normalized=root.PAJGoldenEvents
        ? root.PAJGoldenEvents.normalizeTrace({family:ctx.family,locale:ctx.locale,market:meta.market,instrument_version:meta.instrument_version},meta.events)
        : {events:meta.events.map((e,i)=>({seq:e.seq||i+1,t_ms:e.t_ms??e.t??0,event:e.type||e.event||'unknown',world:e.world||e.screen||null,target:e.object||e.target||e.action||e.choice||null,raw_event:e}))};
      const events=normalized.events.map((e,i)=>({
        seq:e.seq||i+1,
        t:e.t_ms??0,
        event:e.event,
        target:e.target||'',
        screen:e.world||'',
        locale:ctx.locale,
        market:meta.market,
        study_version:'golden-study-v1',
        phase:e.raw_event?.phase||'',
        envelope_version:e.envelope_version||'golden-event-envelope-v1',
        raw_event_type:e.raw_event_type||e.event,
        raw_event:e.raw_event||meta.events[i]
      }));
      const payload={
        client_submission_id:ctx.client_submission_id,
        consent_version:ctx.consent_version,
        locale:ctx.locale,
        instrument_version:meta.instrument_version,
        probe_family:ctx.family,
        world_variant:meta.world_variant||'golden-three-world-v1',
        terminal_action:meta.terminal_action||'',
        market:meta.market,
        study_version:'golden-study-v1',
        events
      };
      const result=await getTransport().submit(payload);
      if(result.state==='saved'){
        const next={...ctx,completed:true,session_id:result.session_id,completed_at:Date.now()};
        sessionStorage.setItem(STUDY_KEY,JSON.stringify(next));
        setStatus(ctx.locale,'saved');
      }else setStatus(ctx.locale,'queued');
      return result;
    })();
    try{return await activeWork}finally{activeWork=null}
  }
  async function retryConsentedQueue(){
    const ctx=readContext();if(!ctx)return [];
    try{
      await ensureDeps();
      const results=await getTransport().retryAll();
      const saved=results.find(x=>x.client_submission_id===ctx.client_submission_id&&x.state==='saved');
      if(saved){
        sessionStorage.setItem(STUDY_KEY,JSON.stringify({...ctx,completed:true,session_id:saved.session_id,completed_at:Date.now()}));
        setStatus(ctx.locale,'saved');
      }
      return results;
    }catch{return []}
  }
  const api={STUDY_KEY,readContext,complete,retryConsentedQueue};
  root.PAJGoldenStudy=api;
  const ctx=readContext();
  if(ctx){
    lockFormalSurface(ctx);
    window.addEventListener('online',()=>retryConsentedQueue());
    queueMicrotask(()=>retryConsentedQueue());
  }
})(window);