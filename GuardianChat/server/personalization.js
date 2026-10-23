/* Account colours affect bubbles and the two brand headings; other chrome stays fixed. */
(()=>{
 let owner='',session='',choices=[],generation=0,lastFetch=0,busy=false,draft=null;
 const fallback={id:'orbit-cyan-navy',roles:2,accent:'#7C3AED',bubble:'#7C3AED',ink:'#FFFFFF',received:'#202546',receivedInk:'#F1F5F9',headingDark:'#22D3EE',headingLight:'#0E7490'};
 const variables={bubble:'bubble',ink:'ink',received:'received','received-ink':'receivedInk','heading-dark':'headingDark','heading-light':'headingLight'};
 function account(){try{return typeof GuardianGaming!=='undefined'?JSON.parse(GuardianGaming.session()):JSON.parse(localStorage.getItem('guardianchat-account')||'null')}catch(_){return null}}
 function apply(p){p=p?.roles===2?p:fallback;for(const [css,key] of Object.entries(variables))document.documentElement.style.setProperty('--personal-'+css,p[key]||fallback[key]);document.documentElement.dataset.palette=p.id}
 function cached(id){try{return JSON.parse(localStorage.getItem('xorbit-palette-'+id))}catch(_){return null}}
 function preview(p){const dialog=document.getElementById('personalizationDialog');if(!dialog||!p)return;for(const el of dialog.querySelectorAll('[data-pair-role]')){const first=el.dataset.pairRole==='first';el.style.backgroundColor=first?p.bubble:p.received;el.style.color=first?p.ink:p.receivedInk}}
 function render(){const select=document.getElementById('paletteChoice');if(!select)return;const current=draft||document.documentElement.dataset.palette;select.replaceChildren();for(const p of choices){const o=document.createElement('option');o.value=p.id;o.textContent=p.name;select.append(o)}select.value=current;select.disabled=!owner||busy;document.getElementById('savePalette').disabled=!owner||busy;preview(choices.find(p=>p.id===current))}
 async function refresh(force=false){
  const a=account(),next=a?.id||'';
  if(next!==owner||a?.token!==session){owner=next;session=a?.token||'';generation++;busy=false;draft=null;apply(owner?cached(owner):null);render();lastFetch=0}
  if(!owner||busy||(!force&&Date.now()-lastFetch<30000))return;
  lastFetch=Date.now();const g=generation,uid=owner,token=session;
  try{const r=await fetch('/preferences',{headers:{Authorization:'Bearer '+token}});if(!r.ok)throw Error();const data=await r.json();if(g!==generation||account()?.id!==uid||account()?.token!==token)return;choices=data.choices;const p=choices.find(p=>p.id===data.palette);if(!p)return;localStorage.setItem('xorbit-palette-'+uid,JSON.stringify(p));apply(p);render()}catch(_){/* Offline: retain only this account's saved pair. */}
 }
 async function save(){
  const a=account(),status=document.getElementById('paletteStatus');if(!a||a.id!==owner||busy)return;
  const palette=document.getElementById('paletteChoice').value,uid=owner,token=session,g=++generation;
  busy=true;draft=palette;render();status.textContent='Saving…';
  try{const r=await fetch('/preferences',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({palette})});if(!r.ok)throw Error('Could not save. Try again.');const data=await r.json();if(g!==generation||account()?.id!==uid||account()?.token!==token)return;choices=data.choices;const p=choices.find(p=>p.id===data.palette);localStorage.setItem('xorbit-palette-'+uid,JSON.stringify(p));draft=null;apply(p);status.textContent='Bubble and brand-heading colours saved for your account.'}catch(e){if(g===generation)status.textContent=e.message}finally{if(g===generation){busy=false;render()}}
 }
 function mount(){
  const settings=document.getElementById('settingsPanel');if(!settings)return;
  const button=document.createElement('button');button.id='openPersonalization';button.type='button';button.textContent='Personalization';button.title='Choose message bubble and brand-heading colours';settings.insertBefore(button,settings.querySelector('label[for=appearance]'));
  const dialog=document.createElement('dialog');dialog.id='personalizationDialog';dialog.setAttribute('aria-label','Personalization');
  dialog.innerHTML='<h2>Personalization</h2><p>First colour: your sent message bubbles.<br>Second colour: received message bubbles.<br>The OrbitChat and OrbitPlay headings follow your pair. Other text and buttons keep the app theme.</p><label for="paletteChoice">Colour pair — first / second</label><select id="paletteChoice"></select><div class="pair-preview"><div class="palette-preview received-preview" data-pair-role="second">Received message · second colour</div><div class="palette-preview sent-preview" data-pair-role="first">Your sent message · first colour</div></div><p id="paletteStatus" role="status"></p><div class="row"><button type="button" id="savePalette">Save colours</button><button type="button" id="closePalette">Close</button></div>';
  document.body.append(dialog);
  button.onclick=()=>{draft=null;document.getElementById('paletteStatus').textContent='';dialog.showModal();render();refresh(true)};
  document.getElementById('savePalette').onclick=save;document.getElementById('closePalette').onclick=()=>{draft=null;dialog.close()};
  document.getElementById('paletteChoice').onchange=e=>{draft=e.target.value;preview(choices.find(p=>p.id===draft))};
 }
 window.OrbitPersonalization={refresh};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{mount();refresh(true)});else{mount();refresh(true)}
 setInterval(()=>refresh(),2000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh(true)});window.addEventListener('storage',()=>refresh(true));
})();
