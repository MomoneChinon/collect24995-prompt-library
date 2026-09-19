/** Copy data/prompts.json into public/data endpoints for GitHub Pages / Deno static serve. */
import { ensureDir } from "https://deno.land/std@0.224.0/fs/ensure_dir.ts";

const root = new URL("..", import.meta.url).pathname;
const dataPath = `${root}/data/prompts.json`;
const pub = `${root}/public/data`;

const raw = await Deno.readTextFile(dataPath);
const doc = JSON.parse(raw) as {
  meta: Record<string, unknown>;
  prompts: Array<Record<string, unknown> & { id: number }>;
};

await ensureDir(`${pub}/by-id`);
await Deno.writeTextFile(`${pub}/prompts.json`, JSON.stringify(doc, null, 2) + "\n");

const prompts = doc.prompts ?? [];
const latest = prompts.length
  ? prompts.reduce((a, b) => (a.id >= b.id ? a : b))
  : null;
await Deno.writeTextFile(
  `${pub}/latest.json`,
  JSON.stringify(latest ?? {}, null, 2) + "\n",
);

const index: Record<string, { main_status_id?: unknown; reply_status_id?: unknown }> = {};
for (const p of prompts) {
  index[String(p.id)] = {
    main_status_id: p.main_status_id,
    reply_status_id: p.reply_status_id,
  };
  await Deno.writeTextFile(
    `${pub}/by-id/${p.id}.json`,
    JSON.stringify(p, null, 2) + "\n",
  );
}
await Deno.writeTextFile(
  `${pub}/index.json`,
  JSON.stringify({ meta: doc.meta, index }, null, 2) + "\n",
);

console.log(`synced ${prompts.length} prompts → public/data`);
