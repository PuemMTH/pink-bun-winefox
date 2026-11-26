import * as THREE from "three";
import { OrbitControls } from "./lib/OrbitControls.js";
import { createCharacter, loadTexture } from "./model.mjs";
import {
  mainClips,
  poseClips,
  playback,
  durationOf,
  advance,
  shownIn,
  readModelFolders,
} from "./studio.mjs";

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
  hover_fadeout: "เริ่มลอยตัว",
  hover: "ลอยตัว",
  focus: "มองตามเป้า",
  use_mainhand: "ใช้มือหลัก",
  use_offhand: "ใช้มือรอง",
  swing_hand: "แกว่งแขน",
};
const angles = {
  front: "ด้านหน้า",
  side: "ด้านข้าง",
  back: "ด้านหลัง",
  three: "สามส่วน",
  top: "ด้านบน",
  free: "อิสระ",
};
const models = [],
  views = [],
  poseViews = [];
const allViews = () => [...views, ...poseViews];
const gallery = () => $("layout").value === "poses";
const currentViews = () => (gallery() ? poseViews : views);
let activeId = null,
  activeView = null,
  nextId = 1,
  busy = false;
let last = performance.now(),
  frames = 0,
  fpsStart = last;
const selected = () => models.find((model) => model.id === activeId);
const transportDuration = () => {
  const model = selected();
  return !model
    ? 1
    : gallery()
      ? Math.max(
          ...poseClips(model.character.animations).map((clip) =>
            durationOf(model, clip),
          ),
          1,
        )
      : durationOf(model);
};
const modelLabel = (model) => `${model.name} #${model.id}`;
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
renderer.autoClear = false;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.domElement.setAttribute("aria-label", "ตัวละครสามมิติหลายช่องมอง");
viewport.prepend(renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff, 1.25));
const key = new THREE.DirectionalLight(0xfff4ed, 2.1);
key.position.set(-3, 6, -5);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
Object.assign(key.shadow.camera, { left: -6, right: 6, top: 5, bottom: -3 });
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
const grid = new THREE.GridHelper(30, 120, 0x61506d, 0x3c3446);
grid.material.transparent = true;
grid.material.opacity = 0.42;
grid.position.y = -0.015;
scene.add(grid);

function toast(text) {
  $("toast").textContent = text;
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").hidden = true), 4500);
}
async function operation(action) {
  if (busy) return;
  busy = true;
  $("loading").hidden = false;
  for (const id of ["open-model", "add-bundled", "duplicate-model", "reload"])
    $(id).disabled = true;
  try {
    await action();
  } catch (error) {
    toast(error.message);
  } finally {
    busy = false;
    $("loading").hidden = true;
    for (const id of ["open-model", "add-bundled", "reload"])
      $(id).disabled = false;
    $("duplicate-model").disabled = !selected();
    $("empty").hidden = models.length > 0;
  }
}

