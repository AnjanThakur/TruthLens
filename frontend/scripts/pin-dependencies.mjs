import { readFile, writeFile } from 'node:fs/promises';
const manifest = JSON.parse(await readFile('package.json', 'utf8'));
const lock = JSON.parse(await readFile('package-lock.json', 'utf8'));
lock.packages[''].engines = manifest.engines;
for (const group of ['dependencies', 'devDependencies']) {
  for (const name of Object.keys(manifest[group] || {})) {
    const version = lock.packages[`node_modules/${name}`]?.version;
    if (!version) throw new Error(`No locked version for ${name}`);
    manifest[group][name] = version;
  }
  lock.packages[''][group] = manifest[group];
}
await writeFile('package.json', `${JSON.stringify(manifest, null, 2)}\n`);
await writeFile('package-lock.json', `${JSON.stringify(lock, null, 2)}\n`);
console.log('Direct dependencies pinned to installed lockfile versions.');
