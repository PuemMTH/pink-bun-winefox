const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { createHash } = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { parseArgs } = require("node:util");
const { writeReport } = require("./render-report.cjs");

const root = path.resolve(__dirname, "..");
const viewer = path.join(root, "viewer");
const reference = path.join(root, "docs/ysm-reference-pack-v1");
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const { values: options } = parseArgs({
  options: {
    outfit: { type: "string" },
    case: { type: "string" },
    "primary-only": { type: "boolean" },
    sequence: { type: "boolean" },
    "inspection-views": { type: "boolean" },
    "part-review": { type: "string" },
    "eye-review": { type: "boolean" },
    "shirt-review": { type: "string" },
    "aunt-review": { type: "boolean" },
    "aunt-flight-review": { type: "string" },
    "flight-review": { type: "string" },
  },
});
const models = {
  school: "dist/pink_bun_winefox",
  white: "dist/pink_bun_winefox_white",
};
const framing = {
  bust: "front",
  detail_front: "front",
  detail_cuff: "front3q",
  detail_hem: "front",
  detail_back: "back3q",
  elytra_fly: "side",
  swim: "side",
  swim_stand: "front",
  climb: "back3q",
  climbing: "side",
  sleep: "front3q",
  ride_pig: "side",
  death: "back3q",
  use_offhand: "right",
  hover_fadeout: "side",
  hover: "back3q",
  focus: "front",
  sneaking: "side",
};
const sampleTimes = {
  idle: [1, 12, 22, 25],
  walk: [0, 0.2, 0.45, 0.7, 0.95],
  run: [0, 0.12, 0.24, 0.3, 0.36, 0.48, 0.6],
  jump: [0, 0.12, 0.24, 0.32, 0.4, 0.58, 0.74],
  death: [0, 0.125, 0.2083, 0.25, 0.4583, 0.7083, 0.8333, 1],
  attacked: [0, 0.08, 0.1667, 0.25, 0.375, 0.5],
  hover_fadeout: [0, 0.1667, 0.375, 0.6667, 1],
  hover: [0, 0.2, 0.45, 0.75, 1],
  focus: [0, 0.25, 0.5, 1, 1.5, 3, 4.4167],
  extra0: [0, 0.75, 1.2, 1.21, 1.5, 2.25, 3],
  extra7: [
    ...Array.from({ length: 15 }, (_, i) => i / 2),
    4.875,
    4.8917,
    4.9167,
    7.4583,
  ].sort((a, b) => a - b),
};
const staticClips = new Set([
  "sit",
  "sneaking",
  "climbing",
  "sleep",
  "boat",
  "ride",
  "ride_pig",
]);
const primaryTimes = {
  idle: 1,
  walk: 0.2,
  run: 0.12,
  jump: 0.24,
  death: 1,
  attacked: 0.1667,
  extra0: 1.5,
};
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const jumpVariables = (time) => ({
  "query.vertical_speed": +(8 - 20 * time).toFixed(2),
  "query.is_on_ground": 0,
});

function readModel(outfit, folder = models[outfit], captureKey = outfit) {
  const directory = path.resolve(root, folder);
  const hashes = {};
  const bytes = (file) => {
    const data = fs.readFileSync(path.join(directory, file));
    hashes[file] = digest(data);
    return data;
  };
  const info = JSON.parse(bytes("ysm.json"));
  const player = info.files.player;
  const geometry = JSON.parse(bytes(player.model.main));
  const animations = {};
  const sources = {};
  // Checklist targets vanilla and wheel clips. Optional mod integrations are separate.
  for (const group of ["main", "extra"]) {
    const file = player.animation[group];
    const clips = JSON.parse(bytes(file)).animations;
    Object.assign(animations, clips);
    for (const clip of Object.keys(clips)) sources[clip] = file;
  }
  const choice = player.texture[0];
  const textureFile = typeof choice === "string" ? choice : choice.uv;
  const texture = bytes(textureFile);
  return {
    data: {
      info,
      geometry,
      animations: { animations },
      texture: "/texture/" + captureKey,
    },
    texture,
    sources,
    provenance: {
      directory: path.relative(root, directory).split(path.sep).join("/"),
      name: info.metadata.name,
      sha256: hashes,
      texture: textureFile,
    },
  };
}

