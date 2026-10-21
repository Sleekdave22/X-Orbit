/* Account discovery is separate from contacts and never grants messaging access. */
(()=>{
 let version=0,query='',next=null,ownerId=account?.id;
 const form=el('globalSearchForm'),input=el('globalSearchQuery'),status=el('globalSearchStatus'),results=el('globalSearchResults'),more=el('globalSearchMore');
 window.OrbitAccountSearch={resetForAccount(){if(ownerId===account?.id)return;ownerId=account?.id;version++;query='';next=null;input.value='';results.replaceChildren();status.textContent='';more.hidden=true}};
 async function search(append=false){
  const owner=account?.id,current=++version;
  if(!owner)return;
  if(!append)query=input.value.trim();
  if(query.replace(/^@/,'').length<2){status.textContent='Enter at least 2 characters';return}
  const offset=append?next:0;
  more.hidden=true;status.textContent='Searching…';
  if(!append)results.replaceChildren();
  try{
   const data=await api('/social/search?q='+encodeURIComponent(query)+'&offset='+(offset||0));
   if(version!==current||account?.id!==owner)return;
   for(const u of data.users){
    const row=document.createElement('div');row.className='account-result';
    const open=document.createElement('button');open.type='button';open.title='View this account and its connection options';
    const photo=document.createElement('span');photo.className='avatar';
    if(u.avatar){const img=document.createElement('img');img.src='data:'+u.avatar_mime+';base64,'+u.avatar;img.alt='';photo.append(img)}else photo.textContent=u.name.slice(0,1);
    const name=document.createElement('span');name.textContent=u.name;
    const detail=document.createElement('small');detail.textContent='@'+u.nickname+(u.contact?' · In your chats':'');name.append(detail);
    open.append(photo,name);open.onclick=()=>openSocialProfile(u.id);row.append(open);results.append(row);
   }
   next=data.next_offset;more.hidden=next===null;status.textContent=results.childElementCount?'Select an account to view its profile.':'No matching accounts. Try an exact @nickname or account ID.';
  }catch(e){if(version===current&&account?.id===owner){status.textContent=e.message;more.hidden=!append||next===null}}
 }
 form.onsubmit=e=>{e.preventDefault();search()};more.onclick=()=>search(true);
 input.oninput=()=>{version++;next=null;more.hidden=true;results.replaceChildren();status.textContent=''};
})();
