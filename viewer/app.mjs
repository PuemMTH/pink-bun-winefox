import * as THREE from "three";
import { OrbitControls } from "./lib/OrbitControls.js";
import { createCharacter, loadTexture } from "./model.mjs";

const $ = (id) => document.getElementById(id);
const labels = {
  idle: "ยืน",
  walk: "เดิน",
  run: "วิ่ง",
  jump: "กระโดด",
  sneak: "ย่อ",
  sit: "นั่ง",
  sneaking: "ย่อเดิน",
  sleep: "นอน",
  swim: "ว่ายน้ำ",
  swim_stand: "ลอยตัวในน้ำ",
  fly: "บิน",
  elytra_fly: "ร่อน",
  climb: "ปีน",
  climbing: "เกาะบันได",
  ride: "ขี่สัตว์",
  ride_pig: "ขี่หมู",
  boat: "นั่งเรือ",
  death: "ล้ม",
  attacked: "ถูกโจมตี",
};
const viewport = $("viewport"),
  scene = new THREE.Scene();
const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
renderer.setClearColor(0, 0);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.domElement.setAttribute("aria-label", "ตัวละครสามมิติ ลากเพื่อหมุน");
viewport.append(renderer.domElement);
const camera = new THREE.OrthographicCamera(-2, 2, 2, -2, 0.01, 100),
  controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minZoom = 0.4;
controls.maxZoom = 5;
controls.maxPolarAngle = Math.PI * 0.95;
controls.autoRotateSpeed = 1.1;
const ambient = new THREE.AmbientLight(0xffffff, 1.25);
scene.add(ambient);
const key = new THREE.DirectionalLight(0xfff4ed, 2.1);
key.position.set(-3, 6, -5);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
key.shadow.camera.left = -3;
key.shadow.camera.right = 3;
key.shadow.camera.top = 4;
key.shadow.camera.bottom = -2;
key.shadow.normalBias = 0.015;
key.shadow.bias = -0.0003;
scene.add(key);
const rim = new THREE.DirectionalLight(0xcfb6ff, 0.65);
rim.position.set(3, 3, 4);
scene.add(rim);
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(200, 200),
  new THREE.ShadowMaterial({ opacity: 0.18 }),
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.012;
ground.receiveShadow = true;
scene.add(ground);
const grid = new THREE.GridHelper(12, 48, 0x61506d, 0x3c3446);
grid.material.transparent = true;
grid.material.opacity = 0.42;
grid.position.y = -0.015;
scene.add(grid);
let character,
  info,
  clip = "idle",
  elapsed = 0,
  playing = true,
  rate = 1,
  last = performance.now(),
  modelHeight = 2,
  imported = null,
  urls = [];
let frames = 0,
  fpsStart = performance.now();

function resize() {
  const rect = viewport.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  const aspect = rect.width / rect.height,
    h = modelHeight * 1.42;
  camera.left = (-h * aspect) / 2;
  camera.right = (h * aspect) / 2;
  camera.top = h / 2;
  camera.bottom = -h / 2;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport);