function activateView(view) {
  if (!view) return;
  activeView = view;
  for (const item of allViews())
    item.pane.classList.toggle("active-pane", item === view);
  document
    .querySelectorAll("[data-view]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === view.angle),
    );
  $("active-view-name").textContent = view.clip
    ? labels[view.clip] || view.clip
    : `ช่อง ${views.indexOf(view) + 1}`;
}
function setAngle(view, angle) {
  view.angle = angle;
  view.angleSelect.value = angle;
  if (angle !== "free") {
    const directions = {
      front: [0, 0.05, -5],
      side: [5, 0, 0],
      back: [0, 0, 5],
      three: [-4, 1.5, -5],
      top: [0, 5, -0.001],
    };
    view.camera.position
      .copy(view.controls.target)
      .add(new THREE.Vector3(...directions[angle]));
    view.camera.zoom = 1;
    view.camera.updateProjectionMatrix();
    view.controls.update();
  }
  if (view === activeView) activateView(view);
}
function updateProjection(view) {
  const rect = view.surface.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const aspect = rect.width / rect.height;
  const h = Math.max(view.height * 1.25, (view.width / aspect) * 1.25);
  Object.assign(view.camera, {
    left: (-h * aspect) / 2,
    right: (h * aspect) / 2,
    top: h / 2,
    bottom: -h / 2,
  });
  view.camera.updateProjectionMatrix();
}
function fit(view) {
  const box = new THREE.Box3();
  for (const model of models)
    if (shownIn(model, view.selection)) {
      if (view.clip) {
        // Include the pose's motion range so low and airborne poses stay in frame.
        const duration = durationOf(model, view.clip);
        for (const fraction of [0, 0.25, 0.5, 0.75, 0.999]) {
          model.character.update(view.clip, duration * fraction, {
            blink: false,
          });
          box.expandByObject(model.character.root);
        }
        updatePose(model);
      } else box.expandByObject(model.character.root);
    }
  if (box.isEmpty()) {
    box.min.set(-0.5, 0, -0.5);
    box.max.set(0.5, 2, 0.5);
  }
  const size = box.getSize(new THREE.Vector3());
  view.height = Math.max(1, size.y);
  view.width = Math.max(0.7, Math.hypot(size.x, size.z));
  view.controls.target.copy(box.getCenter(new THREE.Vector3()));
  updateProjection(view);
  setAngle(view, view.angle === "free" ? "three" : view.angle);
}
function resize() {
  const rect = viewport.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  allViews().forEach(updateProjection);
}
new ResizeObserver(resize).observe(viewport);
function updateViewChoices() {
  for (const view of views) {
    if (
      view.selection !== "all" &&
      !models.some((m) => String(m.id) === view.selection)
    )
      view.selection = "all";
    view.modelSelect.replaceChildren(new Option("ทุกตัวละคร", "all"));
    for (const model of models)
      view.modelSelect.add(new Option(modelLabel(model), String(model.id)));
    view.modelSelect.value = view.selection;
  }
}
function setLayout(count) {
  const poses = count === "poses";
  $("layout").value = String(count);
  const list = poses ? poseViews : views;
  const model = selected();
  const clips = poses && model ? poseClips(model.character.animations) : [];
  if (poses) count = clips.length;
  // Preserve cameras and model assignments when reducing/re-expanding the layout.
  const previousCount = list.length;
  while (list.length < count) {
    const index = list.length,
      pane = document.createElement("section");
    pane.className = "view-pane";
    pane.setAttribute(
      "aria-label",
      poses ? `ท่า ${clips[index]}` : `ช่องมอง ${index + 1}`,
    );
    const header = document.createElement("div");
    header.className = "pane-header";
    const number = document.createElement("span");
    number.className = "pane-number";
    number.textContent = `VIEW ${index + 1}`;
    const modelSelect = document.createElement("select");
    modelSelect.setAttribute("aria-label", `ตัวละครในช่อง ${index + 1}`);
    const angleSelect = document.createElement("select");
    angleSelect.setAttribute("aria-label", `มุมกล้องช่อง ${index + 1}`);
    for (const [value, label] of Object.entries(angles))
      angleSelect.add(new Option(label, value));
    header.append(number, modelSelect, angleSelect);
    const surface = document.createElement("div");
    surface.className = "pane-surface";
    surface.tabIndex = 0;
    surface.setAttribute("aria-label", `หมุนและซูมช่อง ${index + 1}`);
    if (poses) surface.setAttribute("aria-label", `หมุนท่า ${clips[index]}`);
    pane.append(header, surface);
    $("view-panes").append(pane);
    const camera = new THREE.OrthographicCamera(-2, 2, 2, -2, 0.01, 200);
    const controls = new OrbitControls(camera, surface);
    if (poses) {
      controls.enableZoom = false; // Wheel scrolls the gallery instead of zooming one card.
      surface.style.touchAction = "pan-y";
    }
    Object.assign(controls, {
      enableDamping: true,
      dampingFactor: 0.08,
      minZoom: 0.2,
      maxZoom: 8,
      maxPolarAngle: Math.PI * 0.999,
      autoRotateSpeed: 1.1,
      autoRotate: $("auto-rotate").checked,
    });
    const view = {
      pane,
      surface,
      camera,
      controls,
      modelSelect,
      angleSelect,
      selection: "all",
      angle: poses ? "front" : ["front", "side", "back", "three"][index],
      title: number,
      elapsed: 0,
      height: 2,
      width: 1,
    };
    list.push(view);
    pane.onpointerdown = () => activateView(view);
    pane.onfocusin = () => activateView(view);
    modelSelect.onchange = () => {
      view.selection = modelSelect.value;
      fit(view);
    };
    angleSelect.onchange = () => setAngle(view, angleSelect.value);
    controls.addEventListener("start", () => {
      activateView(view);
      setAngle(view, "free");
    });
  }
  allViews().forEach((view) => {
    const index = list.indexOf(view);
    view.pane.hidden = index < 0 || index >= count;
    view.controls.enabled = !view.pane.hidden;
  });
  if (poses)
    list.slice(0, count).forEach((view, index) => {
      view.clip = clips[index];
      view.selection = String(model.id);
      view.modelSelect.hidden = true;
      view.title.textContent = labels[view.clip] || view.clip;
      view.pane.setAttribute("aria-label", `ท่า ${view.title.textContent}`);
    });
  $("view-panes").dataset.layout = poses ? "poses" : count;
  $("navigation-hint").textContent = poses
    ? "เลื่อนในตารางเพื่อดูทุกท่า · ลากตัวละครเพื่อหมุน"
    : "ลากเพื่อหมุน · เลื่อนเพื่อซูม · คลิกขวาเพื่อเลื่อนมุม";
  document.querySelector(".stage").dataset.layout = poses ? "poses" : count;
  document
    .querySelectorAll("[data-view], #reset-camera")
    .forEach((button) => (button.disabled = count === 0));
  if (!count) activeView = null;
  updateViewChoices();
  activateView(
    activeView && list.includes(activeView) && !activeView.pane.hidden
      ? activeView
      : list[0],
  );
  resize();
  (poses ? list.slice(0, count) : list.slice(previousCount)).forEach(fit);
}
async function characterFrom(data) {
  const local = typeof data.texture !== "string",
    url = local ? URL.createObjectURL(data.texture) : data.texture;
  let texture;
  try {
    texture = await loadTexture(url);
    const character = createCharacter(data.geometry, texture, data.animations);
    const properties = data.info?.properties || {},
      scale = Number(properties.height_scale) || 0.7;
    character.root.scale.set(
      Number(properties.width_scale) || scale,
      scale,
      Number(properties.width_scale) || scale,
    );
    character.setMaterial($("material").value);
    character.setWireColor(
      $("background").value === "light" ? 0x785076 : 0xffb6d7,
    );
    return character;
  } catch (error) {
    texture?.dispose();
    throw error;
  } finally {
    if (local) URL.revokeObjectURL(url);
  }
}
function dispose(model) {
  scene.remove(model.character.root);
  model.character.dispose();
}
async function addModels(dataList) {
  const pending = [];
  try {
    for (const data of dataList) {
      const character = await characterFrom(data);
      pending.push({
        id: nextId++,
        name:
          data.info?.metadata?.name ||
          data.source?.manifest.split("/").slice(-2, -1)[0] ||
          "Custom model",
        character,
        data,
        visible: true,
        ...playback(character.animations),
      });
    }
  } catch (error) {
    pending.forEach(dispose);
    throw error;
  }
  for (const model of pending) {
    models.push(model);
    scene.add(model.character.root);
    updatePose(model);
  }
  activeId = pending.at(-1)?.id ?? activeId;
  arrange();
}
function updatePose(model) {
  // Hold the final frame even when the source clip itself is marked looping.
  const time = model.loop
    ? model.elapsed
    : Math.min(model.elapsed, durationOf(model) - 1e-7);
  model.character.update(model.clip, time, { blink: model.blink });
}
function arrange() {
  let cursor = 0;
  for (const model of models) {
    model.character.root.position.x = 0;
    const size = new THREE.Box3()
      .setFromObject(model.character.root)
      .getSize(new THREE.Vector3());
    model.spacing = Math.max(0.8, size.x + 0.3);
    if (model.visible) cursor += model.spacing;
  }
  let offset = -cursor / 2;
  for (const model of models)
    if (model.visible) {
      model.character.root.position.x = offset + model.spacing / 2;
      offset += model.spacing;
    }
  refreshModels();
  updateViewChoices();
  views.forEach(fit);
}
function refreshModels() {
  $("model-list").replaceChildren();
  $("model-count").textContent = models.length;
  $("empty").hidden = models.length > 0;
  $("model-name").textContent =
    models.length > 1
      ? `${models.length} ตัวละคร`
      : models[0]?.name || "Model Studio";
  for (const model of models) {
    const row = document.createElement("div");
    row.className = "model-row";
    row.classList.toggle("selected", model.id === activeId);
    const show = document.createElement("input");
    show.type = "checkbox";
    show.checked = model.visible;
    show.setAttribute("aria-label", `แสดง ${modelLabel(model)}`);
    show.onchange = () => {
      model.visible = show.checked;
      arrange();
    };
    const choose = document.createElement("button");
    choose.className = "model-select";
    choose.textContent = modelLabel(model);
    choose.setAttribute("aria-pressed", String(model.id === activeId));
    choose.onclick = () => {
      activeId = model.id;
      refreshModels();
    };
    const remove = document.createElement("button");
    remove.className = "remove-model";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `นำ ${modelLabel(model)} ออกจากฉาก`);
    remove.onclick = () => {
      if (busy) return;
      models.splice(models.indexOf(model), 1);
      dispose(model);
      if (activeId === model.id) activeId = models.at(-1)?.id ?? null;
      arrange();
    };
    row.append(show, choose, remove);
    $("model-list").append(row);
  }
  if (gallery()) setLayout("poses");
  refreshInspector();
}
function refreshInspector() {
  const model = selected(),
    animations = model?.character.animations || {};
  $("model-title").textContent = model ? modelLabel(model) : "ยังไม่มีตัวละคร";
  $("model-detail").textContent = model?.data.source
    ? "Local model · Browser only"
    : model
      ? `ดัดแปลงโดย ${model.data.info?.metadata?.authors?.at(-1)?.name || "puemmth"} · ฐาน Wine Fox JK`
      : "เพิ่มโมเดลเพื่อเริ่มดู";
  $("model-avatar").hidden = !!model?.data.source || !model;
  for (const id of ["bones", "cubes", "triangles"])
    $(id).textContent = model?.character.stats[id].toLocaleString() || "—";
  $("more-clips").replaceChildren(new Option("เลือกแอนิเมชัน", ""));
  for (const name of mainClips(animations))
    $("more-clips").add(new Option(labels[name] || name, name));
  document.querySelectorAll("[data-clip]").forEach((button) => {
    button.disabled = !animations[button.dataset.clip];
    const isSelected = !gallery() && button.dataset.clip === model?.clip;
    button.classList.toggle("selected", isSelected);
    button.setAttribute("aria-pressed", String(isSelected));
  });
  for (const id of ["duplicate-model", "sync-motion", "blink", "loop", "speed"])
    $(id).disabled = !model;
  for (const id of ["play", "timeline", "more-clips"])
    $(id).disabled = !model?.clip;
  $("clip-tag").textContent =
    gallery() && model
      ? `${poseClips(animations).length} ท่า`
      : model?.clip?.replaceAll("_", " ").toUpperCase() || "—";
  $("clip-name").textContent = gallery()
    ? "ทุกท่าทาง"
    : labels[model?.clip] || model?.clip || "ไม่มีแอนิเมชัน";
  $("more-clips").value = gallery() ? "" : model?.clip || "";
  $("duration").textContent = model ? transportDuration().toFixed(2) : "0.00";
  $("timeline").max = transportDuration();
  $("speed").value = model?.rate || 1;
  $("speed-value").textContent = `${model?.rate || 1}×`;
  $("loop").checked = model?.loop ?? true;
  $("blink").checked = model?.blink ?? true;
  $("expression-note").textContent = gallery()
    ? "เลือกท่าเพื่อดูเต็มช่อง · ปุ่มเล่นและความเร็วใช้กับทุกท่า"
    : model?.clip === "run"
      ? "สีหน้าตอนวิ่งตามแอนิเมชันของตัวละครที่เลือก"
      : "แอนิเมชันและความเร็วปรับแยกแต่ละตัวละคร";
  updateTransport();
}
function updateTransport() {
  const model = selected();
  $("play").textContent = model?.playing ? "Ⅱ" : "▶";
  $("play").setAttribute(
    "aria-label",
    model?.playing ? "หยุดแอนิเมชัน" : "เล่นแอนิเมชัน",
  );
  $("timeline").value = model?.elapsed || 0;
  $("time").textContent = (model?.elapsed || 0).toFixed(2);
}
function selectClip(name) {
  const model = selected();
  if (!model?.character.animations[name]) return;
  Object.assign(model, { clip: name, elapsed: 0, playing: true });
  if (gallery()) setLayout(1);
  refreshInspector();
}
async function bundledData() {
  const json = async (file) => {
    const response = await fetch(`assets/${file}`, { cache: "no-store" });
    if (!response.ok) throw Error("โหลด " + file + " ไม่สำเร็จ");
    return response.json();
  };
  const [geometry, animations, info] = await Promise.all([
    json("model.json"),
    json("animations.json"),
    json("info.json"),
  ]);
  return {
    geometry,
    animations,
    info,
    texture: "assets/texture.png?v=" + Date.now(),
  };
}
$("layout").onchange = (event) => {
  setLayout(
    event.target.value === "poses" ? "poses" : Number(event.target.value),
  );
  refreshInspector();
};
document.querySelectorAll("[data-view]").forEach((button) => {
  button.onclick = () => setAngle(activeView, button.dataset.view);
});
document.querySelectorAll("[data-clip]").forEach((button) => {
  button.onclick = () => selectClip(button.dataset.clip);
});
$("more-clips").onchange = (event) => selectClip(event.target.value);
$("reset-camera").onclick = () => fit(activeView);
$("play").onclick = () => {
  const model = selected();
  if (model) {
    model.playing = !model.playing;
    updateTransport();
  }
};
$("timeline").oninput = (event) => {
  const model = selected();
  if (model) {
    model.elapsed = Number(event.target.value);
    model.playing = false;
    if (gallery())
      for (const view of poseViews)
        view.elapsed =
          (model.elapsed / transportDuration()) * durationOf(model, view.clip);
    updateTransport();
  }
};
$("speed").oninput = (event) => {
  const model = selected();
  if (model) {
    model.rate = Number(event.target.value);
    $("speed-value").textContent = model.rate + "×";
  }
};
for (const id of ["loop", "blink"])
  $(id).onchange = (event) => {
    const model = selected();
    if (model) model[id] = event.target.checked;
  };