function renderCase(sheet, panel, index, model, cameraView) {
  const { id: state, view: referenceView = "detail" } = panel;
  const id =
    sheet.key +
    "-" +
    (index + 1) +
    (cameraView && cameraView !== "front3q" ? "-" + cameraView : "");
  const clip = ["details", "turnaround"].includes(sheet.category)
    ? "idle"
    : state;
  const animation = model.data.animations.animations[clip];
  assert(
    animation,
    `${id}: ${clip} is missing from the built YSM animation files`,
  );
  const view =
    cameraView ??
    (["bust", "varied", "detail"].includes(referenceView)
      ? framing[state] || framing[referenceView] || "front3q"
      : referenceView);
  const duration = Number(animation.animation_length) || 0;
  const animated =
    ["main", "extra"].includes(sheet.category) && !staticClips.has(clip);
  let times = [clip === "idle" ? 1 : 0];
  if (animated) {
    const fractions = [0, 0.125, 0.25, 0.5, 0.75, 0.875];
    if (animation.loop !== true) fractions.push(1);
    times = sampleTimes[clip] || [
      ...new Set(fractions.map((t) => +(duration * t).toFixed(4))),
    ];
  }
  const heldPose = sheet.category === "main" && staticClips.has(clip);
  if (options.sequence && heldPose) {
    let span = duration;
    if (!span) {
      for (const bone of Object.values(animation.bones || {}))
        for (const channel of Object.values(bone))
          if (channel && typeof channel === "object" && !Array.isArray(channel))
            for (const key of Object.keys(channel))
              if (Number.isFinite(Number(key)))
                span = Math.max(span, Number(key));
    }
    times = [0, 0.25, 0.5, 0.75, 1].map((p) => +(p * (span || 1)).toFixed(4));
  } else if (options.sequence && sheet.category === "main" && clip === "idle") {
    times = [1, 12, 18.5, 22, 25];
  }
  const primaryTime =
    primaryTimes[clip] ?? times[Math.min(2, times.length - 1)];
  if (options["primary-only"]) times = [primaryTime];
  return {
    id,
    clip,
    state,
    view,
    referenceView,
    category: sheet.category,
    outfit: sheet.outfit,
    ...(options.sequence && heldPose ? { heldPose: true } : {}),
    source: model.sources[clip],
    reference: sheet.file,
    panel: index + 1,
    frames: times.map((time, i) => {
      const variables = clip === "jump" ? jumpVariables(time) : {};
      if (clip === "extra0") {
        // First accessory toggle, with v.roaming.b initially zero.
        const toggle = Object.entries(animation.timeline || {}).find(
          ([, value]) => value === "v.roaming.a=1-v.roaming.b;",
        );
        if (toggle) variables["v.roaming.a"] = +(time >= Number(toggle[0]));
      }
      return {
        time,
        variables,
        file: `frames/${id}-${i + 1}.png`,
        primary: time === primaryTime,
      };
    }),
  };
}

function addInspectionViews(jobs) {
  const angles = ["left", "right", "top", "bottom"];
  const inspected = new Set(["main", "extra", "photo"]);
  for (const job of jobs) if (job.view === "side") job.view = "right";
  const coverage = new Set(jobs.map(({ state, view }) => `${state}/${view}`));
  for (const job of [...jobs]) {
    const views = inspected.has(job.category)
      ? angles
      : job.category === "turnaround"
        ? ["top", "bottom"]
        : [];
    for (const view of views) {
      const isTurnaround = job.category === "turnaround";
      const state = isTurnaround ? view : job.state;
      const key = `${state}/${view}`;
      if (coverage.has(key)) continue;
      coverage.add(key);
      const id = `${job.id}-${view}`;
      jobs.push({
        ...job,
        id,
        state,
        view,
        frames: job.frames.map((frame, i) => ({
          ...frame,
          file: `frames/${id}-${i + 1}.png`,
        })),
      });
    }
  }
}

