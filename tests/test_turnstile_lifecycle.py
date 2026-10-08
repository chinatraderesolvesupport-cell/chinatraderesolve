"""Exercise the application widget timing without contacting Cloudflare."""

import subprocess
from pathlib import Path


def test_application_challenge_starts_only_when_form_is_complete():
    template = (Path(__file__).parents[1] / "app/templates/index.html").read_text()
    assert 'data-execution="execute"' in template
    source = template.split("const descriptionField=document.getElementById('description');", 1)[1]
    source = "const descriptionField=document.getElementById('description');" + source.split(
        "function updateDescriptionCount()", 1
    )[0]
    script = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const calls = [];
const field = (value) => ({value, validity:{valid:true}});
const fields = {
  description:field('A fictional complaint with enough detail to pass the fifty character minimum.'),
  fullName:field('Test Client'),email:field('test@example.com'),
  channel:field('Alibaba'),mainProblem:field('Quality'),
  descriptionCount:{textContent:''},submitBtn:{disabled:true,setAttribute(){}},
  applicationTurnstileStatus:{textContent:'',dataset:{}},
};
const consents = [{checked:false},{checked:false},{checked:false}];
const context = {
  document:{getElementById:(id)=>fields[id]||null, documentElement:{lang:'ru'}},
  caseFormElement:{querySelectorAll:()=>consents},
  window:{CTR_TRANSLATIONS:{ru:{application_turnstile_loading:'Loading',
    application_turnstile_ready:'Ready',application_turnstile_required:'Required',
    application_turnstile_error:'Error',form_incomplete_status:'Incomplete',
    form_ready_status:'Complete'}},
    turnstile:{execute:(selector)=>calls.push(selector),reset:()=>calls.push('reset')},
    setTimeout:()=>{throw new Error('Unexpected wait')}}
};
vm.runInNewContext(SOURCE + '\n globalThis.h={updateSubmitAvailability};',context);
context.h.updateSubmitAvailability();
assert.equal(calls.length,0,'incomplete consent must not start a challenge');
consents.forEach(c=>c.checked=true);
context.h.updateSubmitAvailability();
context.h.updateSubmitAvailability();
assert.deepEqual(calls,['#applicationTurnstileWidget'],'start exactly once when ready');
assert.equal(fields.submitBtn.disabled,true,'server token is still required');
context.window.ctrApplicationTurnstileSuccess('test-token');
assert.equal(fields.submitBtn.disabled,false);
context.window.ctrApplicationTurnstileExpired();
assert.equal(fields.submitBtn.disabled,true,'expired token blocks submission');
context.window.ctrApplicationTurnstileError('600010');
assert.equal(fields.applicationTurnstileStatus.textContent,'Error (600010)');
assert.equal(fields.submitBtn.disabled,true);
""".replace("SOURCE", __import__("json").dumps(source))
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
