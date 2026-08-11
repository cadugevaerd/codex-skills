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
    release: 'v2.3.0',
    version: '2.3.0',
    base_url: 'https://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.3.0/',
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
    m => { m.base_url = 'https://evil.example/releases/download/v2.3.0/'; },
    m => { m.base_url = 'http://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.3.0/'; },
    m => { m.base_url = 'https://github.com/cadugevaerd/other/releases/download/v2.3.0/'; },
    m => { m.base_url = 'https://github.com/cadugevaerd/backlogctl-releases/releases/download/v9.9.9/'; },
    m => { m.assets['linux-x64'].file = '../backlogctl'; },
    m => { m.assets['linux-x64'].sha256 = 'abc'; },
  ]) {
    const m = manifest(); mutate(m);
    assert.throws(() => bootstrap.validateManifest(m));
  }
});

test('vendored manifest pins the verified backlogctl v2.4.0 release', () => {
  const vendored = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'assets', 'backlogctl-release.json'), 'utf8'));
  assert.equal(vendored.release, 'v2.4.0');
  assert.equal(vendored.version, '2.4.0');
  assert.equal(vendored.base_url, 'https://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.4.0/');
  assert.deepEqual(Object.fromEntries(Object.entries(vendored.assets).map(([key, asset]) => [key, asset.sha256])), {
    'darwin-x64': 'c3bad46bb6c99323985e0e1a59265e761934280d1b7f371fe4f9159ba08ec566',
    'darwin-arm64': '718b41e90968ed67ad181f7bea360f668a6cb554b4886e4e2690ed0710ce50b9',
    'linux-x64': '9ddb006f7ad6b1b4a588f19924cc7f7b4456e0e11796d1b3f5a74dc57b2cff99',
    'linux-arm64': '8fa6047e9634c95a9e7388ce0e486742b4cf4dda485c9240dc56791f7f945cb0',
    'win32-x64': '2dd2adbcad09f4faf84491f64f410417e12b8eae2a2d665b9d0b9065185d0f8f',
    'win32-arm64': 'e5dabdae209297c096c5c7247ef5320d3b187bd14b07067c3d2ead81afa1a510',
  });
});

test('redirects remain inside official HTTPS release paths', () => {
  const from = new URL('https://github.com/cadugevaerd/backlogctl-releases/releases/download/v2.3.0/a');
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

test('install verifies temporary executable, preserves prior binary and cleans failed fresh install', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'backlog-install-'));
  const cleanDir = fs.mkdtempSync(path.join(os.tmpdir(), 'backlog-install-clean-'));
  const target = path.join(dir, 'backlogctl');
  const cleanTarget = path.join(cleanDir, 'backlogctl');
  const old = Buffer.from('old');
  const good = Buffer.from('new-good');
  fs.writeFileSync(target, old, { mode: 0o700 });
  try {
    await assert.rejects(() => bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => Buffer.from('bad'), verifier: () => {} }));
    assert.deepEqual(fs.readFileSync(target), old);

    await assert.rejects(() => bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => good,
      verifier: () => { throw new Error('backlogctl bootstrap failed: wrong version'); } }),
    error => {
      assert.equal(error.message, 'backlogctl bootstrap failed: wrong version');
      return true;
    });
    assert.deepEqual(fs.readFileSync(target), old);

    let cleanVerifies = 0;
    await assert.rejects(() => bootstrap.install({ manifest: manifest(good), installDir: cleanDir,
      os: 'linux', arch: 'x64', downloader: async () => good,
      verifier: () => {
        cleanVerifies += 1;
        if (cleanVerifies === 2) throw new Error('post-install verification failed');
      } }));
    assert.equal(fs.existsSync(cleanTarget), false);

    let verifies = 0;
    const result = await bootstrap.install({ manifest: manifest(good), installDir: dir,
      os: 'linux', arch: 'x64', downloader: async () => good,
      verifier: () => { verifies += 1; } });
    assert.equal(result, target);
    assert.deepEqual(fs.readFileSync(target), good);
    assert.ok(verifies >= 2);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
    fs.rmSync(cleanDir, { recursive: true, force: true });
  }
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
