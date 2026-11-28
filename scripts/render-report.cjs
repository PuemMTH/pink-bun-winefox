const fs = require("node:fs");
const path = require("node:path");

const quote = (value) => '"' + String(value).replaceAll('"', '""') + '"';
const html = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const outfitNames = { school: "ชุดนักเรียน", white: "เชิ้ตขาว" };
const actionNames = {
  climb: "คลานใต้ประตูกล",
  climbing: "ค้างท่าคลาน",
  sneak: "เดินย่อ",
  sneaking: "ย่ออยู่กับที่",
  extra0: "สลับริบบิ้น",
};
const primary = (job) => job.frames.find((frame) => frame.primary);

function frameCard(frame) {
  return `<a href="${frame.file}">
    <img src="${frame.file}" alt="ภาพเรนเดอร์ที่ ${frame.time} วินาที" loading="lazy">
    <span>${frame.time} s</span>
  </a>`;
}

function renderCard(job) {
  const additional = job.frames.filter((frame) => !frame.primary);
  return `<article id="${html(job.id)}">
    <h3>${job.panel}. ${html(actionNames[job.state] || job.state)}</h3>
    <p>${html(job.view)} · ${html(job.clip)}</p>
    ${frameCard(primary(job))}
    ${
      additional.length
        ? `<details><summary>ดูอีก ${additional.length} เฟรม</summary>
      <div class="samples">${additional.map(frameCard).join("")}</div></details>`
        : ""
    }
  </article>`;
}

function writeReport(output, reference, sheets, cases, models, rendererSha256) {
  const write = (file, data) => fs.writeFileSync(path.join(output, file), data);
  fs.mkdirSync(path.join(output, "images"), { recursive: true });
  for (const sheet of sheets) {
    fs.copyFileSync(
      path.join(reference, sheet.file),
      path.join(output, sheet.file),
    );
  }
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
  for (const job of cases) {
    rows.push([
      job.id,
      job.outfit,
      job.category,
      job.state,
      job.referenceView,
      job.reference,
      "pending",
      primary(job).file,
      `Model Studio, ${job.view} at ${primary(job).time} s`,
    ]);
  }
  write(
    "checklist.csv",
    "\ufeff" +
      rows.map((row) => row.map(quote).join(",")).join("\r\n") +
      "\r\n",
  );
  const frames = cases.reduce((total, job) => total + job.frames.length, 0);
  write(
    "manifest.json",
    JSON.stringify(
      {
        renderer: "Model Studio / Three.js",
        created: new Date().toISOString(),
        dimensions: [512, 512],
        captureSettings: {
          background: "light",
          grid: false,
          blink: false,
          camera: "Matching cases share framing across outfits and phases",
        },
        models,
        rendererSha256,
        frames,
        cases,
      },
      null,
      2,
    ) + "\n",
  );
  for (const file of ["LICENSE", "ATTRIBUTION.md"])
    fs.copyFileSync(path.join(reference, file), path.join(output, file));

  const sections = sheets.map(
    (sheet) => `<section id="${html(sheet.key)}">
    <h2>${html(sheet.title)}</h2>
    <details><summary>เปิดชีตคอนเซปต์สำหรับเทียบ</summary>
      <a href="${sheet.file}"><img class="reference" src="${sheet.file}" alt="${html(sheet.title)}" loading="lazy"></a>
    </details>
    <div class="grid">${cases
      .filter((job) => job.reference === sheet.file)
      .map(renderCard)
      .join("")}</div>
  </section>`,
  );
  const sheetLinks = (outfit) =>
    sheets
      .filter((sheet) => sheet.outfit === outfit)
      .map((sheet) => `<a href="#${html(sheet.key)}">${html(sheet.title)}</a>`)
      .join("");
  write(
    "index.html",
    `<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Satou · ภาพเรนเดอร์ YSM</title>
<style>
:root {color-scheme:dark; background:#19151e; color:#f4edf7; font:16px/1.6 system-ui,sans-serif}
body{max-width:1200px;margin:0 auto;padding:clamp(1rem,4vw,3rem)}
h1,h2,h3,p{margin:.25rem 0 .75rem}h1{font-size:clamp(1.8rem,5vw,3rem)}
a{color:#ffc4e4}header{border-bottom:1px solid #655066;padding-bottom:1.5rem}
nav a{margin-right:1rem}summary{cursor:pointer;color:#ffc4e4}section{margin:2rem 0}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));margin-top:1rem}
article{background:#27202d;border:1px solid #55435b;border-radius:.75rem;padding:.75rem}
article p{color:#d8c2e0}article img{display:block;width:100%;border-radius:.4rem}
.reference{display:block;max-width:100%;margin:.75rem 0}
.samples{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
</style></head><body><header>
<h1>Satou · ภาพเรนเดอร์ YSM</h1>
<p>${cases.length} เคส · ${frames} เฟรมจากไฟล์โมเดล YSM ผ่าน Model Studio</p>
<p>กดรูปเพื่อดู PNG เต็มขนาด เฟรมของเคสเดียวกันใช้กล้องตำแหน่งเดียวกันทั้งสองชุด กด “ดูอีก … เฟรม” เพื่อเทียบท่าช่วงต้น กลาง และท้ายคลิป</p>
<p>เวลาและมุมกล้องระบุใต้ภาพ การทดสอบใน Minecraft ยังรอตรวจเรื่องตัวแปรเกม ฟิสิกส์ แสง และสิ่งของที่ถือ</p>
<p>ใน YSM คลิป <code>climb</code> และ <code>climbing</code> คือท่าคลานใต้ประตูกล ส่วนภาพปีนในชีตคอนเซปต์เป็นแบบร่างเดิม</p>
<p>ท่านอนใช้คีย์เฟรม YSM พร้อมมุมวางตัวของเตียงที่จำลองใน Model Studio</p>
<nav><a href="checklist.csv">ตารางตรวจโมเดล</a><a href="manifest.json">ไฟล์ต้นทางและ SHA-256</a><a href="ATTRIBUTION.md">เครดิต</a></nav>
</header><main>
${Object.keys(models)
  .map(
    (outfit) =>
      `<details open><summary>${outfitNames[outfit]}</summary><nav>${sheetLinks(outfit)}</nav></details>`,
  )
  .join("")}
${sections.join("\n")}
</main></body></html>`,
  );
}

module.exports = { writeReport };
