const fs=require('fs'),vm=require('vm');const {JSDOM}=require('jsdom');
const JS=fs.readFileSync('static/pro.js','utf8'),HTML=fs.readFileSync('index.html','utf8'),ADMIN=fs.readFileSync('templates/admin_panel.html','utf8'),CSS=fs.readFileSync('static/app.css','utf8');
function extract(name){let s=JS.indexOf(`function ${name}(`),i=JS.indexOf('{',s),d=0;for(let k=i;k<JS.length;k++){if(JS[k]==='{')d++;else if(JS[k]==='}'&&!--d)return JS.slice(s,k+1);}throw Error(name);}
const dom=new JSDOM(HTML);const ctx={document:dom.window.document,console};vm.createContext(ctx);vm.runInContext(extract('_renderTelegramBot'),ctx);
ctx._renderTelegramBot({telegram_bot_detected:true,telegram_bot_username:'DemoHelperBot',telegram_bot_url:'https://t.me/DemoHelperBot',telegram_check_status:'verified',status:'running'});
const box=dom.window.document.getElementById('rsBotCallout');if(box.hidden||!box.classList.contains('is-live'))throw Error('live callout missing');
if(dom.window.document.getElementById('rsBotGo').href!=='https://t.me/DemoHelperBot')throw Error('bot deep link wrong');
if(!/Go to your bot/.test(box.textContent))throw Error('CTA missing');
const adom=new JSDOM(ADMIN);const ac={document:adom.window.document,console,_fmtUptime:s=>s+'s',_admAgo:x=>x,openAdminJob:()=>{},_botText:(t,v,c)=>{const e=adom.window.document.createElement(t);if(c)e.className=c;e.textContent=v??'—';return e;}};vm.createContext(ac);vm.runInContext(extract('renderAdminTelegramJobs'),ac);
const attack='<img src=x onerror=alert(1)>';ac.renderAdminTelegramJobs({detected:1,running:1,bots:[{id:1,name:attack,owner:attack,status:'running',telegram_bot_username:attack,telegram_check_status:'verified'}],events:[]});if(adom.window.document.querySelector('img'))throw Error('bot metadata became HTML');
if(!/\.rs-bot-go\s*\{[^}]*background:#229ED9/.test(CSS))throw Error('bot CTA style missing');
if(!dom.window.document.getElementById('rsTgToken')||!dom.window.document.getElementById('rsTgVerify'))throw Error('dedicated token verification section missing');
if(!/telegram_bot_username: info\.telegram_bot_username/.test(JS))throw Error('optimistic deployed job drops bot metadata');
if(!/Telegram token detected in this file/.test(JS))throw Error('uploaded bot file is not surfaced');
if(!adom.window.document.getElementById('admTelegramSection')||!adom.window.document.querySelector('.adm-section-nav'))throw Error('admin Telegram section/navigation missing');
if(!/telegram_verification_id=_rsTelegramVerificationId/.test(JS))throw Error('verified proof not sent with bot');
if(!/rs-awaiting-bot/.test(JS+CSS))throw Error('code editor is not gated behind token verification');
if(!/Add Bot 🤖/.test(HTML))throw Error('old job creation label remains');
console.log('12 Telegram bot-first UI checks passed');
