const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { expressions } = require("../src/expressions.cjs");

const outfits = {
  school: { label: "ชุดนักเรียน", folder: "pink_bun_winefox" },
  white: { label: "เชิ้ตขาว", folder: "pink_bun_winefox_white" },
};
const editions = { square: "รุ่นตาเหลี่ยม", original: "รุ่นเดิม" };
const portraits = Object.entries(expressions).map(([clip, label]) => ({
  id: clip,
  clip,
  label,
  view: "front",
  referenceView: "bust",
  times: [0],
}));
const motion = [
  { clip: "idle", label: "ยืนพัก", bustTime: 1, times: [1, 12, 18.5, 22, 25] },
  { clip: "run", label: "วิ่ง", bustTime: 0.12, times: [0, 0.12, 0.24, 0.36, 0.48] },
];
const lowLight = [
  ["idle", "ยืนพัก", 1],
  ["run", "วิ่ง", 0.12],
  ["face_spiral_blank", "ตาก้นหอย", 0],
  ["face_wink", "ขยิบตา", 0],
  ["face_closed", "หลับตา", 0],
  ["idle", "กะพริบตา", 0.12, true],
];
const shots = [
  ...portraits,
  ...motion.map(({ clip, label, bustTime }) => ({
    id: `${clip}-bust`,
    clip,
    label: `สีหน้าตอน${label}`,
    view: "front",
    referenceView: "bust",
    times: [bustTime],
  })),
  ...motion.map(({ clip, label, times }) => ({
    id: clip,
    clip,
    label,
    view: "front3q",
    referenceView: "full",
    times,
  })),
  {
    id: "jump-bust",
    clip: "jump",
    label: "สีหน้าตอนกระโดด",
    view: "front",
    referenceView: "bust",
    times: [0, 0.12, 0.24, 0.4, 0.58, 0.74],
  },
  ...lowLight.map(([clip, label, time, blink = false]) => ({
    id: `${clip}-night${blink ? "-blink" : ""}`,
    clip,
    label,
    view: "front",
    referenceView: "bust",
    lighting: "night",
    blink,
    times: [time],
  })),
];

function framePair(pair, label) {
  return `<div class="pair">${Object.entries(editions)
    .map(([edition, title]) => {
      const file = pair[edition].file;
      return `<figure><a href="${file}"><img src="${file}" alt="${label} ${title}" width="512" height="512" loading="lazy"></a><figcaption>${title}</figcaption></figure>`;
    })
    .join("")}</div>`;
}

function outfitSection(outfit, cases) {
  const label = outfits[outfit].label;
  const busts = cases.filter((item) => item.frames.length === 1 && !item.lighting);
  const dark = cases.filter((item) => item.lighting === "night");
  const actions = cases.filter((item) => item.frames.length > 1);
  const renderPortraits = (items) => `<div class="portraits">${items
    .map((item) => `<article class="card"><h4>${item.label}</h4>${framePair(item.frames[0], item.label)}</article>`)
    .join("\n")}</div>`;
  return `<section id="${outfit}">
  <h2>${label}</h2>
  <section id="${outfit}-glow"><h3>ตาเรืองแสงในที่มืด</h3>${renderPortraits(dark)}</section>
  <h3>สีหน้าในแสงปกติ</h3>${renderPortraits(busts)}
  ${actions
    .map(
      (item) => `<details class="card" id="${outfit}-${item.id}"${item.clip === "jump" ? " open" : ""}><summary>${item.label} · ${item.frames.length} เฟรม · ${item.view === "front" ? "มุมหน้าระยะใกล้" : "มุมเฉียงหน้า"}</summary>
    <div class="motion">${item.frames
      .map(
        (frame) => `<figure class="sample"><figcaption>${frame.time} วินาที</figcaption>${framePair(frame, item.label)}</figure>`,
      )
      .join("\n")}</div></details>`,
    )
    .join("\n")}</section>`;
}

