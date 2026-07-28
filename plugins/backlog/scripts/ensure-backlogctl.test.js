'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const bootstrap = require('./ensure-backlogctl.js');

function manifest(payload = Buffer.from('binary')) {
  return {
    schema_version: 1,
    status: 'released',
    product: 'backlogctl',
    release: 'v2.1.0',
    version: '2.1.0',
    base_url: 'https://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.1.0/',
    assets: {
      'linux-x64': {
        file: 'backlogctl_linux_amd64',
        sha256: crypto.createHash('sha256').update(payload).digest('hex'),
      },
    },
  };
}

test('manifest accepts only immutable official release coordinates', () => {
  assert.doesNotThrow(() => bootstrap.validateManifest(manifest()));
  for (const mutate of [
    m => { m.base_url = 'https://evil.example/releases/download/v2.1.0/'; },
    m => { m.base_url = 'http://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.1.0/'; },
    m => { m.base_url = 'https://github.com/cadugevaerd/other/releases/download/v2.1.0/'; },
    m => { m.base_url = 'https://github.com/cadugevaerd/backlogctl-releases/releases/download/v9.9.9/'; },
    m => { m.assets['linux-x64'].file = '../backlogctl'; },
    m => { m.assets['linux-x64'].sha256 = 'abc'; },
  ]) {
    const m = manifest(); mutate(m);
    assert.throws(() => bootstrap.validateManifest(m));
  }
});

test('redirects remain inside official HTTPS release paths', () => {
  const from = new URL('https://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.1.0/a');
  assert.equal(bootstrap.allowedRedirect(from, new URL('https://objects.githubusercontent.com/x')), true);
  assert.equal(bootstrap.allowedRedirect(from, new URL('https://release-assets.githubusercontent.com/x')), true);
  assert.equal(bootstrap.allowedRedirect(from, new URL('http://objects.githubusercontent.com/x')), false);
  assert.equal(bootstrap.allowedRedirect(from, new URL('https://evil.example/x')), false);
});

test('argument parser rejects unknown, duplicate and malformed flags', () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'backlog-args-'));
  try {
    assert.equal(bootstrap.parseArgs(['--install-dir', base], {}).installDir, path.resolve(base));
    assert.throws(() => bootstrap.parseArgs(['--unknown'], {}));
    assert.throws(() => bootstrap.parseArgs(['--hook', '--hook'], {}));
    assert.throws(() => bootstrap.parseArgs(['--install-dir'], {}));
    assert.throws(() => bootstrap.parseArgs(['--expected-sha256', 'abc'], {}));
  } finally { fs.rmSync(base, { recursive: true, force: true }); }
});

test('install verifies temporary executable and preserves prior binary on failure', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'backlog-install-'));
  const target = path.join(dir, 'backlogctl');
  const old = Buffer.from('old');
  const good = Buffer.from('new-good');
  fs.writeFileSync(target, old, { mode: 0o700 });
  try {
    await assert.rejects(() => bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => Buffer.from('bad'), verifier: () => {} }));
    assert.deepEqual(fs.readFileSync(target), old);

    await assert.rejects(() => bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => good,
      verifier: () => { throw new Error('wrong version'); } }));
    assert.deepEqual(fs.readFileSync(target), old);

    let verifies = 0;
    const result = await bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => good,
      verifier: () => { verifies += 1; } });
    assert.equal(result, target);
    assert.deepEqual(fs.readFileSync(target), good);
    assert.ok(verifies >= 2);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('safe install directory and hook payload are deterministic', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'backlog-safe-'));
  try {
    const real = path.join(root, 'real'); fs.mkdirSync(real);
    const link = path.join(root, 'link'); fs.symlinkSync(real, link);
    assert.throws(() => bootstrap.safeInstallDir(link));
    const payload = bootstrap.hookPayload('/tmp/backlogctl');
    assert.equal(payload.hookSpecificOutput.hookEventName, 'SessionStart');
    assert.match(payload.hookSpecificOutput.additionalContext, /BACKLOGCTL_EXECUTABLE=\/tmp\/backlogctl/);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
