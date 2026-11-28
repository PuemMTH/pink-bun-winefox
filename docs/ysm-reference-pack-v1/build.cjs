// Regenerate the portable index, manifest and manual checklist using Node stdlib.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const dir = __dirname;
const plan = JSON.parse(fs.readFileSync(path.join(dir, "plan.json"), "utf8"));
const draft = process.argv.includes("--draft");
const categories = {
  turnaround: "ชุด · หลายมุม",
  faces: "สีหน้า",
  details: "รายละเอียดผ้า/ผม",
  main: "ท่าหลัก YSM",
  extra: "ท่า extra",
  photo: "โพสถ่ายรูป",
  overview: "ภาพรวมเดิม",
};
const outfits = { school: "ชุดนักเรียน", white: "เชิ้ตขาว" };
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const write = (name, data) => fs.writeFileSync(path.join(dir, name), data);
const sheets = plan.sheets.map((sheet) => {
  const file = path.join(dir, sheet.file);
  if (!fs.existsSync(file)) {
    if (!draft) throw Error("Missing image: " + sheet.file);
    return { ...sheet, ready: false };
  }
  const bytes = fs.readFileSync(file);
  assert.equal(
    bytes.subarray(0, 8).toString("hex"),
    "89504e470d0a1a0a",
    sheet.file + " must be PNG",
  );
  const { prompt, refs, ...entry } = sheet;
  return {
    ...entry,
    ready: true,
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    bytes: bytes.length,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
  };
});
assert.equal(new Set(sheets.map((s) => s.key)).size, sheets.length);
let catalog;
const model = path.resolve(dir, "../../dist/pink_bun_winefox");
if (fs.existsSync(path.join(model, "ysm.json"))) {
  const meta = JSON.parse(fs.readFileSync(path.join(model, "ysm.json")));
  catalog = {
    model: meta.metadata.name,
    extraLabels: meta.properties.extra_animation,
    groups: {},
  };
  for (const [group, file] of Object.entries(meta.files.player.animation)) {
    const animations =
      JSON.parse(fs.readFileSync(path.join(model, file))).animations || {};
    catalog.groups[group] = Object.entries(animations)
      .filter(([name]) => !/parallel|——|^empty$|^gui$|\$/.test(name))
      .map(([id, a]) => ({
        id,
        duration: a.animation_length ?? null,
        loop: a.loop ?? false,
      }));
  }
  write("clip-catalog.json", JSON.stringify(catalog, null, 2) + "\n");
} else
  catalog = JSON.parse(fs.readFileSync(path.join(dir, "clip-catalog.json")));
for (const outfit of Object.keys(outfits)) {
  for (const id of catalog.groups.main.map((c) => c.id))
    assert(
      sheets.some(
        (s) =>
          s.outfit === outfit &&
          s.category === "main" &&
          s.panels.some((p) => p.id === id),
      ),
      "Missing main state " + outfit + "/" + id,
    );
  for (const id of catalog.groups.extra.map((c) => c.id))
    assert(
      sheets.some(
        (s) =>
          s.outfit === outfit &&
          s.category === "extra" &&
          s.panels.some((p) => p.id === id),
      ),
      "Missing extra state " + outfit + "/" + id,
    );
  for (const [id] of plan.faces)
    assert(
      sheets.some(
        (s) =>
          s.outfit === outfit &&
          s.category === "faces" &&
          s.panels.some((p) => p.id === id),
      ),
      "Missing face " + outfit + "/" + id,
    );
  for (const [id] of plan.photo)
    assert(
      sheets.some(
        (s) =>
          s.outfit === outfit &&
          s.category === "photo" &&
          s.panels.some((p) => p.id === id),
      ),
      "Missing photo pose " + outfit + "/" + id,
    );
}
const summary = {
  sheets: sheets.length,
  ready: sheets.filter((s) => s.ready).length,
  panels: sheets.reduce((n, s) => n + s.panels.length, 0),
  mainStates: catalog.groups.main.length,
  extraStates: catalog.groups.extra.length,
  photoStates: plan.photo.length,
  faceStates: plan.faces.length,
  outfits: 2,
};
write(
  "manifest.json",
  JSON.stringify(
    {
      version: 1,
      kind: "AI concept references; not exact rig renders",
      summary,
      sheets,
    },
    null,
    2,
  ) + "\n",
);
const rows = [
  [
    "case_id",
    "outfit",
    "category",
    "state",
    "view",
    "reference_image",
    "status",
    "actual_screenshot",
    "notes",
  ],
];
for (const s of sheets.filter((s) => s.category !== "overview"))
  for (const [i, p] of s.panels.entries())
    rows.push([
      s.key + "-" + (i + 1),
      s.outfit,
      s.category,
      p.id,
      p.view || "detail",
      s.file,
      "pending",
      "",
      "",
    ]);
