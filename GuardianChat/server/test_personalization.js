const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const store=new Map(),styles={},requests=[];
store.set('guardianchat-account',JSON.stringify({id:'alpha',token:'alpha-session'}));
const ctx={JSON,Date,console,localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},window:{addEventListener(){}},document:{readyState:'loading',documentElement:{dataset:{},style:{setProperty:(k,v)=>styles[k]=v}},getElementById:()=>null,addEventListener(){}},setInterval(){},fetch:(path,opts)=>new Promise(resolve=>requests.push({path,opts,resolve}))};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(__dirname+'/personalization.js','utf8'),ctx);
const choices=JSON.parse(fs.readFileSync(__dirname+'/personalization.json','utf8'));
const reply=(n,id)=>requests[n].resolve({ok:true,json:async()=>({palette:id,choices})});
(async()=>{
 const a=ctx.window.OrbitPersonalization.refresh(true);
 store.set('guardianchat-account',JSON.stringify({id:'beta',token:'beta-session'}));
 const b=ctx.window.OrbitPersonalization.refresh(true);
 reply(0,'rose');await a;assert.equal(styles['--personal-bubble'],'#e8b84a','Old account response is ignored');
 reply(1,'ocean');await b;assert.equal(styles['--personal-bubble'],'#b8def3');assert.equal(requests[1].opts.headers.Authorization,'Bearer beta-session');assert(!store.has('xorbit-palette-alpha'));
 store.delete('guardianchat-account');await ctx.window.OrbitPersonalization.refresh(true);assert.equal(styles['--personal-bubble'],'#e8b84a','Logout clears the previous account colour');
 store.set('guardianchat-account',JSON.stringify({id:'beta',token:'new-session'}));const c=ctx.window.OrbitPersonalization.refresh(true);reply(2,'forest');await c;assert.equal(styles['--personal-bubble'],'#b9dfbd');
 console.log('Account colours ignore stale responses, reset on logout and refresh with the correct session.');
})().catch(e=>{console.error(e);process.exitCode=1});
