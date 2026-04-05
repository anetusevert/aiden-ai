import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const t = fs.readFileSync(
  path.join(__dirname, '../src/lib/workflowRegistry.ts'),
  'utf8'
);

const workflows = {};
const re =
  /id: '(LITIGATION_[A-Z0-9_]+|CORPORATE_[A-Z0-9_]+|COMPLIANCE_[A-Z0-9_]+|EMPLOYMENT_[A-Z0-9_]+|ARBITRATION_[A-Z0-9_]+|ENFORCEMENT_[A-Z0-9_]+|RESEARCH_[A-Z0-9_]+|MANAGEMENT_[A-Z0-9_]+)',\s*\n\s*name: '((?:\\'|[^'])*)',\s*\n\s*name_ar: '((?:\\'|[^'])*)'/g;

let m;
while ((m = re.exec(t)) !== null) {
  const unesc = (s) => s.replace(/\\'/g, "'");
  workflows[m[1]] = { en: unesc(m[2]), ar: unesc(m[3]) };
}

console.log('workflow count', Object.keys(workflows).length);
fs.writeFileSync(
  path.join(__dirname, '../messages/_workflows-seed.json'),
  JSON.stringify(workflows, null, 2)
);