const csvValue = (x) => '"' + String(x).replaceAll('"', '""') + '"';
write(
  "checklist.csv",
  "\ufeff" +
    rows.map((row) => row.map(csvValue).join(",")).join("\r\n") +
    "\r\n",
);
write(
  "PROMPTS.md",
  "# Image generation prompts\n\nTool: built-in image_gen. Reference paths below are relative to this pack.\n\n" +
    plan.sheets
      .filter((s) => s.generated)
      .map(
        (s) =>
          "## " +
          s.key +
          "\n\nReferences: " +
          s.refs.join(", ") +
          "\n\n" +
          s.prompt +
          "\n",
      )
      .join("\n"),
);
const cards = sheets
  .map(
    (s) =>
      `<article data-outfit="${s.outfit}" data-category="${s.category}" data-search="${esc(s.title + " " + s.panels.map((p) => p.id).join(" "))}" data-key="${s.key}"><a href="${s.file}" target="_blank" rel="noopener">${s.ready ? `<img src="${s.file}" loading="lazy" alt="${esc(s.title)}">` : '<div class="placeholder">กำลังสร้างภาพ</div>'}</a><div class="card-body"><small>${outfits[s.outfit]} · ${categories[s.category]}</small><h2><a href="${s.file}" target="_blank">${esc(s.title)}</a></h2><p>${esc(
        s.panels
          .map((p) => p.id)
          .filter((v, i, a) => a.indexOf(v) === i)
          .join(" · "),
      )}</p><label><input type="checkbox" data-reviewed="${s.key}"> ตรวจชีตนี้แล้ว</label></div></article>`,
  )
  .join("\n");
