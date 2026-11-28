const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const views = [
  ["right", "Side"],
  ["front3q", "Front Three-Quarter"],
];
const phases = [0, 0.2, 0.4, 0.6, 0.8];

function image(file, caption) {
  return `<figure><a href="${file}"><img src="${file}" alt="${caption}" width="512" height="512" loading="lazy"></a><figcaption>${caption}</figcaption></figure>`;
}

function preview({ id, label, description, shots }) {
  return `<article>
    <h3>${label}${id === "calm" ? ' <span class="active">Selected</span>' : ""}</h3>
    <p>${description}</p>
    ${shots.map(({ frames, label }) => image(frames[Math.floor(frames.length / 2)].file, label)).join("")}
  </article>`;
}

function page(options) {
  const glide = options.filter(({ id }) => id !== "creative");
  const creative = options.find(({ id }) => id === "creative");
  const creativePreview = creative
    ? `<section id="creative"><h2>Creative Flight</h2><div class="creative">${preview(creative)}</div></section>`
    : "";
  const sequences = options.map(({ label, shots }) =>
    `<details>
      <summary>${label} · 5 frames per angle</summary>
      ${shots.filter(({ frames }) => frames.length > 1).map((shot) => `<h3>${shot.label}</h3><div class="sequence">${shot.frames
        .map(({ file, time }) => image(file, `${time.toFixed(2)} s`))
        .join("")}</div>`).join("")}
    </details>`
  ).join("\n");

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Satou’s Aunt Flight Review</title>
<style>
*{box-sizing:border-box}
:root{color-scheme:dark;background:#191522;color:#faf2fb}
body{margin:0;font:16px/1.55 system-ui,sans-serif}
main{max-width:1240px;margin:auto;padding:32px clamp(12px,4vw,48px) 40px}
h1,h2,h3,p,figure{margin:0}
h1{font-size:clamp(1.8rem,5vw,3.4rem);line-height:1.1;margin-bottom:12px}
h2{font-size:1.3rem;margin-bottom:12px}
h3{font-size:1rem}
p,figcaption{color:#dfd1e3}
a{color:#ecd3fc}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
nav a{background:#31273a;padding:6px 12px;border-radius:7px}
section,footer{margin-top:32px}
.options{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,225px),1fr));gap:14px}
.sequence{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:9px;margin:6px 0 18px}
.creative{max-width:380px}
article,details{background:#252031;padding:13px;border-radius:9px}
article figure,details{margin-top:12px}
details h3,summary{margin:4px 0 10px}
summary{cursor:pointer}
img{display:block;width:100%;height:auto;border-radius:7px;background:#e6e0ed}
figcaption{margin-top:4px}
.active{color:#fbd6f4;font-weight:500}
</style></head><body><main>
<header><h1>Satou’s Aunt Flight Review</h1>
<p>Model Studio renders the YSM glide poses with matching camera angles and framing.</p>
<nav aria-label="Flight previews"><a href="#compare">Glide Comparison</a>${creative ? '<a href="#creative">Creative Flight</a>' : ""}<a href="#frames">Frame Sequences</a></nav></header>
<section id="compare"><h2>Glide Comparison</h2><div class="options">${glide.map(preview).join("\n")}</div></section>
${creativePreview}
<section id="frames"><h2>Frame Sequences</h2>${sequences}</section>
<footer><a href="manifest.json">Model and Render Data</a> · <a href="ATTRIBUTION.md">Attribution and License</a></footer>
</main></body></html>\n`;
}

module.exports = async function reviewAuntFlight({
  root, readModel, capture, stamp, baseline, alternatives = [],
}) {
  const dist = path.join(root, "dist");
  const modelPath = path.join(dist, "satou_aunt");
  const modelData = { aunt: readModel("aunt", modelPath, "aunt") };
  const clips = modelData.aunt.data.animations.animations;
  for (const { clip, animation } of alternatives) {
    assert(animation && !Object.hasOwn(clips, clip), `Invalid preview clip: ${clip}`);
    clips[clip] = animation;
  }
  const options = [{
    id: "calm",
    clip: "elytra_fly",
    model: "aunt",
    label: "Slipstream Glide",
    description: "Swept-back arms keep the shape of the braid and dress visible.",
  }, ...alternatives.map(({ clip, label, description }) => ({
    id: clip.replace(/^studio_flight_/, ""),
    clip, label, description, model: "aunt",
  }))];
  if (baseline) {
    modelData.before = readModel("aunt", baseline, "before");
    options.push({
      id: "before",
      clip: "elytra_fly",
      model: "before",
      label: "Original Glide",
      description: "The earlier clip in the same camera views.",
    });
  }
  if (clips.fly) options.push({
    id: "creative",
    clip: "fly",
    model: "aunt",
    label: "Gentle Hover",
    description: "A soft hover with a slight forward lean in Creative mode.",
  });

  const plan = Object.fromEntries(Object.keys(modelData).map((key) => [key, []]));
  for (const option of options) {
    const { id, clip, model } = option;
    assert(/^[\w-]+$/.test(id), `Invalid option name: ${id}`);
    const animation = modelData[model].data.animations.animations[clip];
    const duration = animation?.animation_length;
    assert(duration > 0, `Missing flight clip or duration: ${clip}`);
    const angles = id === "creative" ? views : [...views, ["top", "Top", [0.5]]];
    option.shots = angles.map(([view, label, samples = phases]) => ({
      state: id === "creative" ? "aunt-fly" : "aunt-flight",
      clip,
      view,
      label,
      referenceView: "full",
      frames: samples.map((phase, index) => ({
        file: `frames/${id}-${view}-${index + 1}.png`,
        time: +(duration * phase).toFixed(4),
        variables: { "query.is_on_ground": 0, "query.ground_speed": 10 },
      })),
    }));
    plan[model].push(...option.shots);
  }

  const parent = path.join(dist, "ysm-aunt-flight-reviews");
  fs.mkdirSync(parent, { recursive: true });
  const output = fs.mkdtempSync(path.join(parent, `${stamp}-`));
  fs.mkdirSync(path.join(output, "frames"));
  await capture(output, plan, modelData);

  const models = Object.fromEntries(Object.entries(modelData).map(([key, model]) => [key, model.provenance]));
  const previewAnimations = Object.fromEntries(alternatives.map(({ clip, animation }) => [clip, animation]));
  const manifest = { renderer: "Model Studio / Three.js", models, options, previewAnimations };
  fs.writeFileSync(path.join(output, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
  fs.writeFileSync(path.join(output, "index.html"), page(options));
  for (const file of ["LICENSE", "ATTRIBUTION.md"])
    fs.copyFileSync(path.join(modelPath, file), path.join(output, file));
  fs.cpSync(output, path.join(dist, "viewer", "aunt-flight-review"), { recursive: true });
  console.log(path.join(output, "index.html"));
  return output;
};
