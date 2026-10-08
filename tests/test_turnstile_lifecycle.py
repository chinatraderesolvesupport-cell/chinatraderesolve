"""Exercise the application widget lifecycle with a stubbed Turnstile API."""

import json
import subprocess
from pathlib import Path


def test_application_challenge_waits_for_visible_step_and_recovers_after_expiry():
    template = (Path(__file__).parents[1] / "app/templates/index.html").read_text()
    source = template.split("const descriptionField=document.getElementById('description');", 1)[1]
    source = "const descriptionField=document.getElementById('description');" + source.split(
        "function updateDescriptionCount()", 1
    )[0]
    script = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const calls = [];
const handlers = {};
const field = (value) => ({value, validity:{valid:true}});
const stepTwo = {active:false,classList:{contains:()=>stepTwo.active}};
const fields = {
  description:field('A fictional complaint with enough detail to pass the fifty character minimum.'),
  fullName:field('Test Client'),email:field('test@example.com'),
  channel:field('Alibaba'),mainProblem:field('Quality'),
  stepTwo,descriptionCount:{textContent:''},submitBtn:{disabled:true,setAttribute(){}},
  applicationTurnstileWidget:{dataset:{sitekey:'test-sitekey'},clientWidth:450},
  applicationTurnstileRetry:{hidden:true,addEventListener:(type,fn)=>handlers[type]=fn},
  applicationTurnstileStatus:{textContent:'',dataset:{}},
};
const consents = [{checked:false},{checked:false},{checked:false}];
const context = {
  document:{getElementById:(id)=>fields[id]||null, documentElement:{lang:'ru'},addEventListener:()=>{}},
  caseFormElement:{querySelectorAll:()=>consents},
  window:{CTR_TRANSLATIONS:{ru:{application_turnstile_loading:'Loading',
    application_turnstile_ready:'Ready',application_turnstile_required:'Required',
    application_turnstile_error:'Error',form_incomplete_status:'Incomplete',
    form_ready_status:'Complete'}},
    turnstile:{render:(mount,options)=>{calls.push('render');assert.equal(mount,fields.applicationTurnstileWidget);assert.equal(options.execution,'execute');assert.equal(options['response-field'],false);handlers.widget=options;return 'widget-1'},
      execute:(id)=>calls.push(`execute:${id}`),reset:(id)=>calls.push(`reset:${id}`),remove:(id)=>calls.push(`remove:${id}`)},
    setTimeout:()=>{throw new Error('Unexpected wait')}}
};
vm.runInNewContext(SOURCE + '\n globalThis.h={updateSubmitAvailability,removeApplicationTurnstile,getToken:()=>applicationTurnstileToken};',context);
context.h.updateSubmitAvailability();
assert.equal(calls.length,0,'the hidden step must not render a widget');
stepTwo.active=true;
context.h.updateSubmitAvailability();
assert.deepEqual(calls,['render'],'visible step renders once, without executing');
consents.forEach(c=>c.checked=true);
context.h.updateSubmitAvailability();
context.h.updateSubmitAvailability();
assert.deepEqual(calls,['render','execute:widget-1'],'execute exactly once when ready');
assert.equal(fields.submitBtn.disabled,true,'server token is still required');
handlers.widget.callback('test-token');
assert.equal(context.h.getToken(),'test-token');
assert.equal(fields.submitBtn.disabled,false);
handlers.widget['expired-callback']();
assert.equal(context.h.getToken(),'');
assert.equal(fields.submitBtn.disabled,true);
assert.deepEqual(calls.slice(-2),['reset:widget-1','execute:widget-1'],'expiry starts a fresh challenge');
handlers.widget['error-callback']('600010');
assert.equal(fields.applicationTurnstileStatus.textContent,'Error (600010)');
assert.equal(fields.applicationTurnstileRetry.hidden,false);
assert.equal(fields.submitBtn.disabled,true);
handlers.click();
assert.deepEqual(calls.slice(-2),['reset:widget-1','execute:widget-1'],'retry starts a fresh challenge');
stepTwo.active=false;
context.h.removeApplicationTurnstile();
assert.equal(context.h.getToken(),'');
assert.equal(calls.at(-1),'remove:widget-1');
""".replace("SOURCE", json.dumps(source))
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
