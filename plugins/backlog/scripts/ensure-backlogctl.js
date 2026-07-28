#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const https = require('node:https');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { URL } = require('node:url');

const root = path.resolve(__dirname, '..');
const manifestPath = path.join(root, 'assets', 'backlogctl-release.json');
const RELEASE_REPO_PATH = '/cadugevaerd/backlogctl-releases/releases/download/';
const OFFICIAL_HOSTS = new Set([
  'github.com',
  'release-assets.githubusercontent.com',
  'objects.githubusercontent.com',
]);
const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const HEX64 = /^[a-f0-9]{64}$/i;
const PLATFORMS = new Set(['linux', 'darwin', 'win32']);
const ARCHES = new Set(['x64', 'arm64']);
const REQUEST_TIMEOUT_MS = 30000;

function fail(message) {
  throw new Error(`backlogctl bootstrap failed: ${message}`);
}

function readManifest(file = manifestPath) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`invalid manifest: ${error.message}`);
  }
}

function validateManifest(manifest) {
  if (!manifest || manifest.schema_version !== 1 || manifest.status !== 'released' || manifest.product !== 'backlogctl') {
    fail('invalid schema/status/product');
  }
  if (typeof manifest.version !== 'string' || !SEMVER.test(manifest.version) || manifest.release !== `v${manifest.version}`) {
    fail('invalid version/release');
  }

  let base;
  try {
    base = new URL(manifest.base_url);
  } catch {
    fail('invalid base_url');
  }
  const expectedPath = `${RELEASE_REPO_PATH}v${manifest.version}/`;
  if (base.protocol !== 'https:' || base.hostname !== 'github.com' || base.pathname !== expectedPath || base.search || base.hash || base.username || base.password) {
    fail('base_url must be the official immutable HTTPS release URL');
  }

  if (!manifest.assets || typeof manifest.assets !== 'object' || Array.isArray(manifest.assets)) {
    fail('missing assets');
  }
  for (const [key, asset] of Object.entries(manifest.assets)) {
    const split = key.lastIndexOf('-');
    const platform = key.slice(0, split);
    const arch = key.slice(split + 1);
    if (!PLATFORMS.has(platform) || !ARCHES.has(arch) || !asset || typeof asset.file !== 'string' || path.basename(asset.file) !== asset.file || asset.file.includes('..') || /[\\/]/.test(asset.file) || !HEX64.test(asset.sha256)) {
      fail(`invalid asset ${key}`);
    }
  }
  return manifest;
}

function assetFor(manifest, platform = process.platform, arch = process.arch) {
  if (!PLATFORMS.has(platform) || !ARCHES.has(arch)) {
    fail(`unsupported platform ${platform}/${arch}`);
  }
  const asset = manifest.assets[`${platform}-${arch}`];
  if (!asset) {
    fail('no release asset for this platform');
  }
  return asset;
}

function safeInstallDir(directory) {
  if (!directory || typeof directory !== 'string') {
    fail('--install-dir is required');
  }
  const absolute = path.resolve(directory);
  if (fs.existsSync(absolute)) {
    const stat = fs.lstatSync(absolute);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      fail('install directory must be a real directory');
    }
  } else {
    fs.mkdirSync(absolute, { recursive: true, mode: 0o700 });
    const stat = fs.lstatSync(absolute);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      fail('invalid install directory');
    }
  }
  return absolute;
}

function sha(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function allowedRedirect(from, to) {
  return from.protocol === 'https:' && to.protocol === 'https:' && OFFICIAL_HOSTS.has(from.hostname) && OFFICIAL_HOSTS.has(to.hostname) && !to.username && !to.password;
}

function download(url, redirects = 0, maxRedirects = 5) {
  return new Promise((resolve, reject) => {
    let parsed;
    try {
      parsed = new URL(url);
    } catch {
      reject(new Error('invalid download URL'));
      return;
    }
    if (parsed.protocol !== 'https:' || !OFFICIAL_HOSTS.has(parsed.hostname) || parsed.username || parsed.password) {
      reject(new Error('download host is not official HTTPS'));
      return;
    }

    const request = https.get(parsed, {
      timeout: REQUEST_TIMEOUT_MS,
      headers: {
        'User-Agent': `backlogctl-bootstrap/${validateManifest(readManifest()).version}`,
        Accept: 'application/octet-stream',
      },
    }, (response) => {
      response.on('error', reject);
      if ([301, 302, 303, 307, 308].includes(response.statusCode)) {
        response.resume();
        if (redirects >= maxRedirects) {
          reject(new Error('too many redirects'));
          return;
        }
        const next = new URL(response.headers.location || '', parsed);
        if (!allowedRedirect(parsed, next)) {
          reject(new Error('redirect host is not official HTTPS'));
          return;
        }
        download(next.toString(), redirects + 1, maxRedirects).then(resolve, reject);
        return;
      }
      if (response.statusCode !== 200) {
        response.resume();
        reject(new Error(`download HTTP ${response.statusCode}`));
        return;
      }
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => resolve(Buffer.concat(chunks)));
    });
    request.on('timeout', () => request.destroy(new Error('download timed out')));
    request.on('error', reject);
  });
}

