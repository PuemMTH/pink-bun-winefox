import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as THREE from "../viewer/lib/three.module.min.js";
import { evaluate, sample, poseFor } from "../viewer/animation.mjs";
import { cubeGeometry, createCharacter } from "../viewer/model.mjs";
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
console.log(
  "Viewer checks passed: Molang subset, keyframe pre/post, Catmull-Rom, reflected geometry, signed UVs, inflate, walk motion and sprint face reset.",
);