$("sync-motion").onclick = () => {
  const source = selected();
  if (!source?.clip) return;
  let count = 0;
  for (const model of models)
    if (model.character.animations[source.clip]) {
      for (const property of [
        "clip",
        "elapsed",
        "playing",
        "rate",
        "loop",
        "blink",
      ])
        model[property] = source[property];
      count++;
    }
  toast(`ใช้ท่ากับ ${count} ตัวละครแล้ว`);
};
$("material").onchange = (event) =>
  models.forEach((m) => m.character.setMaterial(event.target.value));
$("grid").onchange = (event) => {
  grid.visible = ground.visible = event.target.checked;
};
$("auto-rotate").onchange = (event) => {
  for (const view of allViews())
    view.controls.autoRotate = event.target.checked;
};
$("background").onchange = (event) => {
  const light = event.target.value === "light",
    transparent = event.target.value === "transparent";
  document.body.classList.toggle("light", light);
  viewport.style.background = transparent
    ? "repeating-conic-gradient(#29242e 0% 25%,#221e27 0% 50%) 0 0/24px 24px"
    : light
      ? "radial-gradient(ellipse at 50% 35%,#f5f0f7,#dcd7e5)"
      : "";
  for (const model of models)
    model.character.setWireColor(light ? 0x785076 : 0xffb6d7);
};
$("capture").onclick = () => {
  if (!models.length) return;
  render(true);
  const link = document.createElement("a");
  link.download = `model-studio-${$("layout").value}-views.png`;
  link.href = renderer.domElement.toDataURL("image/png");
  link.click();
  render();
  toast("บันทึกภาพช่องที่มองเห็นเป็น PNG แล้ว");
};
$("add-bundled").onclick = () =>
  operation(async () => addModels([await bundledData()]));
