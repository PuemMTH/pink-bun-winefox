const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const shots = [
  { id: "front", view: "front", clip: "idle", label: "ด้านหน้า", times: [1] },
  { id: "front3q", view: "front3q", clip: "idle", label: "เฉียงหน้า", times: [1] },
  { id: "back3q", view: "back3q", clip: "idle", label: "เฉียงหลัง", times: [1] },
  { id: "jump", view: "front3q", clip: "jump", label: "กระโดด", times: [0, 0.16, 0.4, 0.55, 0.74] },
  { id: "run", view: "front3q", clip: "run", label: "วิ่ง", times: [0, 0.12, 0.24, 0.36, 0.48] },
];
const editions = { before: "ก่อนปรับ", after: "หลังปรับ" };

function pair(shot, frame) {
  return `<div class="pair">${Object.entries(editions)
    .map(([edition, label]) => {
      const file = frame[edition].file;
      return `<figure>
        <a href="${file}"><img src="${file}" alt="${shot.label} ${label}" loading="lazy" width="512" height="512"></a>
        <figcaption>${label}</figcaption>
      </figure>`;
    })
    .join("")}</div>`;
}

function renderSection(shot) {
  if (shot.frames.length === 1)
    return `<section id="${shot.id}"><h2>${shot.label}</h2>${pair(shot, shot.frames[0])}</section>`;
  return `<section id="${shot.id}"><h2>${shot.label}</h2>
    <details><summary>ดู ${shot.frames.length} เฟรมจากมุมเฉียงหน้า</summary>
      <div class="motion">${shot.frames.map((frame) => `<article>
        <h3>${frame.time.toFixed(2)} วินาที</h3>${pair(shot, frame)}
      </article>`).join("")}</div>
    </details>
  </section>`;
}

function page(cases) {
  return `<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Satou YSM · เทียบเสื้อชุดนักเรียน</title>
<style>
  * { box-sizing: border-box; }
  :root { color-scheme: dark; background: #181820; color: #f8f2f3; }
  body { margin: 0; font: 16px/1.55 system-ui, "Leelawadee UI", sans-serif; }
  main { margin: auto; padding: 32px clamp(12px, 4vw, 48px) 48px; max-width: 1080px; }
  h1, h2, h3, p, figure { margin: 0; }
  h1 { font-size: clamp(1.55rem, 6vw, 2.8rem); }
  h2 { font-size: 1.15rem; margin: 0 0 10px; }
  h3 { font-size: .95rem; }
  p, figcaption { color: #d3cbd9; }
  nav { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
  a { color: #ffc6d8; }
  nav a { background: #292734; border-radius: 5px; padding: 5px 12px; }
  section, footer { margin-top: 28px; }
  .pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: clamp(6px, 2vw, 14px); }
  img { background: #e6e0ed; border-radius: 5px; width: 100%; height: auto; display: block; }
  figcaption { margin-top: 4px; }
  details { background: #292734; border-radius: 5px; padding: 10px 12px; }
  summary { cursor: pointer; }
  .motion { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 345px), 1fr)); gap: 12px; margin-top: 12px; }
</style></head><body><main>
<header><h1>เทียบเสื้อชุดนักเรียน Satou</h1>
<p>ภาพจากรุ่นตาเหลี่ยมที่เรนเดอร์ด้วย Model Studio แต่ละคู่ใช้กล้อง แสง และเฟรมเดียวกัน</p>
<nav aria-label="มุมกล้องและท่าทาง">${cases.map((shot) => `<a href="#${shot.id}">${shot.label}</a>`).join("")}</nav></header>
${cases.map(renderSection).join("\n")}
<footer><a href="manifest.json">ข้อมูลโมเดลและเฟรม</a> · <a href="ATTRIBUTION.md">เครดิต</a></footer>
</main></body></html>`;
}

module.exports = async function compareShirt({
  root,
  baseline,
  readModel,
  capture,
  stamp,
  jumpVariables,
}) {
  const dist = path.join(root, "dist");
  const modelPath = path.join(dist, "pink_bun_winefox_square_eyes");
  assert.notEqual(path.resolve(root, baseline), modelPath, "Pass a separate baseline model folder");

  const cases = shots.map(({ times, ...shot }) => ({
    ...shot,
    referenceView: "detail_front",
    frames: times.map((time) => ({ time })),
  }));
  const models = {
    before: readModel("school", baseline, "before"),
    after: readModel("school", modelPath, "after"),
  };
  const plan = {};
  for (const [edition, model] of Object.entries(models)) {
    plan[edition] = cases.map(({ id, clip, view, referenceView, frames }) => {
      assert(model.data.animations.animations[clip], `${edition}: missing ${clip}`);
      return {
        state: id,
        clip,
        view,
        referenceView,
        frames: frames.map((frame, index) => {
          const captureFrame = {
            time: frame.time,
            variables: clip === "jump" ? jumpVariables(frame.time) : {},
            file: `frames/${id}-${index + 1}-${edition}.png`,
          };
          frame[edition] = captureFrame;
          return captureFrame;
        }),
      };
    });
  }

  const folder = path.join(dist, "ysm-shirt-reviews");
  fs.mkdirSync(folder, { recursive: true });
  const output = fs.mkdtempSync(path.join(folder, `${stamp}-`));
  fs.mkdirSync(path.join(output, "frames"));
  await capture(output, plan, models);

  const manifest = {
    renderer: "Model Studio / Three.js",
    camera: "Matched chest framing across both model editions and action frames",
    models: Object.fromEntries(Object.entries(models).map(([edition, model]) => [edition, model.provenance])),
    cases,
  };
  fs.writeFileSync(path.join(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  fs.writeFileSync(path.join(output, "index.html"), page(cases));
  for (const file of ["LICENSE", "ATTRIBUTION.md"])
    fs.copyFileSync(path.join(root, file), path.join(output, file));
  fs.cpSync(output, path.join(dist, "viewer", "shirt-review"), { recursive: true });
  console.log(path.join(output, "index.html"));
  return output;
};