function verifyExecutable(file, expectedVersion) {
  const result = spawnSync(file, ['version'], { encoding: 'utf8', timeout: 10000, windowsHide: true });
  if (result.error || result.status !== 0 || result.stdout.trim() !== expectedVersion) {
    fail(`executable version verification failed for ${expectedVersion}`);
  }
}

async function install({
  manifest = validateManifest(readManifest()),
  installDir,
  os = process.platform,
  arch = process.arch,
  downloader = download,
  verifier = verifyExecutable,
  expectedSha256,
} = {}) {
  const asset = assetFor(manifest, os, arch);
  const outputDir = safeInstallDir(installDir);
  const targetName = asset.file.endsWith('.exe') ? 'backlogctl.exe' : 'backlogctl';
  const target = path.join(outputDir, targetName);

  if (expectedSha256 !== undefined && (!HEX64.test(expectedSha256) || expectedSha256.toLowerCase() !== asset.sha256.toLowerCase())) {
    fail('expected-sha256 does not match manifest');
  }

  if (fs.existsSync(target)) {
    const stat = fs.lstatSync(target);
    if (stat.isSymbolicLink() || !stat.isFile()) {
      fail('existing target is not a regular file');
    }
    if (sha(fs.readFileSync(target)) === asset.sha256.toLowerCase()) {
      verifier(target, manifest.version);
      return target;
    }
  }

  const data = await downloader(new URL(asset.file, manifest.base_url).toString());
  if (sha(data) !== asset.sha256.toLowerCase()) {
    fail('checksum mismatch');
  }

  const nonce = `${process.pid}-${crypto.randomBytes(16).toString('hex')}`;
  const temporary = path.join(outputDir, `.backlogctl-${nonce}.tmp`);
  const rollback = path.join(outputDir, `.backlogctl-${nonce}.rollback`);
  let targetMoved = false;
  let targetInstalled = false;

  try {
    const fd = fs.openSync(temporary, 'wx', 0o700);
    try {
      fs.writeFileSync(fd, data);
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    if (os !== 'win32') {
      fs.chmodSync(temporary, 0o700);
    }
    if (sha(fs.readFileSync(temporary)) !== asset.sha256.toLowerCase()) {
      fail('temporary checksum mismatch');
    }
    verifier(temporary, manifest.version);

    if (fs.existsSync(target)) {
      fs.renameSync(target, rollback);
      targetMoved = true;
    }
    fs.renameSync(temporary, target);
    targetInstalled = true;
    if (sha(fs.readFileSync(target)) !== asset.sha256.toLowerCase()) {
      fail('installed checksum mismatch');
    }
    verifier(target, manifest.version);
    if (targetMoved) {
      fs.rmSync(rollback, { force: true });
    }
    return target;
  } catch (error) {
    fs.rmSync(temporary, { force: true });
    if (targetInstalled) {
      fs.rmSync(target, { force: true });
    }
    if (targetMoved) {
      if (fs.existsSync(rollback)) {
        fs.renameSync(rollback, target);
      }
    }
    fail(error.message);
  }
}

function parseArgs(args, pluginData = process.env.CLAUDE_PLUGIN_DATA || '') {
  let installDir = '';
  let expectedSha256;
  let hook = false;
  const seen = new Set();

  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (!['--install-dir', '--expected-sha256', '--hook'].includes(argument)) {
      fail(`unknown argument ${argument}`);
    }
    if (seen.has(argument)) {
      fail(`duplicate argument ${argument}`);
    }
    seen.add(argument);
    if (argument === '--hook') {
      hook = true;
      continue;
    }
    const value = args[index + 1];
    if (!value || value.startsWith('--')) {
      fail(`missing ${argument} value`);
    }
    index += 1;
    if (argument === '--install-dir') {
      installDir = path.resolve(value);
    } else {
      expectedSha256 = value;
    }
  }

  if (!installDir && pluginData) {
    installDir = path.resolve(pluginData, 'bin');
  }
  if (!installDir) {
    fail('--install-dir is required');
  }
  if (expectedSha256 !== undefined && !HEX64.test(expectedSha256)) {
    fail('invalid --expected-sha256');
  }
  return { installDir, expectedSha256, hook };
}

function hookPayload(executable) {
  return {
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: `BACKLOGCTL_EXECUTABLE=${executable}. Use this verified executable by exact path; do not assume it is on PATH.`,
    },
  };
}

async function main() {
  const manifest = validateManifest(readManifest());
  const parsed = parseArgs(process.argv.slice(2));
  const executable = await install({
    manifest,
    installDir: parsed.installDir,
    expectedSha256: parsed.expectedSha256,
  });
  if (parsed.hook) {
    process.stdout.write(`${JSON.stringify(hookPayload(executable))}\n`);
  } else {
    process.stdout.write(`${executable}\n`);
  }
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  allowedRedirect,
  assetFor,
  hookPayload,
  install,
  parseArgs,
  safeInstallDir,
  sha,
  validateManifest,
  verifyExecutable,
};
