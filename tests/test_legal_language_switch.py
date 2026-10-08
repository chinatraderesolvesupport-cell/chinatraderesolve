"""Exercise the shipped legal/sample-page language handler in a small DOM harness."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_sample_language_switch_survives_refresh():
    if not shutil.which("node"):
        pytest.skip("Node.js is required for the browser-script regression")
    script = Path(__file__).resolve().parents[1] / "app/static/legal-i18n-v2.js"
    harness = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const select = {value: '', setAttribute() {}};
let current = 'https://chinatraderesolve.com/static/sample_case_assessment.html?lang=ru&utm_source=test';
const storage = new Map();
const context = {
  URL, URLSearchParams,
  navigator: {language: 'ru'},
  localStorage: {getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value)},
  document: {
    body: {dataset: {legalPage: 'sample'}}, documentElement: {lang: ''}, title: '',
    getElementById: () => select, querySelectorAll: () => [],
    querySelector: () => ({href: ''})
  },
  window: {
    location: {get href() {return current}, get search() {return new URL(current).search}},
    history: {replaceState(_state, _title, url) {current = String(url)}},
    addEventListener(_event, callback) {this.ready = callback}
  }
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.window.ready();
assert.equal(select.value, 'ru');
select.onchange({target: {value: 'en'}});
assert.equal(new URL(current).searchParams.get('lang'), 'en');
assert.equal(new URL(current).searchParams.get('utm_source'), 'test');
context.window.ready(); // Simulate page boot after refreshing the new URL.
assert.equal(select.value, 'en');
"""
    result = subprocess.run(["node", "-e", harness, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
