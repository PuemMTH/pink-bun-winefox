import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "../viewer/lib/three.module.min.js";
import { evaluate, sample, poseFor } from "../viewer/animation.mjs";
import { cubeGeometry, createCharacter } from "../viewer/model.mjs";
import {
  poseClips,
  playback,
  advance,
  shownIn,
  readModelFolders,
} from "../viewer/studio.mjs";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const close = (actual, expected) =>
  assert(Math.abs(actual - expected) < 1e-6, `${actual} != ${expected}`);
close(evaluate("math.sin(90)"), 1);
close(evaluate("math.cos(180)"), -1);
assert.equal(evaluate("ysm.food_level<=6?5:0", { "ysm.food_level": 20 }), 0);
assert.equal(evaluate("ysm.food_level<=6?5:0", { "ysm.food_level": 4 }), 5);
assert.equal(evaluate("math.clamp(-5,0,10)+math.lerp(2,6,0.5)"), 4);
assert.equal(evaluate("1/0"), 0);
assert.equal(evaluate("v.unsupported"), 0);
assert.equal(evaluate("globalThis.process.exit()"), 0);
const keys = {
  0: [0, 0, 0],
  1: { pre: [10, 0, 0], post: [20, 0, 0] },
  2: [30, 0, 0],
};
close(sample(keys, 0.5)[0], 5);
close(sample(keys, 1)[0], 20);
close(sample(keys, 1.5)[0], 25);
close(
  sample(
    { 0: { post: [0, 0, 0], lerp_mode: "catmullrom" }, 1: [10, 0, 0] },
    0.5,
  )[0],
  5,
);
const cube = cubeGeometry(
  {
    origin: [0, 0, 0],
    size: [2, 3, 4],
    uv: { north: { uv: [4, 5], uv_size: [-2, 3] } },
  },
  { texture_width: 16, texture_height: 16 },
  new THREE.Vector3(),
);
close(cube.attributes.position.array[0], -2 / 16);
close(cube.attributes.position.array[1], 3 / 16);
close(cube.attributes.uv.array[0], 2 / 16);
close(cube.attributes.uv.array[1], 5 / 16);
close(cube.attributes.uv.array[2], 4 / 16);
close(cube.attributes.uv.array[3], 5 / 16);
assert.equal(cube.index.count, 6);
cube.dispose();
const inflated = cubeGeometry(
  { origin: [0, 0, 0], size: [2, 3, 4], inflate: 0.5, uv: [0, 0] },
  { texture_width: 32, texture_height: 32 },
  new THREE.Vector3(),
);
inflated.computeBoundingBox();
close(inflated.boundingBox.min.x, -2.5 / 16);
close(inflated.boundingBox.max.y, 3.5 / 16);
assert.equal(inflated.index.count, 36);
inflated.dispose();
const data = JSON.parse(
  fs.readFileSync(path.join(root, "dist/pink_bun_winefox/models/main.json")),
);
const animations = JSON.parse(
  fs.readFileSync(
    path.join(root, "dist/pink_bun_winefox/animations/main.animation.json"),
  ),
);
const character = createCharacter(data, new THREE.Texture(), animations);
const galleryClips = poseClips(animations.animations);
assert.deepEqual(galleryClips.slice(0, 6), [
  "idle",
  "walk",
  "run",
  "jump",
  "sneak",
  "sit",
]);
assert.equal(galleryClips.length, new Set(galleryClips).size);
assert(galleryClips.every((name) => !name.includes("parallel")));
assert.deepEqual(poseClips({ run: {}, custom_pose: {}, parallel: {} }), [
  "run",
  "custom_pose",
]);
assert.equal(character.stats.cubes, 292);
assert.equal(character.stats.triangles, 3504);
character.update("run", 0.2);
assert.equal(character.bones.get("CustomRunIrisLeft").group.scale.x, 1);
assert.equal(character.bones.get("LeftEyelidBase").group.scale.x, 0);
character.update("idle", 0.2);
assert.equal(character.bones.get("CustomRunIrisLeft").group.scale.x, 0);
assert.equal(character.bones.get("LeftEyelidBase").group.scale.x, 1);
const start = poseFor(animations.animations, "walk", 0, { blink: false }).get(
  "LeftLeg",
).rotation;
const mid = poseFor(animations.animations, "walk", 0.5, { blink: false }).get(
  "LeftLeg",
).rotation;
assert.notDeepEqual(start, mid, "Walking must change the actual leg pose");
character.dispose();
// Two folders may have identical relative file names: never mix their assets.
const manifest = {
  files: {
    player: {
      model: { main: "model.json" },
      animation: { main: "motion.json" },
      texture: [{ uv: "skin.png" }],
    },
  },
};
const importedFiles = [];
for (const name of ["Alice", "Bob"]) {
  for (const [fileName, content] of Object.entries({
    "ysm.json": JSON.stringify({ ...manifest, metadata: { name } }),
    "model.json": JSON.stringify(data),
    "motion.json": JSON.stringify(animations),
    "skin.png": name,
  })) {
    const file = new File([content], fileName);
    Object.defineProperty(file, "webkitRelativePath", {
      value: `models/${name}/${fileName}`,
    });
    importedFiles.push(file);
  }
}
const imported = await readModelFolders(importedFiles);
assert.deepEqual(
  imported.map((m) => m.info.metadata.name),
  ["Alice", "Bob"],
);
assert.equal(await imported[0].texture.text(), "Alice");
assert.equal(await imported[1].texture.text(), "Bob");
const reloaded = await readModelFolders(
  importedFiles,
  imported[1].source.manifest,
);
assert.equal(reloaded.length, 1);
assert.equal(reloaded[0].info.metadata.name, "Bob");
await assert.rejects(
  () =>
    readModelFolders(
      importedFiles.filter(
        (f) => !f.webkitRelativePath.endsWith("Bob/skin.png"),
      ),
    ),
  /skin.png/,
);
await assert.rejects(() => readModelFolders([]), /ysm.json/);
const actors = imported.map((m, id) => ({
  id,
  visible: true,
  character: createCharacter(m.geometry, new THREE.Texture(), m.animations),
  ...playback(m.animations.animations),
}));
actors[0].clip = "run";
advance(actors[0], 0.2);
actors[0].character.update(actors[0].clip, actors[0].elapsed);
actors[1].character.update(actors[1].clip, actors[1].elapsed);
assert.equal(
  actors[0].character.bones.get("CustomRunIrisLeft").group.scale.x,
  1,
);
assert.equal(
  actors[1].character.bones.get("CustomRunIrisLeft").group.scale.x,
  0,
);
close(actors[1].elapsed, 0);
actors[0].loop = false;
const galleryClock = { ...actors[0], elapsed: 0 };
advance(galleryClock, 1, 30);
assert.equal(
  galleryClock.playing,
  true,
  "Gallery must continue after a short pose ends",
);
close(galleryClock.elapsed, 1);
advance(actors[0], 100);
assert.equal(actors[0].playing, false);
assert.equal(shownIn(actors[0], "all"), true);
assert.equal(shownIn(actors[0], "0"), true);
assert.equal(shownIn(actors[1], "0"), false);
actors[0].visible = false;
assert.equal(shownIn(actors[0], "0"), false);
actors[0].character.dispose();
actors[1].character.update("walk", 0.5); // Disposing one actor cannot invalidate another.
assert.equal(actors[1].character.stats.cubes, 292);
actors[1].character.dispose();
console.log(
  "Viewer checks passed: Molang, keyframes, geometry/UVs, multi-folder import, independent actors/playback, per-view visibility and sprint face reset.",
);
