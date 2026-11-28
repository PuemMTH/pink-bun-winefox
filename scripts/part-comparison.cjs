const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const sections = [
  ["lower", "L", "สะโพกและขา"],
  ["upper", "U", "ช่วงตัวและแขน"],
  ["head", "H", "หัวและใบหน้า"],
  ["motion", "M", "การเคลื่อนไหวรวม"],
];
const rank = { สูง: 0, กลาง: 1, ต่ำ: 2 };
const decisionCode = { ปรับ: "change", คงเดิม: "keep", ตรวจในเกม: "game" };
const outfitName = { school: "ชุดนักเรียน", white: "เชิ้ตขาว" };
const views = {
  front3q: "Front 3/4",
  back3q: "Back 3/4",
  front: "Front",
  back: "Back",
  left: "Left",
  right: "Right",
  top: "Top",
  bottom: "Bottom",
};
const html = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );

function renderCard(item) {
  const adjusted = item.decision === "ปรับ";
  const checked = adjusted
    ? item.done
      ? "ปรับแล้ว"
      : "รอตรวจเพิ่ม"
    : item.decision;
  return `<article class="card" data-group="${item.group}" data-decision="${decisionCode[item.decision]}" id="${item.id}"${adjusted ? "" : " hidden"}>
    <header class="card-title">
      <div><p class="meta">${item.id} · ${html(item.outfit)} · ${html(item.priority)}</p>
      <h2>${html(item.part)}</h2></div>
      <span class="status ${item.done ? "done" : ""}">${checked}</span>
    </header>
    <dl class="notes">
      <div><dt>สิ่งที่เห็น</dt><dd>${html(item.observation)}</dd></div>
      <div><dt>${adjusted ? "สิ่งที่ทำ" : "แนวทาง"}</dt><dd>${html(item.detail)}</dd></div>
      <div><dt>เหตุผล</dt><dd>${html(item.reason)}</dd></div>
      <div><dt>ตรวจซ้ำ</dt><dd>${html(item.verify)}</dd></div>
    </dl>
    ${item.pairs
      .map(
        (p) => `<div class="shot">
      <p class="meta">${outfitName[p.outfit]} · ${html(p.clip)} · ${html(views[p.view] || p.view)} · ${p.time} s</p>
      <div class="pair">${(adjusted
        ? [
            ["ก่อนแก้", p.before],
            ["หลังแก้", p.after],
          ]
        : [["ภาพปัจจุบัน", p.after]]
      )
        .map(
          ([label, frame]) =>
            `<figure><figcaption>${label}</figcaption>
        <a href="${frame.file}" target="_blank" rel="noopener"><img loading="lazy" src="${frame.file}" alt="${label} ${html(item.part)}"></a></figure>`,
        )
        .join("")}</div>
    </div>`,
      )
      .join("")}
    <label class="check"><input type="checkbox" data-id="${item.id}"> ตรวจข้อนี้แล้ว</label>
  </article>`;
}

