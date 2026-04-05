import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const messagesDir = path.join(__dirname, '../messages');

const seed = JSON.parse(
  fs.readFileSync(path.join(messagesDir, '_workflows-seed.json'), 'utf8')
);

function workflowsFor(lang) {
  const o = {};
  for (const [k, v] of Object.entries(seed)) {
    o[k] = lang === 'ar' ? v.ar : v.en;
  }
  return o;
}

for (const locale of ['en', 'ar', 'fr', 'ur', 'tl']) {
  const core = JSON.parse(
    fs.readFileSync(path.join(messagesDir, `${locale}.core.json`), 'utf8')
  );
  core.workflows = workflowsFor(locale === 'ar' ? 'ar' : 'en');
  fs.writeFileSync(
    path.join(messagesDir, `${locale}.json`),
    JSON.stringify(core, null, 2),
    'utf8'
  );
}

console.log('Packed en, ar, fr, ur, tl.json');