function toast(text) {
  $("toast").textContent = text;
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").hidden = true), 4500);
}
function view(which = "front") {
  const target = controls.target.clone(),
    r = 5;
  camera.position
    .copy(target)
    .add(
      which === "back"
        ? new THREE.Vector3(0, 0, r)
        : which === "side"
          ? new THREE.Vector3(r, 0, 0)
          : new THREE.Vector3(0, 0.05, -r),
    );
  camera.zoom = 1;
  camera.updateProjectionMatrix();
  controls.update();
  document
    .querySelectorAll("[data-view]")
    .forEach((b) => b.classList.toggle("active", b.dataset.view === which));
}
function fit() {
  const box = new THREE.Box3().setFromObject(character.root);
  modelHeight = Math.max(1, box.max.y - box.min.y);
  controls.target.set(0, box.min.y + modelHeight * 0.48, 0);
  resize();
  view("front");
}
function selectClip(next) {
  if (!character?.animations[next]) return;
  clip = next;
  elapsed = 0;
  playing = true;
  $("play").textContent = "Ⅱ";
  $("play").setAttribute("aria-label", "หยุดแอนิเมชัน");
  $("clip-tag").textContent = next.replaceAll("_", " ").toUpperCase();
  $("clip-name").textContent = labels[next] || next;
  const length = Number(character.animations[next].animation_length) || 1;
  $("duration").textContent = length.toFixed(2);
  $("timeline").max = length;
  document.querySelectorAll("[data-clip]").forEach((b) => {
    b.classList.toggle("selected", b.dataset.clip === next);
    b.setAttribute("aria-pressed", String(b.dataset.clip === next));
  });
  $("expression-note").textContent =
    next === "run"
      ? "ตาแดงลายก้นหอยและสีหน้าตอนวิ่ง"
      : "กะพริบตาและขยับผมตามแอนิเมชันเดิม";
  if ([...$("more-clips").options].some((o) => o.value === next))
    $("more-clips").value = next;
  else $("more-clips").value = "";
}
async function loadModel(data) {
  $("loading").hidden = false;
  $("loading").style.display = "flex";
  try {
    const texture = await loadTexture(data.texture);
    const replacement = createCharacter(
      data.geometry,
      texture,
      data.animations,
    );
    if (character) {
      scene.remove(character.root);
      character.dispose();
    }
    character = replacement;
    info = data.info || {};
    character.setWireColor(
      $("background").value === "light" ? 0x785076 : 0xffb6d7,
    );
    const properties = info.properties || {},
      scale = Number(properties.height_scale) || 0.7;
    character.root.scale.set(
      Number(properties.width_scale) || scale,
      scale,
      Number(properties.width_scale) || scale,
    );
    scene.add(character.root);
    character.setMaterial($("material").value);
    $("model-title").textContent = info.metadata?.name || "Custom model";
    $("model-name").textContent = (info.metadata?.name || "Pink Bun").replace(
      " - Wine Fox Base",
      "",
    );
    $("model-detail").textContent = imported
      ? "Local model · Browser only"
      : "Wine Fox JK · Custom";
    for (const id of ["bones", "cubes", "triangles"])
      $(id).textContent = character.stats[id].toLocaleString();
    $("more-clips").replaceChildren(new Option("เลือกแอนิเมชัน", ""));
    const mainClips = Object.keys(character.animations).filter(
      (n) => !/parallel|^gui$|——|^empty$|\$/.test(n),
    );
    for (const n of mainClips)
      $("more-clips").add(new Option(labels[n] || n, n));
    document
      .querySelectorAll("[data-clip]")
      .forEach((b) => (b.disabled = !character.animations[b.dataset.clip]));
    selectClip(character.animations.idle ? "idle" : mainClips[0]);
    character.update(clip, 0, { blink: $("blink").checked });
    fit();
    $("loading").style.display = "none";
  } catch (error) {
    $("loading").textContent = "เปิดพรีวิวไม่ได้: " + error.message;
    toast(error.message);
    throw error;
  }
}
async function bundled() {
  const json = async (file) => {
    const r = await fetch(`assets/${file}`, { cache: "no-store" });
    if (!r.ok) throw Error("โหลด " + file + " ไม่สำเร็จ");
    return r.json();
  };
  const [geometry, animations, meta] = await Promise.all([
    json("model.json"),
    json("animations.json"),
    json("info.json"),
  ]);
  await loadModel({
    geometry,
    animations,
    info: meta,
    texture: "assets/texture.png?v=" + Date.now(),
  });
}
async function folder(files) {
  const entries = new Map(
    [...files].map((f) => [f.webkitRelativePath.replaceAll("\\", "/"), f]),
  );
  const match = [...entries.keys()].find(
    (p) => p.endsWith("/ysm.json") || p === "ysm.json",
  );
  if (!match) throw Error("เลือกโฟลเดอร์โมเดลที่มี ysm.json");
  const base = match.slice(0, -"ysm.json".length),
    meta = JSON.parse(await entries.get(match).text()),
    player = meta.files?.player;
  if (!player?.model?.main) throw Error("ไม่พบโมเดลหลักใน ysm.json");
  const get = (name) => {
    const f = entries.get(base + name);
    if (!f) throw Error("ไม่พบไฟล์ " + name);
    return f;
  };
  const geometry = JSON.parse(await get(player.model.main).text()),
    animations = { animations: {} };
  for (const file of Object.values(player.animation || {})) {
    const value = JSON.parse(await get(file).text());
    Object.assign(animations.animations, value.animations || {});
  }
  const choice = player.texture?.[0],
    name = typeof choice === "string" ? choice : choice?.uv;
  if (!name) throw Error("ไม่พบพื้นผิวของโมเดล");
  const texture = URL.createObjectURL(get(name));
  urls.push(texture);
  return { geometry, animations, info: meta, texture };
}

