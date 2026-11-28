import * as THREE from "./lib/three.module.min.js";
import {
  cameraDirections,
  characterFromData,
  createStage,
} from "./rendering.mjs";

const frameSize = 512;
const closeups = {
  // Camera centers as fractions of the neutral model's height.
  bust: [0, 0.83, 0.47],
  detail_front: [0, 0.6, 0.44],
  detail_cuff: [-0.18, 0.49, 0.34],
  detail_hem: [0, 0.4, 0.51],
  detail_back: [0, 0.64, 0.58],
};
const framingFor = (job) => closeups[job.state] || closeups[job.referenceView];
const isBust = (job) => framingFor(job) === closeups.bust;
const cameraKey = (job, outfit) => {
  const group = isBust(job) ? outfit.replace(/^(before|after)-|-(before|after|original|square)$/g, "") : "";
  return `${group}/${job.state}/${job.view}/${job.referenceView}`;
};

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw Error(await response.text());
  return response;
}

async function exportFrames() {
  const plan = await (await request("/plan")).json();
  const { scene, renderer, grid, ground } = createStage();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 200);
  renderer.setSize(frameSize, frameSize);
  const lights = scene.children.filter((object) => object.isLight);
  const daytimeIntensity = lights.map((light) => light.intensity);
  grid.visible = false;
  const canvas = renderer.domElement;
  document.body.append(canvas);
  const characters = new Map();
  const bounds = new Map();
  const faces = new Map();
  const update = (character, job, frame) =>
    character.update(job.clip, frame.time, {
      blink: job.blink ?? false,
      variables: frame.variables,
    });
  try {
    // Pair matching shots under the same camera, even when an outfit or an
    // animation phase extends further than the other one.
    for (const [outfit, jobs] of Object.entries(plan)) {
      const data = await (await request("/model/" + outfit)).json();
      const character = await characterFromData(data);
      characters.set(outfit, character);
      for (const job of jobs) {
        const key = cameraKey(job, outfit);
        if (!bounds.has(key)) bounds.set(key, new THREE.Box3());
        const box = bounds.get(key);
        for (const frame of job.frames) {
          update(character, job, frame);
          box.expandByObject(character.root);
          if (isBust(job)) {
            const head = character.bones.get("Head")?.group;
            const faceMeshes = head?.children.filter((child) => child.isMesh) || [];
            if (!faceMeshes.length) continue;
            if (!faces.has(key)) faces.set(key, new THREE.Box3());
            const faceBox = faces.get(key);
            for (const mesh of faceMeshes) faceBox.expandByObject(mesh);
          }
        }
      }
    }
    for (const [outfit, jobs] of Object.entries(plan)) {
      const character = characters.get(outfit);
      scene.add(character.root);
      try {
        for (const job of jobs) {
          const night = job.lighting === "night";
          renderer.setClearColor(night ? 0x191625 : 0xe6e0ed, 1);
          lights.forEach((light, index) => {
            light.intensity = daytimeIntensity[index] * (night ? 0.19 : 1);
          });
          const key = cameraKey(job, outfit);
          const box = bounds.get(key);
          const face = faces.get(key);
          const cameraBox = face || box;
          const target = cameraBox.getCenter(new THREE.Vector3());
          const extent = cameraBox.getSize(new THREE.Vector3());
          const closeup = framingFor(job);
          if (face) {
            target.y -= 0.15 * extent.y;
          } else if (closeup) {
            const [x, y] = closeup;
            target.set(
              target.x + x * extent.y,
              box.min.y + y * extent.y,
              target.z,
            );
          }
          const vertical = job.view === "top" || job.view === "bottom";
          // Point screen-up towards the model's front at both poles.
          camera.up.set(0, vertical ? 0 : 1, vertical ? -1 : 0);
          const direction = vertical
            ? [0, job.view === "top" ? 5 : -5, 0]
            : cameraDirections[job.view];
          camera.position.copy(target).add(new THREE.Vector3(...direction));
          camera.lookAt(target);
          camera.updateMatrixWorld(true);
          const projected = cameraBox
            .clone()
            .applyMatrix4(camera.matrixWorldInverse)
            .getSize(new THREE.Vector3());
          const projectedSpan = Math.max(projected.x, projected.y);
          const span = face
            ? projectedSpan * 1.8
            : closeup ? closeup[2] * extent.y : projectedSpan * 1.15;
          Object.assign(camera, {
            left: -span / 2,
            right: span / 2,
            bottom: -span / 2,
            top: span / 2,
          });
          camera.updateProjectionMatrix();
          // A Minecraft ground plane would cut through model-only swim/flight clips.
          ground.visible = !vertical && !closeup && box.min.y > -0.08;
          for (const frame of job.frames) {
            update(character, job, frame);
            renderer.render(scene, camera);
            const png = await new Promise((resolve) =>
              canvas.toBlob(resolve, "image/png"),
            );
            if (!png) throw Error("Could not encode " + frame.file);
            await request("/capture/" + frame.file, {
              method: "POST",
              body: png,
            });
          }
        }
      } finally {
        scene.remove(character.root);
      }
    }
  } finally {
    for (const character of characters.values()) character.dispose();
    renderer.dispose();
  }
  await request("/done", { method: "POST" });
}

exportFrames().catch(async (error) => {
  document.body.textContent = error.message;
  await fetch("/error", { method: "POST", body: error.stack || error.message });
});
