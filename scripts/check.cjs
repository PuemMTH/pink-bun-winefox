const fs = require("node:fs"),
  assert = require("node:assert/strict"),
  path = require("node:path");
const repo = path.resolve(__dirname, ".."),
  root = path.join(repo, "dist/pink_bun_winefox");
const g = JSON.parse(fs.readFileSync(path.join(root, "models/main.json"))),
  bones = g["minecraft:geometry"][0].bones,
  by = Object.fromEntries(bones.map((b) => [b.name, b]));
const original = JSON.parse(
  fs.readFileSync(path.join(repo, "vendor/winefox-jk/models/main.json")),
)["minecraft:geometry"][0].bones;
const old = Object.fromEntries(original.map((b) => [b.name, b]));
assert.equal(by.cloth.parent, "DownBody");
assert.equal(by.CustomSkirtLining.parent, "DownBody");
assert.equal(by.CustomSkirtLining.cubes.length, 256);
for (const n of ["LeftLeg", "RightLeg"]) {
  assert.deepEqual(by[n].pivot, old[n].pivot);
  assert.equal(by[n].cubes[0].origin[1], old[n].cubes[0].origin[1]);
  assert(
    Math.abs(
      Math.max(
        ...by[n].cubes
          .filter((q) => !q.rotation)
          .map((q) => q.origin[1] + q.size[1]),
      ) - 16.2,
    ) < 1e-6,
  );
  for (const f of ["north", "south", "east", "west"])
    assert(
      Math.abs(
        by[n].cubes[0].uv[f].uv_size[1] / by[n].cubes[0].size[1] -
          old[n].cubes[0].uv[f].uv_size[1] / old[n].cubes[0].size[1],
      ) < 1e-6,
    );
}
function geometryOnly(b) {
  const q = structuredClone(b);
  for (const c of q.cubes || []) delete c.uv;
  return q;
}
for (const n of ["LeftLowerLeg", "RightLowerLeg", "LeftFoot", "RightFoot"])
  assert.deepEqual(
    geometryOnly(by[n]),
    geometryOnly(old[n]),
    n + " geometry changed",
  );
// Sample the actual walk/run thigh keyframes and reject upper-waist skin outside the liner.
const animations = JSON.parse(
  fs.readFileSync(path.join(root, "animations/main.animation.json")),
).animations;
function rotate(v, r, p) {
  let [x, y, z] = v.map((q, i) => q - p[i]);
  for (let a = 0; a < 3; a++) {
    const t = (-r[a] * Math.PI) / 180,
      c = Math.cos(t),
      s = Math.sin(t);
    if (a === 0) [y, z] = [y * c - z * s, y * s + z * c];
    if (a === 1) [x, z] = [x * c + z * s, -x * s + z * c];
    if (a === 2) [x, y] = [x * c - y * s, x * s + y * c];
  }
  return [x + p[0], y + p[1], z + p[2]];
}
function leaks(b, r) {
  let hits = 0;
  for (const q of b.cubes.filter((q) => !q.rotation))
    for (let ix = 0; ix <= 4; ix++)
      for (let iy = 0; iy <= 8; iy++)
        for (let iz = 0; iz <= 4; iz++) {
          const v = rotate(
            [
              q.origin[0] + (q.size[0] * ix) / 4,
              q.origin[1] + (q.size[1] * iy) / 8,
              q.origin[2] + (q.size[2] * iz) / 4,
            ],
            r,
            b.pivot,
          );
          if (v[1] < 16.5 || v[1] > 21) continue;
          const t = (v[1] - 14.8) / 6.2,
            rx = 4.8 - t * 0.95,
            rz = 3.25 - t * 1.05;
          if ((v[0] / rx) ** 4 + (v[2] / rz) ** 4 > 1.02) hits++;
        }
  return hits;
}
let sampled = 0,
  before = 0,
  after = 0;
for (const anim of ["walk", "run"])
  for (const n of ["LeftLeg", "RightLeg"])
    for (const entry of Object.values(animations[anim].bones[n].rotation)) {
      const r = Array.isArray(entry) ? entry : entry.post;
      if (!r || !r.every(Number.isFinite)) continue;
      before += leaks(old[n], r);
      after += leaks(by[n], r);
      sampled++;
    }
assert(before > 0, "Regression example must reproduce waist clipping");
assert.equal(after, 0, "Upper thighs escape the skirt lining during walk/run");
// Sprint expression uses siblings of the normal iris under the existing blink bones.
for (const side of ["Left", "Right"]) {
  const n = "CustomRunIris" + side;
  assert.equal(by[n].parent, side + "Eyelid");
  assert.equal(animations.run.bones[n].scale, 1);
  assert.equal(animations.run.bones[side + "EyelidBase"].scale, 0);
  for (const clip of ["idle", "walk", "jump", "sneak", "sit"]) {
    assert.equal(animations[clip].bones[n].scale, 0);
    assert.equal(animations[clip].bones[side + "EyelidBase"].scale, 1);
  }
}
assert.equal(animations.run.bones.CustomRunFace.scale, 1);
assert.equal(animations.run.bones.Mouth.scale, 0);
assert.equal(animations.idle.bones.CustomRunFace.scale, 0);
assert.equal(animations.idle.bones.Mouth.scale, 1);
for (const n of ["CustomBunLeft", "CustomBunRight"]) {
  assert.equal(by[n].cubes.length, 14);
  const width =
    Math.max(...by[n].cubes.map((q) => q.origin[0] + q.size[0])) -
    Math.min(...by[n].cubes.map((q) => q.origin[0]));
  const config = JSON.parse(
    fs.readFileSync(path.join(repo, "model.config.json")),
  );
  const crown = old.BaseHair.cubes.filter((q) => q.origin[1] >= 38.9);
  const baseWidth =
    (Math.max(...crown.map((q) => q.origin[0] + q.size[0])) -
      Math.min(...crown.map((q) => q.origin[0]))) *
    0.36;
  assert(
    Math.abs(width - baseWidth * config.bunScale) < 1e-6,
    "Bun scale differs from config",
  );
}
// Test the bow's whole articulated assembly against the front of the added vest.
let bowSamples = 0,
  bowBack = -Infinity;
for (const clip of ["idle", "jump", "sneak", "swim_stand", "sleep"])
  for (const b of bones.filter((b) => /^bow/.test(b.name)))
    for (const q of b.cubes || []) {
      for (const x of [0, 1])
        for (const y of [0, 1])
          for (const z of [0, 1]) {
            let v = q.origin.map((n, i) => n + q.size[i] * [x, y, z][i]);
            if (q.rotation) v = rotate(v, q.rotation, q.pivot);
            for (
              let parent = b;
              parent && /^bow/.test(parent.name);
              parent = by[parent.parent]
            ) {
              const r = animations[clip]?.bones?.[parent.name]?.rotation ||
                parent.rotation || [0, 0, 0];
              if (Array.isArray(r)) v = rotate(v, r, parent.pivot);
            }
            if (Math.abs(v[0]) < 2.3 && v[1] >= 20.5 && v[1] <= 28.7) {
              bowBack = Math.max(bowBack, v[2]);
              bowSamples++;
            }
          }
    }
assert(bowSamples > 0);
assert(bowBack < -2.53, "Bow still intersects the vest: " + bowBack);
console.log(
  JSON.stringify({ bowSamples, bowClearanceFromVest: -2.45 - bowBack }),
);
console.log(
  JSON.stringify({
    sampledPoses: sampled,
    upperWaistEscapesBefore: before,
    upperWaistEscapesAfter: after,
    checks: "passed",
  }),
);
