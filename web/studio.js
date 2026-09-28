'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const TOKEN = document.querySelector('meta[name="predictkit-token"]').content;
  const CONNECTABLE = /^https?:$/.test(location.protocol) && !TOKEN.startsWith('__');
  const TERMINAL = new Set(['idle','failed','stopped','packaged','needs_fixes','interrupted']);
  const THEME_KEY = 'predictkit-studio-theme';
  const DRAFT_KEY = 'predictkit-studio-brief';
  const THEMES = new Set(['solana-signal','trust-layer','studio-classic']);
  const EXAMPLE = {project_name:'LaunchLens',user:'Small product teams preparing a public launch',problem:'The official launch date hides uncertainty that individual team members can see.',industry:'Software teams and project delivery',alternative:'Status meetings, spreadsheets and informal messages',why_prediction:'Collect explicit forecasts and compare them with later outcomes instead of a vague green status.',why_solana:'Future shared forecast registry for independently verifiable timestamps and outcomes; not implemented in this prototype.',difference:'A resolution-first launch forecast with a visible audit trail, rather than another public betting exchange.',market_question:'Will our team publish the public demo by 18:00 UTC on 8 October 2026?',resolution_rule:'YES only if the named release page shows a usable public demo published on or before the stated deadline. The production version must verify an archived source and its timestamp.',void_policy:'VOID if the release page cannot be verified, the scope changes, or the evidence conflicts. No financial settlement.',template:'forecast-studio'};
  const ROLES = {
    research:{name:'Evidence lead',phase:'discovery',initials:'EV',description:'Separates supplied evidence from assumptions and identifies what still needs research.',paths:['research/market.md']},
    product:{name:'Product lead',phase:'discovery',initials:'PR',description:'Turns the founder brief into one useful user journey and a bounded product specification.',paths:['product/spec.md']},
    architect:{name:'Solana architect',phase:'discovery',initials:'SA',description:'Defines the intended chain responsibility and the current off-chain boundary.',paths:['architecture/plan.md']},
    chief:{name:'Chief of staff',phase:'decision',initials:'CS',description:'Synthesizes discovery into the exact build memo you approve before implementation.',paths:['decisions/build-memo.md']},
    frontend:{name:'App engineer',phase:'build',initials:'FE',description:'Produces the complete browser application from the approved brief.',paths:['app/index.html']},
    domain:{name:'Market designer',phase:'build',initials:'MK',description:'Makes the prediction question, resolution evidence and void policy explicit.',paths:['app/market.json','domain/resolution.md']},
    submission:{name:'Submission lead',phase:'build',initials:'SU',description:'Prepares pitch, demo and application drafts with unverified claims marked.',paths:['submission/pitch.md','submission/demo.md','submission/application.md']},
    reviewer:{name:'Reviewer',phase:'review',initials:'QA',description:'Reviews the supplied artifacts in its own role context. Rehearsal output is scripted; local contract checks run separately.',paths:['qa/review.md']}
  };
  const FIELD_GROUPS = [
    {title:'The opportunity',description:'A specific person, a real problem, a useful difference.',fields:[['project_name','Project name',true],['user','Who is this for?',false],['problem','What problem are you solving?'],['industry','Industry or context',true],['alternative','What do people do today?',false],['why_prediction','Why use forecasting?'],['difference','What makes your approach different?']]},
    {title:'The question contract',description:'A forecast is useful when everyone knows how it resolves.',fields:[['market_question','One exact prediction question',false,'Include a clear event and deadline.'],['resolution_rule','Resolution source, deadline and rule',false,'Name the source, who resolves, and what qualifies as YES.'],['void_policy','When should the question be voided?',false,'Explain missing evidence, conflicting sources and scope changes.']]},
    {title:'The implementation',description:'Keep the first version small and the chain role meaningful.',fields:[['why_solana','What should Solana eventually do?',false,'Current starters are off-chain simulations. This field defines the intended integration.']]}
  ];
  const TITLES = {
    brief:['Your idea.\nA working first version.','Start with one clear question. Rehearse the build, approve its direction, and inspect every output.'],
    team:['One brief.\nA team that builds.','Follow the actual scheduler, make the next decision, and inspect each role’s work.'],
    workbench:['Open the work.\nSee what it does.','Inspect your files and try the generated app in an isolated browser preview.'],
    submission:['A clear story.\nWith evidence attached.','Export a draft pack that separates working local behavior from the proof still needed.'],
    log:['Every step.\nA visible record.','Starts, completions, decisions and failures, recorded by the local runtime.']
  };
  let state = {status:'idle',jobs:{},events:[],artifacts:[],usage:{requests:0},provider:'rehearsal'};
  let serverConfig = {};
  let connected = false, initialized = false, currentTab = 'brief', mutationBusy = false, revision = 0, pollTimer, toastTimer;
  let draft = {...EXAMPLE}, hasSavedDraft = false, returnFocus = null, lastStatus = '', lastSync = '';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const human = value => String(value || '').replaceAll('_',' ').replaceAll('.',' / ');
  const size = bytes => Number.isFinite(bytes) ? (bytes < 1024 ? bytes+' B' : (bytes/1024).toFixed(1)+' KB') : '';
  const isActive = () => !TERMINAL.has(state.status);
  const isLive = () => ['openai-responses','openai-agents'].includes(state.server_provider || state.provider);
  const fileExists = path => (state.artifacts || []).some(a => a.path === path);
  function setHTML(id, html) { if ($(id).innerHTML !== html) $(id).innerHTML = html; }
  function toast(message) { clearTimeout(toastTimer); $('toast').textContent=message; $('toast').hidden=false; toastTimer=setTimeout(()=>$('toast').hidden=true,5000); }
  function storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
  function storageSet(key,value) { try { localStorage.setItem(key,value); return true; } catch { return false; } }
  const initialTheme = storageGet(THEME_KEY);
  if (THEMES.has(initialTheme)) document.documentElement.dataset.theme = initialTheme;
  $('theme').value = document.documentElement.dataset.theme;
  $('theme').addEventListener('change', () => { const theme=$('theme').value; if(THEMES.has(theme)){ document.documentElement.dataset.theme=theme; storageSet(THEME_KEY,theme); toast('Appearance changed. Run status and permissions are unchanged.'); } });
  try { const saved=JSON.parse(storageGet(DRAFT_KEY)); if(saved && Object.keys(EXAMPLE).every(key=>typeof saved[key]==='string')) {draft=saved;hasSavedDraft=true;} } catch { /* An invalid draft never blocks opening the studio. */ }
  function setupForm() {
    $('fields').innerHTML = FIELD_GROUPS.map(group=>`<div class="field-group-label"><h3>${group.title}</h3><p>${group.description}</p></div>${group.fields.map(([key,label,short,help])=>`<div class="field ${short?'':'full'}"><label for="field-${key}">${label}</label>${short?`<input id="field-${key}" name="${key}" required minlength="3" maxlength="2500" autocomplete="off">`:`<textarea id="field-${key}" name="${key}" required minlength="3" maxlength="2500"${help?` aria-describedby="help-${key}"`:''}></textarea>`}${help?`<small id="help-${key}">${help}</small>`:''}</div>`).join('')}`).join('') + '<div class="field full"><label for="template">Starter template</label><select id="template" name="template"><option value="forecast-studio">Forecast Studio · forecast, resolve, calibrate</option><option value="market-explorer">Market Explorer · local forecast history</option><option value="resolution-desk">Resolution Desk · human-attested outcome</option></select><small>All three use the same off-chain reference flow with different entry views.</small></div>';
    for(const key of Object.keys(EXAMPLE)) { const input=$(key==='template'?'template':'field-'+key); if(input) input.value=draft[key]; }
    updateQuestion();
    requestAnimationFrame(sizeBriefFields);
    $('draft-status').textContent=hasSavedDraft?'Saved on this browser':'Editable example';
  }
  function readBrief() { const next={}; for(const key of Object.keys(EXAMPLE)) next[key]=$(key==='template'?'template':'field-'+key).value.trim(); return next; }
  function updateBriefContext() { $('brief-context').innerHTML=isActive()?'<strong>Your current run is frozen.</strong> Changes here are saved as a draft for your next run. The approval memo still refers to the brief that started this run.':draft.project_name===EXAMPLE.project_name?'<strong>Meet LaunchLens.</strong> An editable launch forecast for a product team. Make it yours, or run the example to explore.':'<strong>Your founder brief.</strong> Define one useful question. The rehearsal will use these exact fields to personalize the app and its supporting files.'; }
  function updateQuestion() { $('question-preview').textContent=$('field-market_question').value.trim() || 'Your first prediction question will appear here.'; }
  function saveDraft() { draft=readBrief(); hasSavedDraft=storageSet(DRAFT_KEY,JSON.stringify(draft)); $('draft-status').textContent=hasSavedDraft?'Draft saved locally':'Draft kept in this tab'; updateQuestion(); updateBriefContext(); }
  function sizeBriefFields() {
    if($('section-brief').hidden)return;
    $('brief-form').querySelectorAll('textarea').forEach(field=>{field.style.height='auto';field.style.height=(field.scrollHeight+2)+'px';});
  }
  $('brief-form').addEventListener('input',()=>{saveDraft();sizeBriefFields();});
  $('brief-form').addEventListener('change', saveDraft);
  window.addEventListener('resize',sizeBriefFields);
  document.fonts.ready.then(sizeBriefFields);
  function setTab(tab,focus=false) {
    if(!TITLES[tab])return;
    currentTab=tab;
    document.querySelectorAll('.section').forEach(el=>{ const active=el.id==='section-'+tab; el.hidden=!active; el.classList.toggle('active',active); });
    document.querySelectorAll('.navbutton').forEach(el=>{ const active=el.dataset.tab===tab; el.classList.toggle('active',active); if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current'); });
    const title=TITLES[tab][0].split('\n'); $('page-title').replaceChildren(document.createTextNode(title[0]),document.createElement('br')); const accent=document.createElement('span'); accent.className='accent-text';accent.textContent=title[1];$('page-title').append(accent);
    $('page-sub').textContent=TITLES[tab][1];$('hero-actions').hidden=tab==='brief';$('edit-brief').hidden=tab==='brief';$('stats').hidden=tab==='brief' && !state.id;
    if(tab==='brief')requestAnimationFrame(sizeBriefFields);
    if(focus){$('main').focus({preventScroll:true});$('main').scrollIntoView({block:'start'});}
  }
  async function request(path,data,{blob=false}={}) {
    if(!CONNECTABLE)throw new Error('Open the Studio through the local Python server to use the runtime.');
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),12000);
    try {
      const response=await fetch(path,{method:data===undefined?'GET':'POST',headers:{'X-PredictKit-Token':TOKEN,...(data===undefined?{}:{'Content-Type':'application/json'})},body:data===undefined?undefined:JSON.stringify(data),cache:'no-store',credentials:'same-origin',signal:controller.signal});
      if(!response.ok){let message='Request failed ('+response.status+').';try{const detail=await response.json();message=detail.error||message;}catch{}throw new Error(message);}
      return blob ? await response.blob() : await response.json();
    } catch(error) { if(error.name==='AbortError')throw new Error('The local runtime did not respond in time. Reconnect to check its state before retrying.');throw error; }
    finally {clearTimeout(timeout);}
  }
  function acceptState(next) { for(const key of ['server_provider','spend_policy','version'])if(Object.hasOwn(next,key))serverConfig[key]=next[key];state={...next,...serverConfig}; connected=true; lastSync=new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});render(); }
  async function mutate(path,data={}) { mutationBusy=true;revision++;render();try{const next=await request(path,data);acceptState(next);return next;}finally{mutationBusy=false;render();} }
  function empty(title,detail,action) {return `<div class="empty-state"><span class="empty-symbol" aria-hidden="true">◇</span><h3>${esc(title)}</h3><p>${esc(detail)}</p>${action?'<button class="button quiet" data-tab="brief">Open project brief <span aria-hidden="true">↗</span></button>':''}</div>`;}
  function eventMarkup(ev) {
    const names={'job.started':'Role started','job.output_checked':'Output checked','job.completed':'Output accepted','job.failed':'Role failed','job.cancelled':'Role cancelled','provider.usage_recorded':'Usage recorded','founder.approval_required':'Founder approval requested','founder.approved':'Exact memo approved','sprint.started':'Rehearsal started','sprint.finished':'Run finished','sprint.paused':'New work paused','sprint.resumed':'Scheduling resumed','sprint.stopped':'Run stopped'};
    const title=names[ev.kind]||human(ev.kind), role=ROLES[ev.role]?.name||ev.role;
    let detail=ev.message|| (ev.kind==='job.output_checked'?(ev.passed?'Static output checks passed. Inspect the role for recorded results.':'Static output checks failed. The role’s files were not accepted.'):ev.files?.length ? ev.files.length+' file'+(ev.files.length===1?'':'s')+' written to the local run.' : role ? 'Recorded by the local scheduler.' : '');
    return `<div class="event"><time datetime="${esc(ev.at)}">${esc((ev.at||'').slice(11,19)||'—')} UTC</time><div><strong>${esc(title)}${role?' · '+esc(role):''}</strong>${detail?`<p>${esc(detail)}</p>`:''}</div></div>`;
  }
  function checkMarkup(name,passed,detail,status) {return `<div class="check ${passed?'pass':status==='STATIC CHECK FAILED'?'fail':''}"><span class="check-symbol" aria-hidden="true">${passed?'✓':'–'}</span><div><h3>${esc(name)}</h3>${detail?'<p>'+esc(detail)+'</p>':''}<span class="check-status">${esc(status||(passed?'OBSERVED LOCALLY':'NOT YET PROVEN'))}</span></div></div>`;}
  function fileMarkup(file) {const ext=file.path.split('.').at(-1).toUpperCase();return `<button class="file" data-file="${esc(file.path)}"><span class="file-icon" aria-hidden="true">${esc(ext)}</span><span class="file-meta"><code>${esc(file.path)}</code><small>${esc(ROLES[file.owner]?.name||file.owner||'Run artifact')}${file.bytes?' · '+size(file.bytes):''}</small></span><span class="arrow" aria-hidden="true">↗</span></button>`;}
  function render() {
    const focused=document.activeElement?.dataset?.role;
    for(const phase of ['discovery','decision','build','review']) {
      setHTML(phase+'-agents',Object.entries(ROLES).filter(([,role])=>role.phase===phase).map(([id,role])=>{const job=state.jobs?.[id]||{status:'queued'},status=job.status==='queued'?'Waiting':human(job.status);return `<button class="agent ${esc(job.status)}" data-role="${id}" aria-label="${esc(role.name+': '+status+'. Inspect role')}"><span class="agent-top"><span class="role-icon">${role.initials}</span><span class="agent-name">${role.name}</span><span class="agent-arrow" aria-hidden="true">↗</span></span><span class="agent-status"><span class="dot" aria-hidden="true"></span>${esc(status)}${Number.isFinite(job.duration_seconds)?' · '+job.duration_seconds.toFixed(1)+'s':''}</span></button>`;}).join(''));
    }
    if(focused && document.activeElement===document.body)document.querySelector(`[data-role="${focused}"]`)?.focus({preventScroll:true});
    updateBriefContext();
    const jobs=Object.values(state.jobs||{}),completed=jobs.filter(job=>job.status==='done').length,active=jobs.filter(job=>job.status==='running').length;
    setHTML('completed',completed+' <small>/ 8</small>');setHTML('active',active+' <small>/ 3</small>');
    $('usage').textContent=state.usage?.requests||0;$('usage-caption').textContent=isLive()?((state.usage?.input_tokens||0)+(state.usage?.output_tokens||0)).toLocaleString()+' reported tokens':'Scripted rehearsal outputs';
    $('crumb').textContent=state.brief?.project_name||'Your first build';
    $('phase').textContent=state.paused?'Paused':human(state.status==='idle'?'ready':state.status);
    $('phase').setAttribute('aria-live','polite');
    const activeRun=isActive(),busy=mutationBusy||!connected;
    $('launch').disabled=busy||activeRun;$('brief-launch').disabled=busy||activeRun;
    const label=isLive()?'Review live run':'Run rehearsal';$('launch').innerHTML=label+' <span aria-hidden="true">↗</span>';$('brief-launch').innerHTML=(isLive()?'Save & review live run':'Save & run rehearsal')+' <span aria-hidden="true">↗</span>';
    $('pause').disabled=busy||!activeRun;$('stop').disabled=busy||!activeRun;$('pause').textContent=state.paused?'Resume new work':'Pause new work';
    $('run-control-note').textContent=state.paused?'Paused. Work already in flight may finish.':activeRun?'You can pause scheduling or stop this run.':state.status==='interrupted'?'Interrupted by a server restart. Start a new rehearsal to continue.':state.status==='failed'?'The run failed. Inspect role details and the log before starting again.':state.status==='stopped'?'Run stopped. Completed artifacts remain available.':state.status==='idle'?'Ready when you are.':'This run has finished.';
    $('approval').hidden=state.status!=='awaiting_approval';$('approve').disabled=busy;$('review-memo').disabled=busy;
    $('run-alert').hidden=!['failed','stopped','interrupted','needs_fixes'].includes(state.status);
    $('run-alert-text').textContent=state.status==='failed'?'This run failed. Inspect the log and role errors before starting again. Completed artifacts remain available.':state.status==='interrupted'?'This run was interrupted when the server restarted. No paid work was automatically resumed. Inspect its files or start a new run.':state.status==='needs_fixes'?'The run produced a pack with unresolved checks. Inspect the workbench before sharing the draft.':'This run was stopped. Completed artifacts remain available; start a new rehearsal when ready.';
    $('completion').querySelector('.micro').textContent=state.provider==='rehearsal'?'LOCAL REHEARSAL COMPLETE':'RUN PACKAGED / REVIEW REQUIRED';
    $('completion').hidden=state.status!=='packaged'||currentTab==='brief'||currentTab==='workbench'||currentTab==='submission';
    $('team-dot').hidden=state.status!=='awaiting_approval';$('stats').hidden=currentTab==='brief'&&!state.id;
    const events=[...(state.events||[])].reverse();$('events-count').textContent=events.length+' events';
    setHTML('activity',events.length?events.slice(0,8).map(eventMarkup).join(''):empty('No run yet','Start with the sample brief. The scheduler’s first event will appear here.',true));
    setHTML('full-log',events.length?events.map(eventMarkup).join(''):empty('A clean slate','Your run events will appear here after you start a rehearsal.',true));
    const artifacts=state.artifacts||[];$('file-count').textContent=artifacts.length;$('artifact-summary').textContent=artifacts.length?artifacts.length+' role-owned files · '+(state.provider||'unknown provider'):'Files from your current rehearsal';
    setHTML('artifacts-list',artifacts.length?artifacts.map(fileMarkup).join(''):empty('The work will land here','Run your brief, approve the build memo, then open the app and its supporting files.',true));
    $('preview-app').disabled=busy||!fileExists('app/index.html');$('export').disabled=busy||!['packaged','needs_fixes'].includes(state.status);
    const checks=state.verification?.checks||[];
    setHTML('checks',checks.length?checks.map(c=>checkMarkup(c.name||c.label,c.passed,c.detail||c.message||'')).join(''):empty('Checks pending','The coordinator runs file checks after the build.'));
    const readiness=[['Founder brief',!!state.brief,'Your saved product hypothesis.'],['Exact build approval',!!state.memo_hash && state.approved_brief_hash===state.brief_hash && state.approved_memo_hash===state.memo_hash,'Approval is bound to the brief and memo hashes.'],['Pitch and demo drafts',fileExists('submission/pitch.md')&&fileExists('submission/demo.md'),'Written drafts; no presentation or video has been recorded.'],['Exportable file bundle',['packaged','needs_fixes'].includes(state.status),'Local file evidence and run metadata.'],['Live agent execution',false,'Requires review of an authorized provider run and its actual outputs.'],['Meaningful Solana integration',false,'Source and fixtures do not prove a connected on-chain application.'],['Independent builder validation',false,'Not measured. No participant, revenue or usage claims.'],['Current submission requirements',false,'Verify eligibility and the official portal before applying.']];
    setHTML('submission-checks',readiness.map(([name,passed,detail])=>checkMarkup(name,passed,detail)).join(''));
    if(connected) {
      $('mode').className='status-chip connected';$('mode').innerHTML='<span class="status-dot"></span>'+(isLive()?'Live provider configured':'Local rehearsal');
      $('mode-notice').classList.remove('offline');$('mode-notice').querySelector('p').innerHTML=isLive()?'<strong>Live provider configured.</strong> Starting a run requires explicit model-spend approval. Generated code stays local; no blockchain transactions.':'<strong>Local rehearsal.</strong> Real scheduling, approvals and local files. Scripted role outputs; no paid model calls or blockchain transactions.';
      $('retry-connection').hidden=true;$('runtime-footer').textContent='Synced '+lastSync+(state.id?' · '+state.id:' · ready');
    }
    if(initialized && state.status!==lastStatus && state.status==='awaiting_approval')toast('Your build memo is ready. Review it to continue.');
    lastStatus=state.status;
  }
  function disconnected(error) {
    connected=false;render();$('mode').className='status-chip offline';$('mode').innerHTML='<span class="status-dot"></span>Disconnected';$('mode-notice').classList.add('offline');
    $('mode-notice').querySelector('p').textContent=state.id?'Connection lost. Showing the last observed run; its current status is unverified. '+error.message:'The local runtime is unavailable. '+error.message;
    $('retry-connection').hidden=!CONNECTABLE;$('runtime-footer').textContent=lastSync?'Last observed '+lastSync+' · reconnect to verify':'Open via python3 predictkit.py serve';
  }
  async function poll() {
    clearTimeout(pollTimer);
    if(!CONNECTABLE){disconnected(new Error('Open this page through the local Python server.'));return;}
    if(mutationBusy){pollTimer=setTimeout(poll,750);return;}
    const startedRevision=revision;
    try {const next=await request('/api/state');if(startedRevision!==revision)return;
      if(!initialized){if(next.brief&&!hasSavedDraft){draft={...EXAMPLE,...next.brief};setupForm();}if(next.id)setTab(next.status==='packaged'?'workbench':'team');}
      acceptState(next);initialized=true;
    } catch(error) {if(startedRevision===revision)disconnected(error);}
    finally {pollTimer=setTimeout(poll,isActive()?900:2500);}
  }
  $('retry-connection').addEventListener('click',poll);
  function openDialog(title,{kicker='INSPECT THE WORK',body,footer}={}) {
    if(!$('modal').open)returnFocus=document.activeElement;
    $('modal-title').textContent=title;$('modal-kicker').textContent=kicker;$('modalbody').replaceChildren();$('modal-footer').replaceChildren();$('modal-footer').hidden=!footer;
    if(typeof body==='string'){const pre=document.createElement('pre');pre.textContent=body;$('modalbody').append(pre);}else if(body)$('modalbody').append(body);
    if(footer)$('modal-footer').append(footer);
    if(!$('modal').open)$('modal').showModal();$('modal-close').focus({preventScroll:true});$('modalbody').scrollTop=0;
  }
  function closeDialog(){if($('modal').open)$('modal').close();}
  $('modal-close').addEventListener('click',closeDialog);
  $('modal').addEventListener('close',()=>{const target=returnFocus;returnFocus=null;if(target?.isConnected&&!target.disabled&&target.getClientRects().length)target.focus({preventScroll:true});else document.querySelector('.navbutton.active')?.focus({preventScroll:true});});
  $('modal').addEventListener('click',event=>{if(event.target===$('modal')){const rect=$('modal').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeDialog();}});
  function errorDialog(title,error){openDialog(title,{kicker:'ACTION NEEDS ATTENTION',body:error.message||String(error)});}
  async function showFile(path){try{const file=await request('/api/artifact?path='+encodeURIComponent(path));openDialog(path,{body:file.content});}catch(error){errorDialog('Artifact unavailable',error);}}
  function roleEvidenceHTML(job) {
    const receipt=job.capability_receipt,quality=job.quality_report,instructions=job.usage?.instruction_receipt;
    if(!receipt)return `<div class="divider"></div><h3>Run evidence</h3><p>${job.status==='queued'?'This role has not started. Its exact inputs and output checks will appear here after the coordinator records them.':'No capability receipt was recorded for this job. Older runs remain readable, but cannot show the new input and check evidence.'}</p>`;
    const mode={'scripted-rehearsal':'Scripted rehearsal','contract-test':'Local contract test','live-provider':'Live provider'}[receipt.mode]||human(receipt.mode);
    const checks=quality?.checks||[];
    const checksHTML=checks.length?checks.map(check=>checkMarkup(check.label,check.passed,check.detail,check.passed?'STATIC CHECK PASSED':'STATIC CHECK FAILED')).join(''):`<p>${job.status==='failed'?'No completed output checks were recorded. Inspect the recorded error above.':'No output checks have been recorded yet.'}</p>`;
    const inputs=receipt.input_artifacts||[];
    const profile=receipt.profile||{};
    return `<div class="divider"></div><section aria-label="Recorded capability evidence"><h3>What this run received</h3><p>${esc(mode)} · ${esc(receipt.model||'No model')}. The coordinator recorded these prepared inputs; this receipt does not prove that a model followed the instructions.</p><p>${esc(profile.input_context||'The frozen founder brief is included in the prepared context.')}</p>${inputs.length?`<ul>${inputs.map(input=>`<li><code>${esc(input.path)}</code> · ${esc(ROLES[input.owner]?.name||input.owner||'Upstream output')}</li>`).join('')}</ul>`:'<p>No upstream output files were supplied.</p>'}${profile.purpose?`<h3>Assigned outcome</h3><p>${esc(profile.purpose)}</p>`:''}<h3>Recorded output checks</h3>${checksHTML}<p>Static checks verify the output contract. Use the review questions to assess usefulness, correctness and evidence.</p>${profile.review_questions?.length?`<details><summary>Questions that still need judgment</summary><ul>${profile.review_questions.map(question=>`<li>${esc(question)}</li>`).join('')}</ul></details>`:''}${quality?.not_tested?.length?`<details><summary>What these checks did not test</summary><ul>${quality.not_tested.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details>`:''}<details><summary>Read the exact input receipt and hashes</summary><pre>${esc(JSON.stringify(receipt,null,2))}</pre></details>${instructions?`<details><summary>Read the assembled instruction hashes</summary><p>These hashes identify the instruction text assembled for this request. They do not prove compliance.</p><pre>${esc(JSON.stringify(instructions,null,2))}</pre></details>`:`<p>${receipt.mode==='scripted-rehearsal'?'Rehearsal writes scripted outputs. It does not execute the role or skill instruction files.':'No assembled instruction hashes were recorded for this job.'}</p>`}</section>`;
  }
  function showRole(id) {
    const role=ROLES[id];if(!role)return;const job=state.jobs?.[id]||{status:'queued'},body=document.createElement('div');
    const rejected=job.quality_report?.passed===false;
    const missingLabel=rejected?'Rejected · not added to this run':({failed:'Not produced · role failed',cancelled:'Not produced · role cancelled',interrupted:'Not produced · role interrupted',running:'In progress · not accepted yet',done:'Unavailable · file not in this run'}[job.status]||'Pending · role has not started');
    const failedChecks=(job.quality_report?.checks||[]).filter(check=>!check.passed);
    const failureHTML=job.status==='failed'?`<section class="role-failure" aria-label="Role failure"><h3>${rejected?'Output rejected':'This role could not finish'}</h3><p>${rejected?'The coordinator did not accept this role’s files. Review the failed checks before starting another run.':'The run stopped for this role. Inspect the recorded error before starting another run.'}</p>${failedChecks.length?`<ul>${failedChecks.map(check=>`<li>${esc(check.detail||check.label)}</li>`).join('')}</ul>`:''}${job.error?`<details${rejected?'':' open'}><summary>Recorded error</summary><p>${esc(job.error)}</p></details>`:''}</section>`:'';
    const summary=job.summary||(rejected?'Output checks did not pass.':job.status==='failed'?'No output was accepted from this role.':'This role has not produced an output yet.');
    body.innerHTML=`<div class="role-description"><span class="tag">${esc(human(job.status))} · ${esc(state.provider||'rehearsal')}</span><h3>${esc(role.description)}</h3><p>${esc(summary)}</p></div>${failureHTML}<h3>Output contract</h3>${role.paths.map(path=>fileExists(path)?fileMarkup({path,owner:id}):`<div class="file"><span class="file-icon" aria-hidden="true">FILE</span><span class="file-meta"><code>${esc(path)}</code><small>${esc(missingLabel)}</small></span></div>`).join('')}${roleEvidenceHTML(job)}${job.limitations?.length?'<div class="divider"></div><h3>Recorded limitations</h3><ul>'+job.limitations.map(text=>'<li>'+esc(text)+'</li>').join('')+'</ul>':''}${job.usage?'<div class="binding-info">Provider: '+esc(job.usage.provider||state.provider)+'<br>Reported requests: '+esc(job.usage.requests||0)+'<br>Input tokens: '+esc(job.usage.input_tokens||0)+' · Output tokens: '+esc(job.usage.output_tokens||0)+'</div>':''}`;
    const skillLink=document.createElement('a');skillLink.className='button quiet';skillLink.href='/skills?role='+encodeURIComponent(id);skillLink.textContent='Inspect assigned skills & instructions';body.append(skillLink);
    openDialog(role.name,{kicker:'ROLE / '+role.phase.toUpperCase(),body});
  }
  async function reviewMemo() {
    try {
      const snapshot=await request('/api/state');acceptState(snapshot);
      if(snapshot.status!=='awaiting_approval')return showFile('decisions/build-memo.md');
      const file=await request('/api/artifact?path=decisions%2Fbuild-memo.md');
      if(!crypto.subtle)throw new Error('This browser cannot verify the displayed memo hash. Use the localhost Studio in a current browser.');
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(file.content)))).map(byte=>byte.toString(16).padStart(2,'0')).join('');
      if(digest!==snapshot.memo_hash)throw new Error('The memo changed while loading. Close this dialog and review the latest memo.');
      const captured={brief_hash:snapshot.brief_hash,memo_hash:snapshot.memo_hash,id:snapshot.id};
      const body=document.createElement('div'),pre=document.createElement('pre'),binding=document.createElement('div');pre.textContent=file.content;binding.className='binding-info';binding.textContent='BRIEF SHA-256  '+captured.brief_hash+'\nMEMO SHA-256  '+captured.memo_hash;body.append(pre,binding);
      const footer=document.createElement('div');footer.innerHTML='<label class="approval-confirm"><input type="checkbox" id="memo-confirm"><span>I reviewed this build memo and approve this exact brief and scope. This does not authorize publication or blockchain actions.</span></label><div class="buttons"><button class="button quiet" id="memo-cancel">Keep reviewing</button><button class="button primary" id="memo-submit" disabled>Approve this exact memo <span aria-hidden="true">→</span></button></div>';
      openDialog('Review the build direction',{kicker:'FOUNDER APPROVAL / '+(snapshot.brief?.project_name||''),body,footer});
      $('memo-confirm').addEventListener('change',()=>$('memo-submit').disabled=!$('memo-confirm').checked);
      $('memo-cancel').addEventListener('click',closeDialog);
      $('memo-submit').addEventListener('click',async()=>{const button=$('memo-submit');button.disabled=true;button.textContent='Confirming exact approval…';try{
        const current=await request('/api/state');if(current.id!==captured.id||current.brief_hash!==captured.brief_hash||current.memo_hash!==captured.memo_hash||current.status!=='awaiting_approval')throw new Error('This approval is stale. Review the current run and its latest memo before approving.');
        await mutate('/api/approve',{brief_hash:captured.brief_hash,memo_hash:captured.memo_hash});closeDialog();setTab('team');toast('Exact brief and memo approved. The build can continue.');
      }catch(error){errorDialog('Approval blocked',error);}});
    }catch(error){errorDialog('Memo review unavailable',error);}
  }
  $('review-memo').addEventListener('click',reviewMemo);$('approve').addEventListener('click',reviewMemo);
  $('edit-brief').addEventListener('click',()=>setTab('brief',true));
  $('reset-brief').addEventListener('click',()=>{draft={...EXAMPLE};hasSavedDraft=false;setupForm();saveDraft();$('draft-status').textContent='Example loaded';toast('LaunchLens example loaded into your local draft.');});
  async function startRun(approveSpend=false) {
    try{await mutate('/api/start',{brief:readBrief(),approve_model_spend:approveSpend});closeDialog();setTab('team',true);toast(approveSpend?'Authorized live run started.':'Local rehearsal started. Discovery is underway.');}
    catch(error){errorDialog('Run could not start',error);}
  }
  function launch() {
    if(!$('brief-form').checkValidity()){setTab('brief',true);$('brief-form').reportValidity();return;}
    saveDraft();
    if(isLive()) {
      const policy=state.spend_policy,body=document.createElement('div');
      body.innerHTML='<h3>Live model execution uses your configured API account.</h3><p>Your brief and accepted artifacts will be sent to the provider. This is a single bounded run; it is not a rehearsal.</p>'+(policy?'<div class="binding-info">Configured run policy\n'+esc(JSON.stringify(policy,null,2))+'</div>':'<p class="connection-error">No spend policy was returned by this server. Configure the model and budget locally before starting.</p>')+'<p>Configured token prices are estimates, not a provider billing hard cap. No automatic paid retry, wallet transaction or publication is authorized here.</p>';
      const footer=document.createElement('div');footer.innerHTML='<label class="approval-confirm"><input id="spend-check" type="checkbox"><span>I approve this one run with the configured model and budget shown above.</span></label><div class="buttons"><button class="button quiet" id="spend-cancel">Cancel</button><button class="button primary" id="spend-start" disabled>Start authorized live run</button></div>';
      openDialog('Approve model spend',{kicker:'PAID PROVIDER / EXPLICIT APPROVAL',body,footer});$('spend-cancel').onclick=closeDialog;$('spend-check').onchange=()=>$('spend-start').disabled=!$('spend-check').checked||!policy;$('spend-start').onclick=()=>startRun(true);
    } else startRun(false);
  }
  $('launch').addEventListener('click',launch);$('brief-form').addEventListener('submit',event=>{event.preventDefault();launch();});
  $('pause').addEventListener('click',async()=>{try{const pausing=!state.paused;await mutate(pausing?'/api/pause':'/api/resume');toast(pausing?'New work paused. In-flight work may finish.':'Scheduling resumed.');}catch(error){errorDialog('Run control unavailable',error);}});
  $('stop').addEventListener('click',async()=>{try{await mutate('/api/stop');toast('Stop requested. Completed files remain in the run.');}catch(error){errorDialog('Stop unavailable',error);}});
  $('founder-help').addEventListener('click',()=>openDialog('You remain in control',{kicker:'FOUNDER / DECISION OWNER',body:'You choose the brief and approve its exact build memo.\n\nThe coordinator schedules role work and saves accepted files. Pause prevents new work from starting; work already in flight may finish. Stop requests cancellation without deleting existing outputs.\n\nPublication, model spend and wallet transactions require their own explicit approval. This Studio never automatically submits or publishes your work.'}));
  $('preview-app').addEventListener('click',async()=>{try{
    const file=await request('/api/artifact?path=app%2Findex.html');
    const policy="<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; font-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'\">";
    const body=document.createElement('div'),notice=document.createElement('p'),frame=document.createElement('iframe');notice.className='preview-label';notice.textContent='Isolated app preview · off-chain simulation · external network access blocked · browser-session data resets when closed.';
    frame.title='Generated application — isolated off-chain simulation';frame.setAttribute('sandbox','allow-scripts');frame.referrerPolicy='no-referrer';frame.srcdoc=policy+file.content;body.append(notice,frame);openDialog(state.brief?.project_name||'Generated application',{kicker:'APP PREVIEW / ISOLATED',body});
  }catch(error){errorDialog('App preview unavailable',error);}});
  $('export').addEventListener('click',async()=>{const button=$('export');button.disabled=true;button.textContent='Preparing ZIP…';try{const blob=await request('/api/export',undefined,{blob:true}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='predictkit-'+(state.id||'run')+'.zip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);toast('Draft ZIP downloaded. Nothing was published.');}catch(error){errorDialog('Export unavailable',error);}finally{button.innerHTML='Export ZIP <span aria-hidden="true">↓</span>';render();}});
  async function showHistory() {
    try {const data=await request('/api/history'),body=document.createElement('div');const runs=Array.isArray(data)?data:(data.runs||[]);
      body.innerHTML='<p>Saved on this computer. Opening a run changes the inspected record; it does not restart work.</p>'+(runs.length?runs.map(run=>`<button class="history-row" data-run="${esc(run.id)}"${isActive()?' disabled':''}><span><strong>${esc(run.project_name||run.brief?.project_name||'Untitled run')}${run.id===(data.selected_id||state.id)?' · current':''}</strong><small>${esc(run.created_at||run.id)}<br>${esc(run.provider||'Saved local run')}</small></span><span class="tag">${esc(human(run.status))}</span></button>`).join(''):empty('No saved runs yet','Complete your first rehearsal to start a local history.'))+(isActive()?'<p class="boundary">Pause or stop does not discard the current run. Finish or stop it before switching records.</p>':'');
      openDialog('Saved runs',{kicker:'LOCAL HISTORY',body});
    }catch(error){errorDialog('History unavailable',error);}
  }
  $('history').addEventListener('click',showHistory);$('log-history').addEventListener('click',showHistory);
  document.addEventListener('click',async event=>{const tab=event.target.closest('[data-tab]');if(tab){setTab(tab.dataset.tab,true);render();}const role=event.target.closest('[data-role]');if(role)showRole(role.dataset.role);const file=event.target.closest('[data-file]');if(file)showFile(file.dataset.file);const run=event.target.closest('[data-run]');if(run&&!run.disabled){try{await mutate('/api/select',{id:run.dataset.run});closeDialog();setTab('workbench',true);toast('Saved run opened. Your editable brief draft is preserved.');}catch(error){errorDialog('Cannot open this run',error);}}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
  setupForm();setTab('brief');render();poll();
})();
