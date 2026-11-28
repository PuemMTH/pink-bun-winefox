import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "../viewer/lib/three.module.min.js";
import { evaluate, sample, poseFor } from "../viewer/animation.mjs";
import { cubeGeometry, createCharacter } from "../viewer/model.mjs";
import { photoClips, makePhotoAnimations } from "../viewer/photo-poses.mjs";
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
const sourceBeforePhotoPoses = JSON.stringify(animations);
const character = createCharacter(data, new THREE.Texture(), animations);
assert.equal(
  JSON.stringify(animations),
  sourceBeforePhotoPoses,
  "Photo presets must not modify imported animations",
);
assert.equal(photoClips(character.animations).length, 6);
assert.deepEqual(
  makePhotoAnimations(animations.animations, []),
  {},
  "Unsupported rigs must not receive broken poses",
);
const photoHands = [];
for (const clip of photoClips(character.animations)) {
  character.update(clip, 0, { blink: true });
  character.root.updateMatrixWorld(true);
  const hand = character.bones
    .get("LeftHand")
    .group.getWorldPosition(new THREE.Vector3());
  photoHands.push(hand.toArray());
  const box = new THREE.Box3().setFromObject(character.root);
  assert(box.min.y > -0.12, `${clip} must keep the feet above the floor`);
  assert(box.max.y < 4, `${clip} must retain character scale`);
  assert.equal(character.bones.get("CustomRunIrisLeft").group.scale.x, 0);
  assert.equal(character.bones.get("LeftEyelid").group.scale.y, 1);
  character.update(clip, 0.7, { blink: true });
  character.root.updateMatrixWorld(true);
  const later = character.bones
    .get("LeftHand")
    .group.getWorldPosition(new THREE.Vector3());
  assert(later.distanceTo(hand) < 1e-6, `${clip} must hold the photo pose`);
}
assert(
  new THREE.Vector3(...photoHands[0]).distanceTo(
    new THREE.Vector3(...photoHands[2]),
  ) > 0.3,
  "Wave and hip presets must be visibly distinct",
);
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
assert.equal(character.stats.cubes, 299);
assert.equal(character.stats.triangles, 3508);
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
// Exactly zero vertical speed must keep the elbow bent at the jump apex.
const apex = poseFor(animations.animations, "jump", 0.4, {
  variables: { "query.vertical_speed": 0 },
});
for (const side of ["Left", "Right"])
  close(apex.get(side + "ForeArm").rotation[0], -80);
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
assert.equal(actors[1].character.stats.cubes, 299);
actors[1].character.dispose();

// Check the actual YSM wheel clips for both outfits, including face reset.
for (const name of ["pink_bun_winefox", "pink_bun_winefox_white"]) {
  const read = (file) =>
    JSON.parse(fs.readFileSync(path.join(root, "dist", name, file)));
  const info = read("ysm.json");
  const player = info.files.player;
  const extra = read(player.animation.extra).animations;
  const actor = createCharacter(read(player.model.main), new THREE.Texture(), {
    animations: { ...read(player.animation.main).animations, ...extra },
  });
  const faces = Object.keys(extra).filter((id) => id.startsWith("face_"));
  assert.equal(faces.length, 8);
  assert.equal(photoClips(extra).length, 6);
  for (const [i, id] of faces.entries()) {
    const names = faces.map((_, index) => `CustomExpression${index}`);
    const rest = names.map((bone) => actor.bones.get(bone).bindPosition.z);
    actor.update(id, 0.2);
    assert.equal(actor.bones.get("Eyes").group.scale.x, 0);
    for (const [index, bone] of names.entries())
      close(
        actor.bones.get(bone).group.position.z,
        rest[index] - (i === index ? 0.42 / 16 : 0),
      );
    actor.update("idle", 0.2);
    assert.equal(actor.bones.get("Eyes").group.scale.x, 1);
    close(actor.bones.get(names[i]).group.position.z, rest[i]);
  }
  if (name.endsWith("_white")) {
    const meshFor = (boneName) =>
      actor.bones.get(boneName).group.children.find((child) => child.isMesh);
    const chest = meshFor("jk");
    chest.geometry.computeBoundingBox();
    for (const [clip, time, arms] of [
      ["extra7", 4.8917, ["LeftForeArm"]],
      ["studio_photo_shy", 0, ["LeftForeArm", "RightForeArm"]],
    ]) {
      actor.update(clip, time, { blink: false });
      for (const bone of arms) {
        const sleeve = meshFor(bone);
        sleeve.geometry.computeBoundingBox();
        const center = sleeve.geometry.boundingBox.getCenter(
          new THREE.Vector3(),
        );
        chest.worldToLocal(sleeve.localToWorld(center));
        assert(
          !chest.geometry.boundingBox.containsPoint(center),
          `${clip} at ${time}s: ${bone} center penetrates the shirt`,
        );
      }
    }
  }
  actor.dispose();
}
// Test the bundles that the Studio actually opens against the active game builds.
for (const [folder, preset] of [
  ["pink_bun_winefox_square_eyes", ""],
  ["pink_bun_winefox_white_square_eyes", "white"],
  ["satou_aunt", "aunt"],
]) {
  const dist = path.join(root, "dist");
  const read = (directory, file) =>
    JSON.parse(fs.readFileSync(path.join(directory, file), "utf8"));
  const model = path.join(dist, folder);
  const studio = path.join(dist, "viewer/assets", preset);
  const info = read(model, "ysm.json");
  const player = info.files.player;
  const main = read(model, player.animation.main).animations;
  assert.deepEqual(read(studio, "info.json"), info);
  assert.deepEqual(read(studio, "model.json"), read(model, player.model.main));
  assert.deepEqual(read(studio, "animations.json").animations, {
    ...main,
    ...read(model, player.animation.extra).animations,
  });
  const texture = typeof player.texture[0] === "string"
    ? player.texture[0] : player.texture[0].uv;
  assert.deepEqual(
    fs.readFileSync(path.join(studio, "texture.png")),
    fs.readFileSync(path.join(model, texture)),
  );

  const clip = "fly";
  const duration = main[clip].animation_length;
  const state = { clip, elapsed: duration - 0.0001, rate: 1, loop: true, playing: true };
  const rotation = (clock) =>
    poseFor(main, clip, clock.elapsed, { layerTime: clock.layerTime })
      .get(preset === "aunt" ? "bone34" : "Bangs").rotation;
  const before = rotation(state);
  advance(state, 0.0002, duration);
  assert(rotation(state).every((axis, index) => Math.abs(axis - before[index]) < 0.02),
    `Auxiliary animation jumps at the Creative loop boundary in ${folder}`);
  if (preset === "aunt") {
    assert.equal(poseFor(main, "walk", 0.1).get("LeftEyelid").scale[1], 0);
    assert.equal(poseFor(main, "walk", 0.1, { blink: false }).get("LeftEyelid").scale[1], 1);
  }
}
console.log(
  "Viewer checks passed: active model bundles, continuous auxiliary animation, blink toggle, Molang, keyframes, geometry/UVs, multi-folder import, independent actors, six static photo poses, rig compatibility and sprint face reset.",
);