function browserPath() {
  const programRoots = [
    process.env.ProgramFiles,
    process.env["ProgramFiles(x86)"],
    process.env.LOCALAPPDATA,
  ].filter(Boolean);
  const choices = [
    ...programRoots.flatMap((base) =>
      [
        "Google/Chrome/Application/chrome.exe",
        "Microsoft/Edge/Application/msedge.exe",
      ].map((app) => path.join(base, app)),
    ),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ];
  const browser =
    process.env.CHROME_PATH ||
    choices.find((candidate) => fs.existsSync(candidate));
  assert(
    browser,
    "Install Chrome/Edge/Chromium or set CHROME_PATH to its executable.",
  );
  return browser;
}

async function capture(output, plan, modelData) {
  const browser = browserPath();
  const pending = new Map(
    Object.values(plan).flatMap((jobs) =>
      jobs.flatMap((job) => job.frames.map((frame) => [frame.file, frame])),
    ),
  );
  const total = pending.size;
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ysm-render-chrome-"));
  let child, resolveJob, rejectJob;
  const finished = new Promise((resolve, reject) => {
    resolveJob = resolve;
    rejectJob = reject;
  });
  const send = (res, body, type = "text/plain") =>
    res
      .writeHead(200, { "Content-Type": type, "Cache-Control": "no-store" })
      .end(body);
  const server = http.createServer(async (req, res) => {
    try {
      const url = req.url;
      if (req.method === "GET") {
        if (url === "/")
          return send(
            res,
            '<!doctype html><meta charset="utf-8"><title>Model Studio export</title><script type="module" src="/export.mjs"></script>',
            "text/html",
          );
        if (url === "/plan")
          return send(res, JSON.stringify(plan), "application/json");
        if (url.startsWith("/model/") && modelData[url.slice(7)])
          return send(
            res,
            JSON.stringify(modelData[url.slice(7)].data),
            "application/json",
          );
        if (url.startsWith("/texture/") && modelData[url.slice(9)])
          return send(res, modelData[url.slice(9)].texture, "image/png");
        if (/^\/(?:lib\/)?[a-z0-9._-]+\.(?:mjs|js)$/i.test(url)) {
          return send(
            res,
            fs.readFileSync(path.join(viewer, url.slice(1))),
            "text/javascript",
          );
        }
      }
      if (req.method === "POST") {
        if (url === "/done") {
          assert.equal(pending.size, 0, "Browser finished with missing frames");
          send(res, "complete");
          return resolveJob();
        }
        const frame = pending.get(url.slice(9));
        if (url === "/error" || (url.startsWith("/capture/") && frame)) {
          const chunks = [];
          let size = 0;
          for await (const bytes of req) {
            size += bytes.length;
            assert(size < 2_000_000, "Oversize browser response");
            chunks.push(bytes);
          }
          const data = Buffer.concat(chunks);
          if (url === "/error") throw Error(data.toString());
          assert(
            data.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex")),
            "Browser response is not PNG",
          );
          assert.equal(data.readUInt32BE(16), 512);
          assert.equal(data.readUInt32BE(20), 512);
          fs.writeFileSync(path.join(output, frame.file), data);
          frame.sha256 = digest(data);
          pending.delete(frame.file);
          const count = total - pending.size;
          if (count % 30 === 0 || count === total)
            console.log(`Rendered ${count}/${total} PNGs`);
          return send(res, "saved");
        }
      }
      res.writeHead(404).end("Not found");
    } catch (error) {
      res.writeHead(500).end(error.message);
      rejectJob(error);
    }
  });
  let deadline;
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    child = spawn(
      browser,
      [
        "--headless=new",
        "--enable-unsafe-swiftshader",
        "--use-angle=swiftshader",
        "--disable-background-networking",
        "--no-first-run",
        "--no-default-browser-check",
        "--user-data-dir=" + profile,
        "http://127.0.0.1:" + server.address().port + "/",
      ],
      { windowsHide: true, stdio: "ignore" },
    );
    child.once("error", rejectJob);
    child.once("exit", (code) =>
      rejectJob(Error("Chrome exited before export finished (" + code + ")")),
    );
    deadline = setTimeout(
      () => rejectJob(Error("Browser export exceeded 5 minutes")),
      300_000,
    );
    await finished;
  } finally {
    clearTimeout(deadline);
    if (child?.pid && child.exitCode === null) {
      child.kill();
      await new Promise((resolve) => child.once("close", resolve));
    }
    server.closeAllConnections();
    server.close();
    if (
      path.dirname(profile) === os.tmpdir() &&
      path.basename(profile).startsWith("ysm-render-chrome-")
    ) {
      try {
        fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5 });
      } catch {}
    }
  }
}

