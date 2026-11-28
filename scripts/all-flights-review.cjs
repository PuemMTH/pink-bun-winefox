const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const models = [
  {
    id: "school",
    directory: "pink_bun_winefox_square_eyes",
    name: "Satou Matsuzaka",
    outfit: "School uniform",
    glide: "Focused Glide",
    hover: "Steady Hover",
  },
  {
    id: "white",
    directory: "pink_bun_winefox_white_square_eyes",
    name: "Satou Matsuzaka",
    outfit: "White shirt",
    glide: "Open-Arm Drift",
    hover: "Soft Float",
  },
  {
    id: "aunt",
    directory: "satou_aunt",
    name: "Satou’s Aunt",
    outfit: "Pink dress",
    glide: "Slipstream Glide",
    hover: "Gentle Hover",
  },
];
const modes = [
  { id: "elytra", clip: "elytra_fly", label: "Elytra", speed: 10, pose: "glide" },
  { id: "creative", clip: "fly", label: "Creative flight", speed: 3, pose: "hover" },
];
const phases = [0, 0.2, 0.4, 0.6, 0.8];
const angles = [
  { view: "front3q", label: "Front three-quarter", phases: [0.4] },
  { view: "left", label: "Left side", phases },
  { view: "right", label: "Right side", phases },
  { view: "top", label: "Top", phases: [0.4] },
  { view: "bottom", label: "Underside", phases: [0.4] },
];
const checks = [
  {
    id: "braid-creative",
    label: "Braid clearance in Creative flight",
    detail: "The braid follows the turn and stays clear of the shoulder and dress.",
    clip: "fly",
    views: ["front3q"],
    times: [0.16, 0.28, 0.4, 0.52, 0.64],
    variables: { "query.is_on_ground": 0, "query.ground_speed": 8, "ysm.head_yaw": 32, "ysm.head_pitch": 35 },
  },
  {
    id: "braid-elytra",
    label: "Braid clearance during Elytra glide",
    detail: "The braid compensates for head aim as it trails behind the head.",
    clip: "elytra_fly",
    views: ["right"],
    times: [0.06, 0.18, 0.3, 0.42, 0.54],
    variables: { "query.is_on_ground": 0, "query.ground_speed": 8, "ysm.head_yaw": -50, "ysm.head_pitch": -35 },
  },
  {
    id: "dress-heel",
    label: "Dress clearance during crouch walk",
    detail: "The dress clears the rising heel at the rear and the forward knee.",
    clip: "sneak",
    views: ["back", "back3q", "right"],
    referenceView: "detail_hem",
    times: [0.09, 0.13, 0.17, 0.21, 0.25, 1.66],
    variables: { "query.ground_speed": 1.295, "query.is_sneaking": 1, "query.is_moving": 1 },
  },
];
const editions = ["before", "after"];

function pair(frame, label) {
  return `<div class="pair">${editions.map((edition) => {
    const caption = `${edition === "before" ? "Before" : "After"} · ${frame[edition].time.toFixed(3)} s`;
    const { file } = frame[edition];
    return `<figure><a href="${file}"><img src="${file}" alt="${label}, ${caption}" width="512" height="512" loading="lazy"></a><figcaption>${caption}</figcaption></figure>`;
  }).join("")}</div>`;
}

function flightCard(model, mode) {
  const title = model[mode.pose];
  const label = `${model.name} · ${model.outfit} · ${title}`;
  const [hero, ...views] = mode.angles;
  return `<article>
    <h3>${mode.label} · ${title}</h3>
    ${pair(hero.frames[0], `${label}, ${hero.label}`)}
    ${views.map((angle) => `<details>
      <summary>${angle.label} · ${angle.frames.length} ${angle.frames.length === 1 ? "frame" : "frames"}</summary>
      ${angle.frames.map((frame) => `<div class="phase">
        ${angle.frames.length > 1 ? `<h4>${Math.round(frame.phase * 100)}% of the loop</h4>` : ""}
        ${pair(frame, `${label}, ${angle.label}`)}
      </div>`).join("")}
    </details>`).join("")}
  </article>`;
}

function checkCard(check) {
  return `<article id="${check.id}">
    <h3>${check.label}</h3>
    <p>${check.detail}</p>
    ${check.angles.map(({ view, frames }, index) => `<div class="phase">
      ${index === 0 ? pair(frames[2], `${check.label}, ${view}`) : ""}
      <details><summary>${view === "back3q" ? "Rear three-quarter" : view === "front3q" ? "Front three-quarter" : view[0].toUpperCase() + view.slice(1)} · ${frames.length} frames</summary>
        ${frames.map((frame) => `<div class="phase">${pair(frame, `${check.label}, ${view}`)}</div>`).join("")}
      </details>
    </div>`).join("")}
  </article>`;
}