function page(items, stamp) {
  const done = items.filter((item) => item.done).length;
  const planned = items.filter((item) => item.decision === "ปรับ").length;
  return `<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ตรวจโมเดล Satou YSM</title>
<style>
:root{color-scheme:dark;--page:#16131a;--panel:#211b26;--line:#4a394d;--txt:#f4edf5;--dim:#cfbbd4;--pink:#ffc9e0;--green:#bce7d0}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--txt);font:16px/1.6 system-ui,"Leelawadee UI",sans-serif}
main{max-width:1100px;margin:auto;padding:28px clamp(16px,4vw,44px) 60px}h1,h2,p,dl,dd,figure{margin:0}h1{font-size:clamp(2rem,6vw,3rem);line-height:1.12}
.intro{padding:12px 0 24px}.intro p{margin-top:10px;color:var(--dim)}a{color:var(--pink)}button,input,select{font:inherit}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px;position:sticky;top:0;background:var(--page);border-block:1px solid var(--line);padding:12px 0;z-index:1}
button,select{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--txt);padding:6px 11px;cursor:pointer}
button[aria-pressed="true"]{border-color:var(--pink);color:var(--pink)}.check{display:flex;gap:6px;align-items:center;color:var(--dim);font-size:.9rem}
input[type=checkbox]{accent-color:#f4abcd;width:1.05rem;height:1.05rem}#summary{color:var(--dim);margin-left:auto;font-size:.88rem}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:clamp(12px,2vw,24px);margin-top:18px;scroll-margin-top:110px}
.card-title{display:flex;align-items:start;justify-content:space-between;gap:10px;margin-bottom:12px}.card-title h2{font-size:1.35rem}
.meta{color:var(--dim);font-size:.86rem}.status{color:#ffe1af;border:1px solid var(--line);padding:2px 8px;border-radius:6px;font-size:.86rem;white-space:nowrap}
.status.done{color:var(--green)}.notes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 18px;font-size:.92rem}
dt{color:var(--pink);font-weight:650}dd{color:var(--txt)}.shot{margin-top:14px;border-top:1px solid var(--line);padding-top:9px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:5px}figure{min-width:0}figcaption{font-weight:650;margin-bottom:4px}
img{display:block;width:100%;height:auto;max-width:512px;border-radius:6px;background:#e6e0ed}.card>.check{margin-top:12px}
footer{color:var(--dim);padding-top:24px}.empty{padding-top:20px}[hidden]{display:none!important}
@media(max-width:600px){.notes{grid-template-columns:1fr}#summary{width:100%;margin-left:0}.card-title h2{font-size:1.15rem}}
</style>
</head>
<body><main>
<header class="intro"><h1>ตรวจโมเดล Satou YSM</h1>
<p>ปรับแล้ว ${done} จาก ${planned} ข้อที่เสนอแก้ ภาพคู่จาก Model Studio ใช้ท่า เวลา และกล้องเดียวกัน</p>
<p>ใช้ภาพหลังแก้ตรวจรูปทรง แล้วติ๊กข้อที่ดูแล้ว ผลการผสมท่าและการถือไอเทมใน Minecraft ยังรอตรวจ</p></header>
<div class="controls" aria-label="ตัวกรองเช็กลิสต์">
  <button data-filter="all" aria-pressed="true">ทุกส่วน</button>
  ${sections.map(([key, , label]) => `<button data-filter="${key}" aria-pressed="false">${label}</button>`).join("")}
  <select id="decision" aria-label="ผลประเมิน"><option value="change">ข้อที่เสนอแก้</option><option value="keep">คงเดิม</option><option value="game">ตรวจในเกม</option><option value="all">ทุกผลประเมิน</option></select>
  <label class="check"><input id="pending" type="checkbox"> เฉพาะยังไม่ตรวจ</label>
  <span id="summary" aria-live="polite"></span>
</div>
${items.map(renderCard).join("\n")}
<p id="empty" class="empty" hidden>ไม่มีข้อที่ตรงกับตัวกรอง</p>
<footer><a href="manifest.json">ข้อมูลเฟรมและไฟล์โมเดล</a> · <a href="ATTRIBUTION.md">เครดิต</a></footer>
</main><script>
const key = ${JSON.stringify("satou-part-review-" + stamp)};
const cards = [...document.querySelectorAll(".card")];
let reviewed;
try { reviewed = new Set(JSON.parse(localStorage.getItem(key) || "[]")); } catch { reviewed = new Set(); }
let group = "all";
const pending = document.getElementById("pending");
const decision = document.getElementById("decision");
const summary = document.getElementById("summary");
function show() {
  let visible = 0;
  for (const card of cards) {
    card.hidden = (group !== "all" && card.dataset.group !== group) ||
      (decision.value !== "all" && decision.value !== card.dataset.decision) ||
      (pending.checked && reviewed.has(card.id));
    if (!card.hidden) visible++;
  }
  summary.textContent = visible + " ข้อที่แสดง · ตรวจแล้ว " + reviewed.size + "/" + cards.length;
  document.getElementById("empty").hidden = visible !== 0;
}
for (const input of document.querySelectorAll("[data-id]")) {
  input.checked = reviewed.has(input.dataset.id);
  input.onchange = () => {
    if (input.checked) reviewed.add(input.dataset.id); else reviewed.delete(input.dataset.id);
    try { localStorage.setItem(key, JSON.stringify([...reviewed])); } catch {}
    show();
  };
}
const buttons = [...document.querySelectorAll("[data-filter]")];
for (const button of buttons) button.onclick = () => {
  group = button.dataset.filter;
  for (const b of buttons) b.setAttribute("aria-pressed", String(b === button));
  show();
};
pending.onchange = show;
decision.onchange = show;
show();
</script></body></html>`;
}