$("duplicate-model").onclick = () =>
  operation(async () => {
    const model = selected();
    if (model) await addModels([model.data]);
  });
$("reload").onclick = () =>
  operation(async () => {
    const model = selected();
    if (!model) {
      await addModels([await bundledData()]);
      return;
    }
    const data = model.data.source
      ? (
          await readModelFolders(
            model.data.source.files,
            model.data.source.manifest,
          )
        )[0]
      : await bundledData();
    const replacement = await characterFrom(data);
    dispose(model);
    model.character = replacement;
    model.data = data;
    model.name = data.info?.metadata?.name || model.name;
    if (!replacement.animations[model.clip])
      Object.assign(model, playback(replacement.animations));
    scene.add(replacement.root);
    updatePose(model);
    arrange();
    toast("โหลดตัวละครที่เลือกใหม่แล้ว");
  });
$("open-model").onclick = () => $("model-files").click();
$("model-files").onchange = (event) => {
  const files = [...event.target.files];
  event.target.value = "";
  if (files.length)
    operation(async () => {
      const data = await readModelFolders(files);
      await addModels(data);
      toast(`เพิ่ม ${data.length} ตัวละครแล้ว · ไฟล์อยู่ในเบราว์เซอร์`);
    });
};
function render(capture = false) {
  const rect = viewport.getBoundingClientRect(),
    background = $("background").value,
    bounds = $("view-panes").getBoundingClientRect();
  renderer.setScissorTest(false);
  renderer.setClearColor(
    background === "light" ? 0xe6e0ed : 0x1b1923,
    capture && background !== "transparent" ? 1 : 0,
  );
  renderer.clear();
  renderer.setScissorTest(true);
  for (const view of currentViews())
    if (!view.pane.hidden) {
      const area = view.surface.getBoundingClientRect();
      if (!area.width || !area.height) continue;
      const left = Math.max(area.left, bounds.left),
        right = Math.min(area.right, bounds.right),
        top = Math.max(area.top, bounds.top),
        bottom = Math.min(area.bottom, bounds.bottom);
      if (right <= left || bottom <= top) continue;
      renderer.setViewport(
        area.left - rect.left,
        rect.bottom - area.bottom,
        area.width,
        area.height,
      );
      renderer.setScissor(
        left - rect.left,
        rect.bottom - bottom,
        right - left,
        bottom - top,
      );
      for (const model of models)
        model.character.root.visible = shownIn(model, view.selection);
      if (view.clip)
        selected()?.character.update(view.clip, view.elapsed, {
          blink: selected().blink,
        });
      renderer.render(scene, view.camera);
    }
  for (const model of models) {
    model.character.root.visible = model.visible;
    if (gallery()) updatePose(model);
  }
  renderer.setScissorTest(false);
}
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (gallery() && selected())
    for (const view of poseViews) {
      const clock = { ...selected(), clip: view.clip, elapsed: view.elapsed };
      advance(clock, dt);
      view.elapsed = clock.elapsed;
    }
  for (const model of models) {
    advance(
      model,
      dt,
      gallery() && model === selected()
        ? transportDuration()
        : durationOf(model),
    );
    updatePose(model);
  }
  updateTransport();
  for (const view of currentViews())
    if (!view.pane.hidden) view.controls.update();
  render();
  frames++;
  if (now - fpsStart > 1000) {
    $("fps").textContent =
      Math.round((frames * 1000) / (now - fpsStart)) + " FPS";
    frames = 0;
    fpsStart = now;
  }
  requestAnimationFrame(frame);
}
window.addEventListener("beforeunload", () => {
  models.forEach(dispose);
  allViews().forEach((v) => v.controls.dispose());
  renderer.dispose();
});
setLayout("poses");
refreshModels();
requestAnimationFrame(frame);
operation(async () => addModels([await bundledData()]));