write(
  "index.html",
  `<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Satou · YSM reference pack</title><style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;color:#f4edf6;background:#16131c}*{box-sizing:border-box}body{margin:0}header,main{max-width:1600px;margin:auto;padding:28px}header{padding-bottom:12px}h1{font-size:clamp(26px,4vw,42px);margin:8px 0}p{line-height:1.7}header p{color:#bcafc7;max-width:900px}a{color:#f4bddb}nav{display:flex;gap:16px;flex-wrap:wrap;margin:18px 0}.filters{display:flex;gap:12px;align-items:end;flex-wrap:wrap;position:sticky;top:0;background:#211b29f5;padding:16px;z-index:2;border:1px solid #594058;border-radius:10px}.filters label{font-size:14px;display:grid;gap:5px}.filters .unreviewed{display:flex;align-items:center;padding-bottom:8px}input,select{font:inherit;color:inherit;background:#302738;border:1px solid #69516b;border-radius:6px;padding:9px}input[type=checkbox]{accent-color:#f2a9d0}input[type=search]{min-width:210px}#progress{color:#d0b9cc;font-size:14px}#gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));gap:20px;margin-top:22px}article{background:#241d2d;border:1px solid #49394f;border-radius:12px;overflow:hidden}article[hidden]{display:none}article img{display:block;width:100%;height:auto;aspect-ratio:1.5;object-fit:contain;background:#c7bacf}.card-body{padding:18px}small{color:#d3adcb;font-size:13px}h2{font-size:18px;margin:8px 0}article p{font-size:13px;color:#baadca;overflow-wrap:anywhere}article label{font-size:14px}.placeholder{display:grid;place-items:center;height:220px;background:#35283e;color:#be99ba}#empty{display:none;color:#cab8d1}@media print{.filters,nav,input{display:none}article{break-inside:avoid}body{background:white;color:black}a{color:black}}
</style><header><small>ARTIFACT PACK · VERSION 1</small><h1>Satou · YSM reference pack</h1><p>2 ชุด · ${summary.sheets} ชีต · ${summary.panels} ภาพย่อย<br>ท่าหลัก ${summary.mainStates} คลิป + extra ${summary.extraStates} สถานะ + โพสถ่ายรูป ${summary.photoStates} แบบ ครบทั้งสองชุด และตารางสีหน้า ${summary.faceStates} แบบต่อชุด</p><p>ภาพคอนเซปต์ AI สำหรับเทียบรูปลักษณ์ สีหน้า และทรงเสื้อผ้า การเคลื่อนไหวและจุดทะลุต้องตรวจด้วยโมเดลจริงในเกมด้วย หมวดภาพรวมเดิมมีรายละเอียดที่อาจต่างกัน ให้ใช้ตารางสีหน้าและชีตรายละเอียดเป็นเป้าหมายแต่ละหมวด</p><nav><a href="CHECKLIST.md">วิธีตรวจโมเดล</a><a href="checklist.csv" download>ดาวน์โหลดตารางเช็ก CSV</a><a href="COVERAGE.md">ขอบเขตคลิป</a><a href="PROMPTS.md">พรอมป์ต image_gen</a><a href="manifest.json">Manifest / SHA-256</a></nav></header><main><div class="filters"><label>ชุด<select id="outfit"><option value="all">ทุกชุด</option><option value="school">ชุดนักเรียน</option><option value="white">เชิ้ตขาว</option></select></label><label>หมวด<select id="category"><option value="all">ทุกหมวด</option>${Object.entries(
    categories,
  )
    .map(([key, label]) => '<option value="' + key + '">' + label + "</option>")
    .join(
      "",
    )}</select></label><label>ค้นหาท่า<input type="search" id="search" placeholder="run, sit, spiral, extra5…"></label><label class="unreviewed"><input type="checkbox" id="only-pending">เฉพาะยังไม่ตรวจ</label><span id="progress"></span></div><p id="empty">ไม่พบชีตตามตัวกรองนี้</p><div id="gallery">${cards}</div></main><script>
const cards=[...document.querySelectorAll('article')],key='satou-reference-v1-reviewed';let reviewed={};try{reviewed=JSON.parse(localStorage.getItem(key)||'{}')}catch{};
function filter(){let visible=0;for(const card of cards){const show=(outfit.value==='all'||card.dataset.outfit===outfit.value)&&(category.value==='all'||card.dataset.category===category.value)&&card.dataset.search.toLowerCase().includes(search.value.toLowerCase())&&(!pending.checked||!reviewed[card.dataset.key]);card.hidden=!show;if(show)visible++}progress.textContent=visible+' ชีตที่แสดง · ตรวจแล้ว '+Object.values(reviewed).filter(Boolean).length+'/'+cards.length;document.getElementById('empty').style.display=visible?'none':'block'}
const outfit=document.getElementById('outfit'),category=document.getElementById('category'),search=document.getElementById('search'),pending=document.getElementById('only-pending'),progress=document.getElementById('progress');
for(const box of document.querySelectorAll('[data-reviewed]')){box.checked=!!reviewed[box.dataset.reviewed];box.onchange=()=>{reviewed[box.dataset.reviewed]=box.checked;try{localStorage.setItem(key,JSON.stringify(reviewed))}catch{}filter()}}for(const control of [outfit,category,search,pending])control.addEventListener('input',filter);filter();
</script></html>`,
);
const missing = sheets.filter((s) => !s.ready).map((s) => s.key);
write(
  "COVERAGE.md",
  "# Coverage\n\n" +
    JSON.stringify(summary, null, 2) +
    "\n\n## Native main clips\n\n" +
    catalog.groups.main
      .map((c) => "- `" + c.id + "` — school + white")
      .join("\n") +
    "\n\n## Extra clips\n\n" +
    catalog.groups.extra
      .map(
        (c) =>
          "- `" +
          c.id +
          "` " +
          (catalog.extraLabels[c.id] || "") +
          " — school + white",
      )
      .join("\n") +
    "\n\nextra0 is an accessory-toggle/reset event; its neutral illustration does not define new headwear. Static nod/shake/dance images are characteristic phases, not animation-cycle proofs.\n\n## Optional integration clips\n\nThese are inventoried but require their integration runtime and are not given independent image targets in this base-character pack:\n\n" +
    Object.entries(catalog.groups)
      .filter(([g]) => !["main", "extra"].includes(g))
      .map(
        ([g, clips]) =>
          "### " + g + "\n\n" + clips.map((c) => "- `" + c.id + "`").join("\n"),
      )
      .join("\n\n") +
    "\n\n## Draft missing images\n\n" +
    (missing.join("\n") || "None") +
    "\n",
);
console.log(
  JSON.stringify({ ...summary, checklistCases: rows.length - 1, missing }),
);
