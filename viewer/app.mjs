import * as THREE from "three";
import { OrbitControls } from "./lib/OrbitControls.js";
import {
  cameraDirections,
  characterFromData,
  createStage,
} from "./rendering.mjs";
import { photoPoseLabels, photoClips, isPhotoPose } from "./photo-poses.mjs";
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
  idle: "Idle",
  walk: "Walk",
  run: "Run",
  jump: "Jump",
  sneak: "Crouch Walk",
  sit: "Sit",
  sneaking: "Crouch Idle",
  sleep: "Sleep",
  swim: "Swim",
  swim_stand: "Tread Water",
  fly: "Creative Flight",
  elytra_fly: "Elytra Glide",
  climb: "Crawl",
  climbing: "Crawl Idle",
  ride: "Ride",
  ride_pig: "Ride Pig",
  boat: "Boat",
  death: "Fall",
  attacked: "Hit Reaction",
  hover_fadeout: "Hover Start",
  hover: "Hover",
  focus: "Focus",
  use_mainhand: "Use Main Hand",
  use_offhand: "Use Off Hand",
  swing_hand: "Swing Arm",
  ...photoPoseLabels,
};
const angles = {
  front: "Front",
  side: "Side",
  back: "Back",
  three: "Three-quarter",
  top: "Top",
  free: "Free orbit",
};
const models = [],
  views = [],
  poseViews = [];
const allViews = () => [...views, ...poseViews];
const gallery = () => ["poses", "photos"].includes($("layout").value);
const galleryClips = (animations) =>
  $("layout").value === "photos"
    ? photoClips(animations)
    : poseClips(animations);
