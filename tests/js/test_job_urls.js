const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('static/pro.js', 'utf8');
const start = src.indexOf('const JOB_SECTIONS');
const end = src.indexOf('const TAB_PATHS', start);
const context = {};
vm.createContext(context);
vm.runInContext(src.slice(start, end), context);
const parse = context.parseJobPath;
function eq(path, expected) {
  const got = JSON.parse(JSON.stringify(parse(path)));
  if (JSON.stringify(got) !== JSON.stringify(expected)) throw new Error(`${path}: ${JSON.stringify(got)}`);
}
eq('/runspace/my-bot', {slug:'my-bot',section:'editor',legacy:false});
eq('/runspace/my-bot/logs', {slug:'my-bot',section:'logs',legacy:false});
eq('/runspace/my-bot/database/', {slug:'my-bot',section:'database',legacy:false});
eq('/runspace/owner/my-bot', {slug:'my-bot',section:'editor',legacy:true});
eq('/runspace/owner/my-bot/page', {slug:'my-bot',section:'details',legacy:true});
eq('/runspace/logs', {slug:'logs',section:'editor',legacy:false});
if (!parse('/runspace/my-bot/typo/extra')?.invalid) throw new Error('mistyped section accepted');
console.log('7 job URL checks passed');