function page(cases) {
  return `<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Satou YSM · เปรียบเทียบรุ่นตาเหลี่ยม</title>
<style>
:root{color-scheme:dark;--page:#1a151d;--card:#28202b;--line:#514257;--text:#fcf0f6;--pink:#ffc8df;--muted:#dccbdc}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--text);font:16px/1.55 system-ui,"Leelawadee UI",sans-serif}
main{max-width:1180px;margin:auto;padding:36px clamp(14px,4vw,48px) 48px}h1,h2,h3,h4,p,figure{margin:0}
h1{font-size:clamp(1.7rem,5vw,3rem);line-height:1.2}h2{margin-bottom:12px}h3{margin-bottom:10px}h4,summary{font-size:1rem;font-weight:650}
header p{margin:8px 0 18px;color:var(--muted)}a{color:var(--pink)}nav{display:flex;flex-wrap:wrap;gap:8px}
nav a{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 12px;text-decoration:none}
section{margin-top:28px}.portraits,.motion{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,405px),1fr));gap:12px}
section[id$="-glow"]{margin:16px 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:clamp(8px,2vw,16px)}
.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:8px}
img{display:block;width:100%;height:auto;border-radius:5px;background:#e6e0ed}figcaption{color:var(--muted);font-size:.88rem;margin-top:3px}
.pair figure:first-child figcaption{color:var(--pink)}details{margin-top:12px}summary{cursor:pointer}.motion{margin-top:10px}
.sample{border-top:1px solid var(--line);padding-top:8px}.sample>figcaption{color:var(--text)}footer{margin-top:30px}
</style>
</head>
<body><main>
<header><h1>Satou YSM รุ่นตาเหลี่ยม</h1>
<p>เทียบสีหน้าและท่าทางกับรุ่นเดิม ภาพทุกคู่เรนเดอร์จากโมเดลจริงผ่าน Model Studio ด้วยกล้องและเวลาเดียวกัน คลิกภาพเพื่อดูขนาดเต็ม</p>
<nav aria-label="เลือกชุด">${Object.entries(outfits)
    .map(([id, outfit]) => `<a href="#${id}">${outfit.label}</a>`)
    .join("")}</nav></header>
${Object.keys(outfits)
    .map((outfit) => outfitSection(outfit, cases[outfit]))
    .join("\n")}
<footer><a href="manifest.json">ข้อมูลโมเดลและเฟรม</a> · <a href="ATTRIBUTION.md">เครดิต</a></footer>
</main></body></html>`;
}

module.exports = async function compareEyes({
  root,
  readModel,
  capture,
  stamp,
  jumpVariables,
}) {
  const dist = path.join(root, "dist");
  const plan = {};
  const modelData = {};
  const cases = {};

  for (const [outfit, { folder }] of Object.entries(outfits)) {
    cases[outfit] = shots.map(({ times, ...shot }) => ({
      ...shot,
      frames: times.map((time) => ({ time })),
    }));

    for (const edition of Object.keys(editions)) {
      const key = `${outfit}-${edition}`;
      const directory = path.join(
        dist,
        edition === "square" ? `${folder}_square_eyes` : folder,
      );
      const model = readModel(outfit, directory, key);
      modelData[key] = model;
      plan[key] = cases[outfit].map(({ id, frames, ...shot }) => {
        const { clip } = shot;
        assert(model.data.animations.animations[clip], `${key}: missing ${clip}`);
        return {
          id: `${key}-${id}`,
          state: id,
          ...shot,
          frames: frames.map((pair, index) => {
            const frame = {
              time: pair.time,
              variables: clip === "jump" ? jumpVariables(pair.time) : {},
              file: `frames/${key}-${id}-${index + 1}.png`,
            };
            pair[edition] = frame;
            return frame;
          }),
        };
      });
    }
  }

  const folder = path.join(dist, "ysm-eye-reviews");
  fs.mkdirSync(folder, { recursive: true });
  const output = fs.mkdtempSync(path.join(folder, `${stamp}-`));
  fs.mkdirSync(path.join(output, "frames"));
  await capture(output, plan, modelData);

  const frames = Object.values(plan)
    .flat()
    .reduce((total, job) => total + job.frames.length, 0);
  const manifest = {
    renderer: "Model Studio / Three.js",
    camera: "Shared framing per state and view",
    frames,
    models: Object.fromEntries(
      Object.entries(modelData).map(([key, model]) => [key, model.provenance]),
    ),
    cases,
  };
  fs.writeFileSync(
    path.join(output, "manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
  );
  fs.writeFileSync(path.join(output, "index.html"), page(cases));
  for (const file of ["LICENSE", "ATTRIBUTION.md"]) {
    fs.copyFileSync(path.join(root, file), path.join(output, file));
  }
  fs.cpSync(output, path.join(dist, "viewer", "eye-review"), { recursive: true });
  console.log(path.join(output, "index.html"));
  return { output, frames };
};