const galleryTitle = () =>
  $("layout").value === "photos" ? "Photo Poses" : "All Poses";
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
          ...galleryClips(model.character.animations).map((clip) =>
            durationOf(model, clip),
          ),
          1,
        )
      : durationOf(model);
};
const modelDescription = (model) => {
  const tips = model?.data.info?.metadata?.tips;
  return typeof tips === "string" ? tips.trim() : "";
};
const modelLabel = (model) => {
  const description = modelDescription(model).split("\n", 1)[0];
  const variant =
    description && description.length <= 40 ? ` · ${description}` : "";
  return `${model.name}${variant} #${model.id}`;
};
const viewport = $("viewport");
const { scene, renderer, ground, grid } = createStage();
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.autoClear = false;
renderer.domElement.setAttribute("aria-label", "Multi-view 3D model preview");
viewport.prepend(renderer.domElement);

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
  for (const id of [
    "open-model",
    "add-bundled",
    "add-white",
    "add-aunt",
    "duplicate-model",
    "reload",
  ])
    $(id).disabled = true;
  try {
    await action();
  } catch (error) {
    toast(error.message);
  } finally {
    busy = false;
    $("loading").hidden = true;
    for (const id of ["open-model", "add-bundled", "add-white", "add-aunt", "reload"])
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
    : `View ${views.indexOf(view) + 1}`;
}
function setAngle(view, angle) {
  view.angle = angle;
  view.angleSelect.value = angle;
  if (angle !== "free") {
    view.camera.position
      .copy(view.controls.target)
      .add(new THREE.Vector3(...cameraDirections[angle]));
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
    view.modelSelect.replaceChildren(new Option("All models", "all"));
    for (const model of models)
      view.modelSelect.add(new Option(modelLabel(model), String(model.id)));
    view.modelSelect.value = view.selection;
  }
}
function setLayout(count) {
  const poses = ["poses", "photos"].includes(count);
  $("layout").value = String(count);
  const list = poses ? poseViews : views;
  const model = selected();
  const clips = poses && model ? galleryClips(model.character.animations) : [];
  if (poses) count = clips.length;
  // Preserve cameras and model assignments when reducing/re-expanding the layout.
  const previousCount = list.length;
  while (list.length < count) {
    const index = list.length,
      pane = document.createElement("section");
    pane.className = "view-pane";
    pane.setAttribute(
      "aria-label",
      poses ? `Pose ${clips[index]}` : `View ${index + 1}`,
    );
    const header = document.createElement("div");
    header.className = "pane-header";
    const number = document.createElement("span");
    number.className = "pane-number";
    number.textContent = `VIEW ${index + 1}`;
    const modelSelect = document.createElement("select");
    modelSelect.setAttribute("aria-label", `Model in view ${index + 1}`);
    const angleSelect = document.createElement("select");
    angleSelect.setAttribute("aria-label", `Camera for view ${index + 1}`);
    for (const [value, label] of Object.entries(angles))
      angleSelect.add(new Option(label, value));
    header.append(number, modelSelect, angleSelect);
    const surface = document.createElement("div");
    surface.className = "pane-surface";
    surface.tabIndex = 0;
    surface.setAttribute("aria-label", `Orbit and zoom in view ${index + 1}`);
    if (poses) surface.setAttribute("aria-label", `Orbit pose ${clips[index]}`);
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
      layerTime: 0,
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
      if (view.clip !== clips[index]) view.elapsed = view.layerTime = 0;
      view.clip = clips[index];
      view.selection = String(model.id);
      view.modelSelect.hidden = true;
      view.title.textContent = labels[view.clip] || view.clip;
      view.pane.setAttribute("aria-label", `Pose ${view.title.textContent}`);
    });
  $("view-panes").dataset.layout = poses ? "poses" : count;
  $("navigation-hint").textContent = poses
    ? "Scroll to see every pose · Drag to orbit"
    : "Drag to orbit · Scroll to zoom · Right-drag to pan";
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
  const character = await characterFromData(data);
  character.setMaterial($("material").value);
  character.setWireColor(
    $("background").value === "light" ? 0x785076 : 0xffb6d7,
  );
  return character;
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
  model.character.update(model.clip, time, {
    blink: model.blink,
    layerTime: model.layerTime,
  });
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
      ? `${models.length} models`
      : models[0]?.name || "Model Studio";
  for (const model of models) {
    const row = document.createElement("div");
    row.className = "model-row";
    row.classList.toggle("selected", model.id === activeId);
    const show = document.createElement("input");
    show.type = "checkbox";
    show.checked = model.visible;
    show.setAttribute("aria-label", `Show ${modelLabel(model)}`);
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
    remove.setAttribute("aria-label", `Remove ${modelLabel(model)} from the scene`);
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
  if (
    $("layout").value === "photos" &&
    !photoClips(selected()?.character.animations || {}).length
  )
    setLayout(1);
  else if (gallery()) setLayout($("layout").value);
  refreshInspector();
}
function refreshInspector() {
  const model = selected(),
    animations = model?.character.animations || {};
  $("model-title").textContent = model?.name || "No model selected";
  $("model-detail").textContent =
    modelDescription(model) ||
    (model ? "Imported model" : "Add a model to start");
  $("model-avatar").hidden = !model?.data.bundle || model.data.bundle === "assets/aunt";
  $("model-credits").href = (model?.data.bundle || "assets") + "/ATTRIBUTION.md";
  if (!$("model-avatar").hidden) {
    const avatar = $("model-avatar").querySelector("img");
    avatar.src = model.data.bundle + "/preview.png";
    avatar.alt = model.name;
  }
  for (const id of ["bones", "cubes", "triangles"])
    $(id).textContent = model?.character.stats[id].toLocaleString() || "—";
  $("more-clips").replaceChildren(new Option("Choose an animation", ""));
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
  $("show-photo-poses").disabled = !photoClips(animations).length;
  $("layout").querySelector('option[value="photos"]').disabled =
    !photoClips(animations).length;
  $("clip-tag").textContent =
    gallery() && model
      ? `${galleryClips(animations).length} poses`
      : isPhotoPose(model?.clip)
        ? "PHOTO"
        : model?.clip?.replaceAll("_", " ").toUpperCase() || "—";
  $("clip-name").textContent = gallery()
    ? galleryTitle()
    : labels[model?.clip] || model?.clip || "No animation";
  $("more-clips").value = gallery() ? "" : model?.clip || "";
  $("duration").textContent = model ? transportDuration().toFixed(2) : "0.00";
  $("timeline").max = transportDuration();
  $("speed").value = model?.rate || 1;
  $("speed-value").textContent = `${model?.rate || 1}×`;
  $("loop").checked = model?.loop ?? true;
  $("blink").checked = model?.blink ?? true;
  $("expression-note").textContent = gallery()
    ? "Select a pose to fill the view. Photo poses hold still."
    : isPhotoPose(model?.clip)
      ? "Orbit the camera and save this pose as a PNG."
      : model?.clip === "run"
        ? "The selected model supplies the running expression."
        : "Each model has its own animation and playback speed.";
  updateTransport();
}
function updateTransport() {
  const model = selected();
  $("play").textContent = model?.playing ? "Ⅱ" : "▶";
  $("play").setAttribute(
    "aria-label",
    model?.playing ? "Pause animation" : "Play animation",
  );
  $("timeline").value = model?.elapsed || 0;
  $("time").textContent = (model?.elapsed || 0).toFixed(2);
}
function selectClip(name) {
  const model = selected();
  if (!model?.character.animations[name]) return;
  Object.assign(model, { clip: name, elapsed: 0, layerTime: 0, playing: !isPhotoPose(name) });
  updatePose(model);
  if (gallery()) setLayout(1);
  currentViews()
    .filter((view) => !view.pane.hidden)
    .forEach(fit);
  refreshInspector();
}
async function bundledData(bundle = "assets") {
  const json = async (file) => {
    const response = await fetch(`${bundle}/${file}`, { cache: "no-store" });
    if (!response.ok) throw Error(`Could not load ${bundle}/${file}`);
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
    bundle,
    texture: bundle + "/texture.png?v=" + Date.now(),
  };
}
$("layout").onchange = (event) => {
  setLayout(
    ["poses", "photos"].includes(event.target.value)
      ? event.target.value
      : Number(event.target.value),
  );
  $("view-panes").scrollTop = 0;
  refreshInspector();
};
document.querySelectorAll("[data-view]").forEach((button) => {
  button.onclick = () => setAngle(activeView, button.dataset.view);
});
for (const [id, label] of Object.entries(photoPoseLabels)) {
  const button = document.createElement("button");
  button.dataset.clip = id;
  button.textContent = label;
  $("photo-pose-buttons").append(button);
}
$("show-photo-poses").onclick = () => {
  setLayout("photos");
  $("view-panes").scrollTop = 0;
  refreshInspector();
};
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
    model.elapsed = model.layerTime = Number(event.target.value);
    model.playing = false;
    if (gallery())
      for (const view of poseViews)
        view.elapsed = view.layerTime =
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
        "layerTime",
        "playing",
        "rate",
        "loop",
        "blink",
      ])
        model[property] = source[property];
      count++;
    }
  toast(`Applied the pose to ${count} models`);
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
  toast("Saved visible views as a PNG");
};
$("add-bundled").onclick = () =>
  operation(async () => addModels([await bundledData()]));
$("add-white").onclick = () =>
  operation(async () => addModels([await bundledData("assets/white")]));
$("add-aunt").onclick = () =>
  operation(async () => addModels([await bundledData("assets/aunt")]));
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
      : await bundledData(model.data.bundle);
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
    toast("Reloaded the selected model");
  });
$("open-model").onclick = () => $("model-files").click();
$("model-files").onchange = (event) => {
  const files = [...event.target.files];
  event.target.value = "";
  if (files.length)
    operation(async () => {
      const data = await readModelFolders(files);
      await addModels(data);
      toast(`Imported ${data.length} models from local files`);
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
          layerTime: view.layerTime,
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
      const clock = {
        ...selected(),
        clip: view.clip,
        elapsed: view.elapsed,
        layerTime: view.layerTime,
      };
      advance(clock, dt);
      view.elapsed = clock.elapsed;
      view.layerTime = clock.layerTime;
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
