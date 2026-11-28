const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const views = [
  ["front3q", "เฉียงหน้า"],
  ["front", "ด้านหน้า"],
  ["left", "ด้านซ้าย"],
  ["right", "ด้านขวา"],
  ["back", "ด้านหลัง"],
  ["back3q", "เฉียงหลัง"],
  ["top", "ด้านบน"],
  ["bottom", "ด้านล่าง"],
];
const motions = [
  ["walk", "เดิน"],
  ["run", "วิ่ง"],
  ["jump", "กระโดด"],
];
const samplePhases = [0, 0.22, 0.44, 0.66, 0.88];

function image(file, caption) {
  return `<figure><a href="${file}"><img src="${file}" alt="${caption}" width="512" height="512" loading="lazy"></a><figcaption>${caption}</figcaption></figure>`;
}

function page(shots) {
  const turnaround = shots
    .filter(({ clip, referenceView }) => clip === "idle" && referenceView === "full")
    .map(({ label, frames }) => image(frames[0].file, label))
    .join("");
  const portrait = shots.find(({ referenceView }) => referenceView === "bust");
  const motion = shots
    .filter(({ clip }) => clip !== "idle")
    .map(({ label, frames }) => {
      const thumbnails = frames
        .map(({ file, time }) => image(file, `${time.toFixed(2)} วินาที`))
        .join("");
      return `<article class="clip"><h3>${label}</h3><div class="motion">${thumbnails}</div></article>`;
    })
    .join("\n");
  return `<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Satou’s Aunt · YSM</title>
<style>
  * { box-sizing: border-box; }
  :root { color-scheme: dark; background: #191522; color: #faf2fb; }
  body { margin: 0; font: 16px/1.55 system-ui, "Leelawadee UI", sans-serif; }
  main { margin: auto; padding: 32px clamp(12px, 4vw, 48px) 40px; max-width: 1180px; }
  h1, h2, h3, p, figure { margin: 0; }
  h1 { font-size: clamp(2rem, 6vw, 3.4rem); line-height: 1.1; margin-bottom: 12px; }
  h2 { font-size: 1.3rem; margin-bottom: 12px; }
  h3 { font-size: 1rem; margin-bottom: 10px; }
  p, figcaption { color: #dfd1e3; }
  nav { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
  a { color: #ecd3fc; }
  nav a { background: #31273a; padding: 6px 12px; border-radius: 7px; }
  section, footer { margin-top: 32px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 14px; }
  .motion { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 155px), 1fr)); gap: 9px; }
  .portrait { max-width: 420px; }
  .clip { background: #252031; padding: 13px; border-radius: 9px; margin-top: 12px; }
  img { display: block; width: 100%; height: auto; border-radius: 7px; background: #e6e0ed; }
  figcaption { margin-top: 4px; }
</style></head><body><main>
<header><h1>Satou’s Aunt</h1>
<p>โมเดล YSM ดัดแปลงจาก Matured Wine Fox ภาพทุกเฟรมเรนเดอร์จากโมเดลด้วย Model Studio</p>
<nav aria-label="ส่วนของภาพพรีวิว"><a href="#views">รอบตัว</a><a href="#portrait">ใบหน้า</a><a href="#motion">การเคลื่อนไหว</a></nav></header>
<section id="views"><h2>รอบตัว</h2><div class="grid">${turnaround}</div></section>
<section id="portrait"><h2>ใบหน้าและทรงเปีย</h2><div class="portrait">${image(portrait.frames[0].file, portrait.label)}</div></section>
<section id="motion"><h2>การเคลื่อนไหว</h2>${motion}</section>
<footer><a href="manifest.json">ข้อมูลภาพและโมเดล</a> · <a href="ATTRIBUTION.md">ที่มาและสัญญาอนุญาต</a></footer>
</main></body></html>\n`;
}

module.exports = async function reviewAunt({ root, readModel, capture, stamp, jumpVariables }) {
  const key = "satou_aunt";
  const dist = path.join(root, "dist");
  const modelPath = path.join(dist, key);
  const model = readModel(key, modelPath, key);
  const animations = model.data.animations.animations;
  assert(animations.idle, "Missing idle animation");
  const shots = [
    ...views.map(([view, label]) => ({
      id: view,
      clip: "idle",
      label,
      view,
      referenceView: "full",
      times: [1],
    })),
    {
      id: "portrait",
      clip: "idle",
      label: "ภาพระยะใกล้ด้านหน้า",
      view: "front",
      referenceView: "bust",
      times: [1],
    },
    ...motions.map(([clip, label]) => {
      const duration = animations[clip]?.animation_length;
      assert(duration > 0, `Missing duration for ${clip}`);
      return {
        id: clip,
        clip,
        label,
        view: "front3q",
        referenceView: "full",
        times: samplePhases.map((fraction) => +(duration * fraction).toFixed(4)),
      };
    }),
  ].map(({ id, clip, times, ...shot }) => ({
    ...shot,
    id,
    state: id,
    clip,
    frames: times.map((time, index) => ({
      file: `frames/${id}-${index + 1}.png`,
      time,
      variables: clip === "jump" ? jumpVariables(time) : {},
    })),
  }));
  const parent = path.join(dist, "ysm-aunt-reviews");
  fs.mkdirSync(parent, { recursive: true });
  const output = fs.mkdtempSync(path.join(parent, `${stamp}-`));
  fs.mkdirSync(path.join(output, "frames"));
  await capture(output, { [key]: shots }, { [key]: model });

  const manifest = { renderer: "Model Studio / Three.js", model: model.provenance, shots };
  fs.writeFileSync(
    path.join(output, "manifest.json"),
    JSON.stringify(manifest, null, 2) + "\n",
  );
  fs.writeFileSync(path.join(output, "index.html"), page(shots));
  for (const file of ["LICENSE", "ATTRIBUTION.md"]) {
    fs.copyFileSync(path.join(modelPath, file), path.join(output, file));
  }
  fs.cpSync(output, path.join(dist, "viewer", "aunt-review"), { recursive: true });
  console.log(path.join(output, "index.html"));
  return output;
};