module.exports = async function compareParts({
  root,
  baseline,
  readModel,
  capture,
  stamp,
}) {
  const dist = path.join(root, "dist");
  const beforeDir = path.resolve(root, baseline);
  const read = (file) =>
    JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
  const previous = read(path.join(beforeDir, "manifest.json"));
  const lookup = new Map(
    previous.cases.flatMap((job) =>
      job.frames.map((frame) => [frame.file, { job, frame }]),
    ),
  );
  const items = [];
  for (const [group, prefix] of sections) {
    const rows = read(path.join(dist, `part-review-${group}.json`)).sort(
      (a, b) => rank[a.priority] - rank[b.priority],
    );
    const fixes = new Map(
      (group === "motion"
        ? []
        : read(path.join(dist, `part-fixes-${group}.json`))
      ).map((row) => [row.part, row]),
    );
    for (const [index, row] of rows.entries()) {
      const fix =
        row.decision === "ปรับ"
          ? fixes.get(row.part)
          : { done: false, detail: row.change, verify: row.check };
      assert(
        typeof fix?.done === "boolean" && fix.detail && fix.verify,
        row.part,
      );
      items.push({
        ...row,
        ...fix,
        group,
        id: `${prefix}-${String(index + 1).padStart(2, "0")}`,
        pairs: [],
      });
    }
  }
  const plan = {};
  const modelData = {};
  for (const outfit of Object.keys(outfitName)) {
    const before = previous.models[outfit];
    for (const edition of ["before", "after"]) {
      const key = edition + "-" + outfit;
      plan[key] = [];
      const directory =
        edition === "before"
          ? path.join(beforeDir, path.basename(before.directory))
          : undefined;
      const model = readModel(outfit, directory, key);
      if (edition === "before")
        assert.deepEqual(model.provenance.sha256, before.sha256, key);
      modelData[key] = model;
    }
  }
  for (const item of items)
    for (const [i, original] of item.frames.entries()) {
      const shot = lookup.get(original);
      assert(shot, original);
      const { job, frame } = shot;
      const pair = {
        clip: job.clip,
        view: job.view,
        outfit: job.outfit,
        time: frame.time,
        original,
      };
      for (const edition of item.decision === "ปรับ"
        ? ["before", "after"]
        : ["after"]) {
        const key = edition + "-" + job.outfit;
        assert(modelData[key].data.animations.animations[job.clip], job.clip);
        const image = {
          time: frame.time,
          variables: frame.variables,
          file: `frames/${item.id}-${i + 1}-${edition}.png`,
        };
        pair[edition] = image;
        plan[key].push({ ...job, frames: [image] });
      }
      item.pairs.push(pair);
    }
  const folder = path.join(dist, "ysm-part-reviews");
  fs.mkdirSync(folder, { recursive: true });
  const output = fs.mkdtempSync(path.join(folder, stamp + "-"));
  fs.mkdirSync(path.join(output, "frames"));
  console.log("Rendering matched before and after frames: " + output);
  await capture(output, plan, modelData);
  const result = {
    renderer: "Model Studio / Three.js",
    camera: "Shared framing per clip and view",
    changes: items,
    models: Object.fromEntries(
      Object.entries(modelData).map(([id, m]) => [id, m.provenance]),
    ),
  };
  fs.writeFileSync(
    path.join(output, "manifest.json"),
    JSON.stringify(result, null, 2) + "\n",
  );
  fs.writeFileSync(path.join(output, "index.html"), page(items, stamp));
  for (const file of ["LICENSE", "ATTRIBUTION.md"])
    fs.copyFileSync(path.join(root, file), path.join(output, file));
  console.log(path.join(output, "index.html"));
};
