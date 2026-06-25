import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, '../../../data/replay/disk-space-run.events.jsonl');
const target = resolve(
  here,
  '../public/data/replay/disk-space-run.events.jsonl',
);

mkdirSync(dirname(target), { recursive: true });
copyFileSync(source, target);