document
  .querySelectorAll("[data-view]")
  .forEach((b) => (b.onclick = () => view(b.dataset.view)));
document
  .querySelectorAll("[data-clip]")
  .forEach((b) => (b.onclick = () => selectClip(b.dataset.clip)));
$("more-clips").onchange = (e) => selectClip(e.target.value);
$("reset-camera").onclick = () => fit();
$("play").onclick = () => {
  playing = !playing;
  $("play").textContent = playing ? "Ⅱ" : "▶";
  $("play").setAttribute(
    "aria-label",
    playing ? "หยุดแอนิเมชัน" : "เล่นแอนิเมชัน",
  );
};
$("timeline").oninput = (e) => {
  elapsed = Number(e.target.value);
  playing = false;
  $("play").textContent = "▶";
  $("play").setAttribute("aria-label", "เล่นแอนิเมชัน");
};
$("speed").oninput = (e) => {
  rate = Number(e.target.value);
  $("speed-value").textContent = rate + "×";
};
$("material").onchange = (e) => character?.setMaterial(e.target.value);
$("grid").onchange = (e) => {
  grid.visible = e.target.checked;
  ground.visible = e.target.checked;
};
$("auto-rotate").onchange = (e) => (controls.autoRotate = e.target.checked);
$("background").onchange = (e) => {
  const light = e.target.value === "light",
    transparent = e.target.value === "transparent";
  document.body.classList.toggle("light", light);
  $("viewport").style.background = transparent
    ? "repeating-conic-gradient(#29242e 0% 25%,#221e27 0% 50%) 0 0/24px 24px"
    : light
      ? "radial-gradient(ellipse at 50% 35%,#f5f0f7,#dcd7e5)"
      : "";
  renderer.setClearColor(0, 0);
  grid.material.color?.set(light ? 0x9a8aa7 : 0x3c3446);
  character?.setWireColor(light ? 0x785076 : 0xffb6d7);
};
$("capture").onclick = () => {
  if (!character) return;
  const background = $("background").value;
  renderer.setClearColor(
    background === "light" ? 0xe6e0ed : 0x1b1923,
    background === "transparent" ? 0 : 1,
  );
  renderer.render(scene, camera);
  const link = document.createElement("a");
  link.download = `pink-bun-${clip}.png`;
  link.href = renderer.domElement.toDataURL("image/png");
  link.click();
  renderer.setClearColor(0, 0);
  toast("บันทึกภาพ PNG แล้ว");
};
$("reload").onclick = async () => {
  try {
    if (imported) {
      const files = imported.files;
      imported = { ...(await folder(files)), files };
      await loadModel(imported);
    } else await bundled();
    toast("โหลดโมเดลใหม่แล้ว");
  } catch {}
};
$("open-model").onclick = () => $("model-files").click();
$("model-files").onchange = async (e) => {
  try {
    const files = [...e.target.files],
      data = await folder(files);
    imported = { ...data, files };
    await loadModel(imported);
    toast("เปิดไฟล์ในเบราว์เซอร์แล้ว");
  } catch (error) {
    toast(error.message);
  }
};
controls.addEventListener("start", () =>
  document
    .querySelectorAll("[data-view]")
    .forEach((b) => b.classList.remove("active")),
);
window.addEventListener("beforeunload", () =>
  urls.forEach((u) => URL.revokeObjectURL(u)),
);
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (character) {
    const duration = Number(character.animations[clip]?.animation_length) || 1;
    if (playing) {
      elapsed += dt * rate;
      if (elapsed > duration) {
        if ($("loop").checked) elapsed %= duration;
        else {
          elapsed = duration;
          playing = false;
          $("play").textContent = "▶";
          $("play").setAttribute("aria-label", "เล่นแอนิเมชัน");
        }
      }
    }
    character.update(clip, elapsed, { blink: $("blink").checked });
    $("timeline").value = elapsed;
    $("time").textContent = elapsed.toFixed(2);
  }
  controls.update();
  renderer.render(scene, camera);
  frames++;
  if (now - fpsStart > 1000) {
    $("fps").textContent =
      Math.round((frames * 1000) / (now - fpsStart)) + " FPS";
    frames = 0;
    fpsStart = now;
  }
  requestAnimationFrame(frame);
}
resize();
requestAnimationFrame(frame);
bundled().catch(() => {});
