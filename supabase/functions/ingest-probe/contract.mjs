export const GOLDEN_CONSENT='golden-consent-v1';
export const GOLDEN_STUDY='golden-study-v1';
export const GOLDEN_ENVELOPE='golden-event-envelope-v1';

export const MARKET_BY_LOCALE={
  en:'US','zh-CN':'CN','zh-TW':'TW',ja:'JP',ko:'KR',es:'ES',fr:'FR',de:'DE',pt:'BR',ru:'RU'
};

export const GOLDEN_SPECS={
  PF01:{instrument:'golden-challenge-v2',world:'golden-three-world-v1'},
  PF02:{instrument:'golden-pf02-v1',world:'golden-three-world-v1'},
  PF03:{instrument:'golden-pf03-v1',world:'golden-three-world-v1'},
  PF04:{instrument:'golden-pf04-v1',world:'golden-three-world-v1'},
  PF05:{instrument:'golden-pf05-v1',world:'golden-three-world-v1'},
  PF06:{instrument:'golden-pf06-v1',world:'golden-three-world-v1'},
  PF07:{instrument:'golden-pf07-v1',world:'golden-three-world-v1'},
  PF08:{instrument:'golden-pf08-v1',world:'golden-open-workspaces-v1'}
};

export function isGoldenAttempt({consent,instrument,studyVersion}){
  return consent===GOLDEN_CONSENT || studyVersion===GOLDEN_STUDY || String(instrument||'').startsWith('golden-');
}

export function validateGoldenSubmission({locale,consent,instrument,family,world,studyVersion,market,events}){
  if(!isGoldenAttempt({consent,instrument,studyVersion})) return null;
  const spec=GOLDEN_SPECS[family];
  if(!spec || instrument!==spec.instrument || world!==spec.world) return 'golden_contract_mismatch';
  if(consent!==GOLDEN_CONSENT) return 'golden_consent_required';
  if(studyVersion!==GOLDEN_STUDY) return 'golden_study_version_required';
  if(MARKET_BY_LOCALE[locale]!==market) return 'golden_market_mismatch';
  if(!Array.isArray(events)||events.length<4) return 'golden_trace_too_short';

  let lastSeq=0,lastT=-1;
  const types=[];
  for(const e of events){
    if(!e||typeof e!=='object') return 'golden_event_invalid';
    const seq=Number(e.seq),t=Number(e.t??e.t_ms);
    if(!Number.isInteger(seq)||seq<=lastSeq) return 'golden_sequence_invalid';
    if(!Number.isFinite(t)||t<lastT) return 'golden_time_invalid';
    if(e.locale!==locale) return 'golden_event_locale_mismatch';
    if(e.market!==market) return 'golden_event_market_mismatch';
    if(e.study_version!==GOLDEN_STUDY) return 'golden_event_study_mismatch';
    if(e.envelope_version!==GOLDEN_ENVELOPE) return 'golden_envelope_required';
    if(typeof e.raw_event_type!=='string'||!e.raw_event_type) return 'golden_raw_event_type_required';
    if(!e.raw_event||typeof e.raw_event!=='object'||Array.isArray(e.raw_event)) return 'golden_raw_event_required';
    const type=String(e.event||e.type||'');
    if(!/^[a-z][a-z0-9_:-]{0,79}$/i.test(type)) return 'golden_event_type_invalid';
    types.push(type);lastSeq=seq;lastT=t;
  }
  if(types[0]!=='session_start') return 'golden_session_start_required';
  if(types[types.length-1]!=='session_complete') return 'golden_session_complete_required';
  if(!types.includes('commit')) return 'golden_commit_required';
  return null;
}