function page(models, checks, auntOptions) {
  return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YSM Motion Review</title>
<style>
*{box-sizing:border-box}
:root{color-scheme:dark;background:#181522;color:#faf3fb}
body{margin:0;font:16px/1.55 system-ui,sans-serif}
main{max-width:1190px;margin:auto;padding:32px clamp(12px,4vw,44px) 40px}
h1,h2,h3,h4,p,figure{margin:0}
h1{font-size:clamp(1.8rem,5vw,3.4rem);line-height:1.12;margin-bottom:12px}
h2{font-size:clamp(1.3rem,3vw,1.65rem);margin-bottom:12px}
h3,h4{font-size:1rem;margin-bottom:8px}
p,figcaption{color:#dccfe3}
a{color:#f2cef7}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:15px}
nav a{background:#302638;padding:6px 12px;border-radius:6px}
section,footer{margin-top:30px}
.modes{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,350px),1fr))}
article{min-width:0;background:#262031;border-radius:9px;padding:13px}
.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
img{display:block;width:100%;height:auto;border-radius:7px;background:#e6e0ed}
figcaption{margin-top:4px;font-size:.88rem}
details{margin-top:14px}
summary{cursor:pointer}
.phase{margin-top:14px}
.credits{margin-top:8px;font-size:.92rem}
</style></head><body><main>
<header><h1>YSM Motion Review</h1>
<p>Compare the installed baseline with the revised YSM packages. Model Studio renders each pair with a shared camera. The flight overview matches the loop phase, and the fix comparisons match the pose inputs and time.</p>
<nav aria-label="Review sections"><a href="#fixes">Aunt’s fixes</a>${models.map(({ id, name, outfit }) => `<a href="#${id}">${id === "aunt" ? name : outfit}</a>`).join("")}</nav></header>
<section id="fixes"><h2>Satou’s Aunt · Before and after</h2>
<div class="modes">${checks.map(checkCard).join("")}</div></section>
${models.map((model) => `<section id="${model.id}"><h2>${model.name} · ${model.outfit}</h2>
<div class="modes">${model.modes.map((mode) => flightCard(model, mode)).join("")}</div>
<p class="credits"><a href="credits/${model.id}.md">Model credits</a>${model.id === "aunt" && auntOptions ? ` · <a href="${auntOptions}">Aunt’s alternate glide poses</a>` : ""}</p></section>`).join("\n")}
<footer><a href="manifest.json">Render provenance</a> · <a href="LICENSE">License</a></footer>
</main></body></html>\n`;
}

module.exports = async function reviewAllFlights({ root, readModel, capture, stamp, baseline }) {
  assert(baseline, "Pass the folder containing the three before models");
  const dist = path.join(root, "dist");
  const beforeRoot = path.resolve(root, baseline);
  assert.notEqual(beforeRoot, dist, "Pass a separate baseline folder");
  const plan = {};
  const modelData = {};
  const review = models.map((model) => ({
    ...model,
    modes: modes.map((mode) => ({
      ...mode,
      angles: angles.map(({ phases, ...angle }) => ({
        ...angle,
        frames: phases.map((phase) => ({ phase })),
      })),
    })),
  }));

  for (const model of review) {
    for (const edition of editions) {
      const modelRoot = edition === "before" ? beforeRoot : dist;
      const folder = path.join(modelRoot, model.directory);
      const key = `${model.id}-${edition}`;
      modelData[key] = readModel(model.id, folder, key);
      const { animations } = modelData[key].data.animations;
      plan[key] = model.modes.flatMap(({ id, clip, speed, angles }) => {
        const duration = animations[clip]?.animation_length;
        assert(duration > 0, `Missing flight clip or duration in ${key}: ${clip}`);
        return angles.map(({ view, frames }) => ({
          state: `${model.id}-${id}`,
          clip,
          view,
          referenceView: "full",
          frames: frames.map((frame, index) => {
            const shot = {
              file: `frames/${model.id}-${id}-${view}-${index + 1}-${edition}.png`,
              time: +(duration * frame.phase).toFixed(4),
              variables: { "query.is_on_ground": 0, "query.ground_speed": speed },
            };
            frame[edition] = shot;
            return shot;
          }),
        }));
      });
    }
  }

  const fixReview = checks.map(({ views, times, ...check }) => ({
    ...check,
    angles: views.map((view) => ({
      view,
      frames: times.map((time) => ({ time })),
    })),
  }));
  for (const edition of editions) {
    for (const check of fixReview) {
      for (const angle of check.angles) {
        plan[`aunt-${edition}`].push({
          state: check.id,
          clip: check.clip,
          view: angle.view,
          referenceView: check.referenceView || "full",
          frames: angle.frames.map((frame, index) => {
            const shot = {
              file: `frames/${check.id}-${angle.view}-${index + 1}-${edition}.png`,
              time: frame.time,
              variables: check.variables,
            };
            frame[edition] = shot;
            return shot;
          }),
        });
      }
    }
  }

  const parent = path.join(dist, "ysm-flight-reviews");
  fs.mkdirSync(parent, { recursive: true });
  const output = fs.mkdtempSync(path.join(parent, `${stamp}-`));
  const stable = path.join(dist, "viewer", "flight-review");
  fs.mkdirSync(path.join(output, "frames"));
  await capture(output, plan, modelData);

  const manifest = {
    renderer: "Model Studio / Three.js",
    models: Object.fromEntries(Object.entries(modelData).map(([key, model]) => [key, model.provenance])),
    review,
    fixes: fixReview,
  };
  fs.writeFileSync(path.join(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  fs.mkdirSync(path.join(output, "credits"));
  for (const { id, directory } of models)
    fs.copyFileSync(path.join(dist, directory, "ATTRIBUTION.md"), path.join(output, "credits", `${id}.md`));
  fs.copyFileSync(path.join(dist, models[0].directory, "LICENSE"), path.join(output, "LICENSE"));

  const options = path.join(dist, "viewer", "aunt-flight-review", "index.html");
  const optionLink = (folder) => fs.existsSync(options) ? path.relative(folder, options).split(path.sep).join("/") : "";
  fs.writeFileSync(path.join(output, "index.html"), page(review, fixReview, optionLink(output)));
  fs.cpSync(output, stable, { recursive: true });
  fs.writeFileSync(path.join(stable, "index.html"), page(review, fixReview, optionLink(stable)));
  console.log(path.join(output, "index.html"));
  return output;
};
