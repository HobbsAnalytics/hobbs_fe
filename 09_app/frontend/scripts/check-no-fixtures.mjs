// Post-build guard: fail if any dev/test fixture reached the production bundle.
// Run automatically by `npm run build`; also usable on its own: `node scripts/check-no-fixtures.mjs [distDir]`.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const dist = resolve(process.argv[2] ?? 'dist');
// Strings that exist only in src/fixtures/*: the marker, the canned conversation id, the sample PDF asset name and
// the fixture installer's log line.
const NEEDLES = ['__BLUERRIDGE_FIXTURE__', 'fixture-conv-0001', 'sample-drawing', 'serving /api/* from src/fixtures'];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

let files;
try {
  files = walk(dist);
} catch {
  console.error(`check-no-fixtures: ${dist} not found; run vite build first`);
  process.exit(1);
}

const hits = [];
for (const f of files) {
  if (f.toLowerCase().includes('sample-drawing')) hits.push(`${f}: fixture asset file`);
  if (!/\.(js|mjs|css|html|json|map)$/.test(f)) continue;
  const text = readFileSync(f, 'utf8');
  for (const n of NEEDLES) if (text.includes(n)) hits.push(`${f}: contains "${n}"`);
}

if (hits.length) {
  console.error('check-no-fixtures: FAIL, fixture content found in the production build:\n  ' + hits.join('\n  '));
  process.exit(1);
}
console.log(`check-no-fixtures: OK, ${files.length} files in ${dist}, no fixture strings or assets`);