async function main() {
  if (options["flight-review"])
    return require("./all-flights-review.cjs")({
      root,
      baseline: options["flight-review"],
      readModel,
      capture,
      stamp,
    });
  if (options["aunt-flight-review"]) {
    const source = readJson(path.join(root, "vendor/winefox-matured/animations/main.animation.json"));
    const { alternatives } = require("../src/aunt-flight.cjs")(source.animations.elytra_fly);
    return require("./aunt-flight-review.cjs")({
      root,
      baseline: options["aunt-flight-review"],
      readModel,
      capture,
      stamp,
      alternatives,
    });
  }
  if (options["aunt-review"])
    return require("./aunt-review.cjs")({
      root,
      readModel,
      capture,
      stamp,
      jumpVariables,
    });
  if (options["shirt-review"])
    return require("./shirt-comparison.cjs")({
      root,
      baseline: options["shirt-review"],
      readModel,
      capture,
      stamp,
      jumpVariables,
    });
  if (options["eye-review"])
    return require("./eye-comparison.cjs")({
      root,
      readModel,
      capture,
      stamp,
      jumpVariables,
    });
  if (options["part-review"])
    return require("./part-comparison.cjs")({
      root,
      baseline: options["part-review"],
      readModel,
      capture,
      stamp,
    });
  assert(
    !options.sequence || !options["primary-only"],
    "Choose --sequence or --primary-only",
  );
  assert(
    !options["inspection-views"] || options.sequence,
    "--inspection-views requires --sequence",
  );
  if (options.outfit)
    assert(
      Object.hasOwn(models, options.outfit),
      "Choose --outfit school or white",
    );
  const { sheets } = readJson(path.join(reference, "manifest.json"));
  const selected = sheets.filter(
    (sheet) =>
      sheet.category !== "overview" &&
      (!options.outfit || options.outfit === sheet.outfit) &&
      (!options.case ||
        sheet.panels.some(
          (_, i) => options.case === sheet.key + "-" + (i + 1),
        )),
  );
  assert(selected.length > 0, "No matching reference-pack checks");
  const modelData = Object.fromEntries(
    [...new Set(selected.map((s) => s.outfit))].map((outfit) => [
      outfit,
      readModel(outfit),
    ]),
  );
  const plan = Object.fromEntries(
    Object.keys(modelData).map((outfit) => [outfit, []]),
  );
  for (const sheet of selected) {
    for (const [i, panel] of sheet.panels.entries()) {
      if (options.case && options.case !== sheet.key + "-" + (i + 1)) continue;
      const photoViews =
        options.sequence && sheet.category === "photo"
          ? ["front", "front3q", "side", "back3q", "back"]
          : [undefined];
      for (const view of photoViews)
        plan[sheet.outfit].push(
          renderCase(sheet, panel, i, modelData[sheet.outfit], view),
        );
    }
  }
  if (options["inspection-views"])
    for (const jobs of Object.values(plan)) addInspectionViews(jobs);
  const reportRoot = path.join(root, "dist/ysm-render-checks");
  fs.mkdirSync(reportRoot, { recursive: true });
  const output = fs.mkdtempSync(path.join(reportRoot, stamp + "-"));
  fs.mkdirSync(path.join(output, "frames"), { recursive: true });
  console.log("Rendering YSM in Model Studio: " + output);
  await capture(output, plan, modelData);
  writeReport(
    output,
    reference,
    selected,
    Object.values(plan).flat(),
    Object.fromEntries(
      Object.entries(modelData).map(([outfit, value]) => [
        outfit,
        value.provenance,
      ]),
    ),
    Object.fromEntries(
      [
        "export.mjs",
        "rendering.mjs",
        "model.mjs",
        "animation.mjs",
        "lib/three.module.min.js",
        "lib/three.core.min.js",
      ].map((file) => [file, digest(fs.readFileSync(path.join(viewer, file)))]),
    ),
  );
  console.log(path.join(output, "index.html"));
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
