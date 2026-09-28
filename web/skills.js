'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const key = 'predictkit-studio-theme', themes = new Set(['solana-signal','trust-layer','studio-classic']);
  const token = document.querySelector('meta[name="predictkit-token"]').content;
  const phases = {discovery:'Discover',decision:'Align & approve',build:'Build in parallel',review:'Review'};
  const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let catalog, toastTimer, loadSequence=0;
  try {const saved=localStorage.getItem(key);if(themes.has(saved))document.documentElement.dataset.theme=saved;} catch {}
  $('catalog-theme').value=document.documentElement.dataset.theme;
  $('catalog-theme').addEventListener('change',()=>{const theme=$('catalog-theme').value;if(!themes.has(theme))return;document.documentElement.dataset.theme=theme;try{localStorage.setItem(key,theme);}catch{}});
  function toast(message){clearTimeout(toastTimer);$('catalog-toast').textContent=message;$('catalog-toast').hidden=false;toastTimer=setTimeout(()=>$('catalog-toast').hidden=true,4500);}
  const roleTitle=id=>catalog?.roles.find(role=>role.id===id)?.title||id;
  const textList=(items,className='')=>`<ul${className?` class="${className}"`:''}>${(items||[]).map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`;
  const pathList=paths=>`<ul class="contract-paths">${paths.map(path=>`<li><code>${esc(path)}</code></li>`).join('')}</ul>`;
  function skillOwnership(item){
    if(!item.primary_role)return '';
    const others=(item.used_by||[]).filter(id=>id!==item.primary_role);
    return `<dl class="skill-ownership"><div><dt>Primary role</dt><dd>${esc(roleTitle(item.primary_role))}</dd></div>${others.length?`<div><dt>Also used by</dt><dd>${esc(others.map(roleTitle).join(', '))}</dd></div>`:''}</dl>`;
  }
  function sourceHTML(item,{role=false}={}){
    const id=role?'role-'+item.id:item.id;
    return `<details class="skill-source" data-source="${esc(id)}"><summary><span class="skill-source-icon" aria-hidden="true">${role?'ROLE':'SKILL'}</span><span><strong>${esc(role?'Read the full role instructions':item.name||item.id)}</strong><small>${esc(role?item.role_path:item.description)}</small></span></summary>${role?'':skillOwnership(item)}<div class="source-toolbar"><code>${esc(role?item.role_path:item.path)}</code><button class="button quiet" type="button" data-copy="${esc(id)}">Copy text</button></div><pre class="source-content" tabindex="0" aria-label="${esc((role?item.title:item.name)+' instructions')}">${esc(role?item.role_content:item.content)}</pre>${item.sha256?`<p class="source-hash">SHA-256 ${esc(item.sha256)}</p>`:''}</details>`;
  }
  function capabilityHTML(profile){
    if(!profile)return '';
    return `<section class="role-capabilities"><h3>What this role helps you do</h3>${textList(profile.can_do,'capability-actions')}<div class="capability-example"><h4>Example assignment</h4><p>${esc(profile.example)}</p></div></section>`;
  }
  function acceptanceHTML(profile){
    if(!profile)return '';
    return `<section class="role-acceptance"><h3>How the output is checked</h3><p>The coordinator runs these static checks on each result. They check the file contract; they do not prove the work is correct.</p><ul class="acceptance-list">${(profile.acceptance_checks||[]).map(check=>`<li><span class="acceptance-type">Static check</span><span>${esc(check.label)}</span></li>`).join('')}</ul><details class="capability-disclosure"><summary>Questions that still need judgment <span>${profile.review_questions?.length||0}</span></summary>${textList(profile.review_questions)}</details><details class="capability-disclosure"><summary>Where this role stops</summary>${textList(profile.cannot_do)}<p>${esc(profile.execution)}</p></details></section>`;
  }
  function selectRole(id,{focus=false,updateURL=true}={}){
    const role=catalog.roles.find(r=>r.id===id);if(!role)return;
    for(const button of document.querySelectorAll('[data-role]'))button.setAttribute('aria-pressed',String(button.dataset.role===id));
    const deps=role.depends_on.map(dep=>catalog.roles.find(r=>r.id===dep)?.title||dep);
    const assigned=role.skills.map(skillId=>catalog.skills.find(skill=>skill.id===skillId)).filter(Boolean);
    const profile=role.capability;
    const inputHTML=profile?`<p>${esc(profile.input_context)}</p>${profile.input_paths?.length?pathList(profile.input_paths):'<p class="contract-empty">No upstream output files.</p>'}`:`<p>${esc(deps.length?deps.join(', '):'Your founder brief. Discovery roles can run together.')}</p>`;
    $('role-detail').innerHTML=`<article class="role-card"><header class="role-card-heading"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 8h22M5 16h14M5 24h22m-6-13 6 5-6 5"/></svg><div><h2>${esc(role.title)}</h2><p>${esc(profile?.purpose||role.summary)}</p><div class="role-detail-meta"><span>Stage <strong>${esc(phases[role.phase]||role.phase)}</strong></span><span>Model <strong>Shared configuration</strong></span><span>Executable tools <strong>None</strong></span></div></div></header>${capabilityHTML(profile)}<div class="role-contract"><section><h3>Receives these inputs</h3>${inputHTML}${role.phase==='build'?'<p class="contract-approval">Starts after your exact build-memo approval.</p>':''}</section><section><h3>Owns these output files</h3>${pathList(role.outputs)}</section></div>${acceptanceHTML(profile)}<section class="role-skills"><h3>${assigned.length} assigned ${assigned.length===1?'skill':'skills'}</h3><p>These bundled instructions guide the role in a live request. Open a skill to see its purpose, primary role and complete source. This catalog does not show a completed run.</p>${assigned.map(skill=>sourceHTML(skill)).join('')}</section><div class="role-prompt">${sourceHTML(role,{role:true})}</div></article>`;
    if(updateURL){const url=new URL(location.href);url.searchParams.set('role',id);history.replaceState({},'',url);}
    if(focus)$('role-detail').focus({preventScroll:true});
  }
  function render(){
    $('role-directory').innerHTML=Object.entries(phases).map(([phase,label])=>`<section class="role-phase"><h3>${label}</h3>${catalog.roles.filter(role=>role.phase===phase).map(role=>`<button type="button" class="role-choice" data-role="${esc(role.id)}" aria-pressed="false"><span>${esc(role.title)}</span><span>${role.skills.length} ${role.skills.length===1?'skill':'skills'}</span></button>`).join('')}</section>`).join('');
    $('guide-list').innerHTML=(catalog.operator_guides||[]).map(guide=>sourceHTML(guide)).join('');
    const preferred=new URLSearchParams(location.search).get('role');selectRole(catalog.roles.some(r=>r.id===preferred)?preferred:'frontend',{updateURL:false});
  }
  async function load(){
    const seq=++loadSequence,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
    $('catalog-error').hidden=true;$('catalog-layout').setAttribute('aria-busy','true');
    try{const response=await fetch('/api/catalog',{headers:{'X-PredictKit-Token':token},credentials:'same-origin',cache:'no-store',signal:controller.signal});if(!response.ok)throw new Error('The local catalog could not be loaded ('+response.status+').');const next=await response.json();if(seq!==loadSequence)return;catalog=next;render();}
    catch(error){if(seq!==loadSequence)return;$('catalog-error-message').textContent=(error.name==='AbortError'?'The local server took too long to respond.':error.message)+' Check that PredictKit is running, then try again.';$('catalog-error').hidden=false;if(!catalog){$('role-directory').textContent='Instructions are unavailable.';$('guide-list').textContent='The guides will appear after reconnection.';}}
    finally{clearTimeout(timer);if(seq===loadSequence)$('catalog-layout').setAttribute('aria-busy','false');}
  }
  document.addEventListener('click',async event=>{
    const roleButton=event.target.closest('[data-role]');if(roleButton){selectRole(roleButton.dataset.role);return;}
    const button=event.target.closest('[data-copy]');if(!button||!catalog)return;
    const id=button.dataset.copy,item=id.startsWith('role-')?catalog.roles.find(r=>r.id===id.slice(5)):[...catalog.skills,...(catalog.operator_guides||[])].find(s=>s.id===id);
    if(!item)return;
    try{await navigator.clipboard.writeText(item.role_content||item.content);toast('Instructions copied.');}catch{toast('Clipboard unavailable. Select the instruction text and copy it.');}
  });
  $('catalog-retry').addEventListener('click',load);load();
})();
