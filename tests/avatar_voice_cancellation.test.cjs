const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../core/web_validation.html'), 'utf8');
const source = html.slice(html.indexOf('let krishnaAvatarSpeaking='), html.indexOf('async function sendKrishnaPopup()'));

function createHarness(browserVoice=false) {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {textContent:'', value:''});
    return elements.get(id);
  };
  const timers=[];
  const synth=browserVoice ? {cancel(){},getVoices(){return []},speak(u){u.onstart();u.onend()}} : undefined;
  const context=vm.createContext({AbortController,window:{speechSynthesis:synth,
    SpeechSynthesisUtterance:browserVoice ? class {constructor(text){this.text=text}} : undefined,
    },
    SpeechSynthesisUtterance:class {constructor(text){this.text=text}},
    $:get,krishnaVoiceLanguage:()=>({short:'en',locale:'en-IN'}),
    req:(url,payload,signal)=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted')),{once:true})),
    Audio:()=>assert.fail('Cancelled synthesis must never play audio'),
    setTimeout:fn=>{timers.push(fn);return timers.length},clearTimeout(){}});
  vm.runInContext(source,context);
  return {context,get,timers};
}

test('Stop voice cancels pending synthesis and preserves stopped status',async()=>{
  const h=createHarness();
  const pending=vm.runInContext("speakKrishnaReply('Hello')",h.context);
  vm.runInContext('stopKrishnaVoice()',h.context);
  await pending;
  assert.equal(h.get('krishnaVoiceState').textContent,'Voice stopped');
});

test('Synthesis timeout releases preparing state and completes browser fallback',async()=>{
  const h=createHarness(true);
  const pending=vm.runInContext("speakKrishnaReply('Hello')",h.context);
  h.timers[0]();
  await pending;
  assert.equal(h.get('krishnaVoiceState').textContent,'Voice finished · microphone ready');
});
