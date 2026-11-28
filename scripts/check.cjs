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
assert.equal(by.CustomSkirtLining.parent, "cloth");
assert.equal(by.CustomSkirtLining.cubes.length, 12);
for (const q of by.CustomSkirtLining.cubes) {
  assert(!q.rotation, "Lining should use unrotated pixel-style solids");
  assert(
    q.size.every((n) => n > 0),
    "Lining wall must have positive dimensions",
  );
}
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
  const join = by[`Custom${n.replace(/Leg$/, "")}ThighJoin`];
  assert.equal(join.parent, n, "The hip filler must move with the thigh");
  const [connector] = join.cubes;
  const skin = by[n].cubes.at(-1);
  for (let axis = 0; axis < 3; axis++) {
    assert(
      Math.max(connector.origin[axis], skin.origin[axis]) <
        Math.min(
          connector.origin[axis] + connector.size[axis],
          skin.origin[axis] + skin.size[axis],
        ),
      n + " hip filler misses the thigh",
    );
    assert(
      connector.origin[axis] < by[n].pivot[axis] &&
        by[n].pivot[axis] < connector.origin[axis] + connector.size[axis],
      n + " hip filler misses its hinge",
    );
  }
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
function inverseRotate(v, r, p) {
  let [x, y, z] = v.map((q, i) => q - p[i]);
  for (const a of [2, 1, 0]) {
    const t = (r[a] * Math.PI) / 180,
      c = Math.cos(t),
      s = Math.sin(t);
    if (a === 0) [y, z] = [y * c - z * s, y * s + z * c];
    if (a === 1) [x, z] = [x * c + z * s, -x * s + z * c];
    if (a === 2) [x, y] = [x * c - y * s, x * s + y * c];
  }
  return [x + p[0], y + p[1], z + p[2]];
}
function leaks(b, r, clip, time) {
  let hits = 0;
  for (const q of b.cubes.filter((q) => !q.rotation))
    for (let ix = 0; ix <= 4; ix++)
      for (let iy = 0; iy <= 8; iy++)
        for (let iz = 0; iz <= 4; iz++) {
          let v = rotate(
            [
              q.origin[0] + (q.size[0] * ix) / 4,
              q.origin[1] + (q.size[1] * iy) / 8,
              q.origin[2] + (q.size[2] * iz) / 4,
            ],
            r,
            b.pivot,
          );
          v = inverseRotate(
            v,
            keyframeValue(clip.bones.cloth?.rotation, time, [0, 0, 0]),
            by.cloth.pivot,
          );
          if (v[1] < 16.5 || v[1] > 21) continue;
          const frames = new Map();
          for (const wall of by.CustomSkirtLining.cubes) {
            if (
              v[1] < wall.origin[1] - 1e-6 ||
              v[1] > wall.origin[1] + wall.size[1] + 1e-6
            )
              continue;
            const key = wall.origin[1];
            if (!frames.has(key)) frames.set(key, []);
            frames.get(key).push(wall);
          }
          const covered = [...frames.values()].some((walls) => {
            const left = Math.min(...walls.map((q) => q.origin[0])) + 0.18;
            const right =
              Math.max(...walls.map((q) => q.origin[0] + q.size[0])) - 0.18;
            const front = Math.min(...walls.map((q) => q.origin[2])) + 0.18;
            const back =
              Math.max(...walls.map((q) => q.origin[2] + q.size[2])) - 0.18;
            return (
              v[0] >= left && v[0] <= right && v[2] >= front && v[2] <= back
            );
          });
          if (!covered) hits++;
        }
  return hits;
}
let sampled = 0,
  before = 0,
  after = 0;
for (const anim of ["walk", "run"])
  for (const n of ["LeftLeg", "RightLeg"])
    for (const [time, entry] of Object.entries(
      animations[anim].bones[n].rotation,
    )) {
      const r = Array.isArray(entry) ? entry : entry.post;
      if (!r || !r.every(Number.isFinite)) continue;
      before += leaks(old[n], r, animations[anim], Number(time));
      after += leaks(by[n], r, animations[anim], Number(time));
      sampled++;
    }
assert(before > 0, "Regression example must reproduce waist clipping");
assert.equal(after, 0, "Upper thighs escape the skirt lining during walk/run");
// Reproduce sprint opening using the original clip, then compare the assembled
// skirt's vertices to their hip-relative rest positions across its keyframes.
const originalAnimations = JSON.parse(
  fs.readFileSync(
    path.join(repo, "vendor/winefox-jk/animations/main.animation.json"),
  ),
).animations;
const originalRun = originalAnimations.run.bones;
function keyframeValue(channel, time, fallback) {
  if (channel === undefined) return fallback;
  if (typeof channel === "number" || Array.isArray(channel)) return channel;
  const keys = Object.entries(channel)
    .map(([key, value]) => [Number(key), value.post || value])
    .sort((a, b) => a[0] - b[0]);
  if (time <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++)
    if (time <= keys[i][0]) {
      const [start, a] = keys[i - 1],
        [end, b] = keys[i],
        t = (time - start) / (end - start);
      return typeof a === "number"
        ? a + (b - a) * t
        : a.map((n, axis) => n + (b[axis] - n) * t);
    }
  return keys.at(-1)[1];
}
const skirtBones = bones.filter((b) => {
  for (let p = b; p; p = by[p.parent]) if (p.name === "cloth") return true;
  return false;
});
function skirtVertex(v, bone, pose, time) {
  for (let b = bone; b.name !== "DownBody"; b = by[b.parent]) {
    const channels = pose[b.name] || {};
    const scale = keyframeValue(channels.scale, time, [1, 1, 1]);
    const rotation = keyframeValue(channels.rotation, time, [0, 0, 0]);
    const position = keyframeValue(channels.position, time, [0, 0, 0]);
    v = v.map(
      (n, i) =>
        b.pivot[i] +
        (n - b.pivot[i]) * (typeof scale === "number" ? scale : scale[i]),
    );
    v = rotate(v, rotation, b.pivot).map((n, i) => n + position[i]);
  }
  return v;
}
let runSkirtBefore = 0,
  runSkirtAfter = 0,
  runPanelSeparation = 0;
for (const time of Object.keys(animations.run.bones.cloth.rotation).map(Number))
  for (const bone of skirtBones)
    for (const q of bone.cubes || []) {
      for (const x of [0, 1])
        for (const y of [0, 1])
          for (const z of [0, 1]) {
            let rest = q.origin.map((n, i) => n + q.size[i] * [x, y, z][i]);
            if (q.rotation) rest = rotate(rest, q.rotation, q.pivot);
            const oldPose = skirtVertex(rest, bone, originalRun, time);
            const newPose = skirtVertex(rest, bone, animations.run.bones, time);
            const relativePose = inverseRotate(
              newPose,
              keyframeValue(
                animations.run.bones.cloth.rotation,
                time,
                [0, 0, 0],
              ),
              by.cloth.pivot,
            );
            runSkirtBefore = Math.max(
              runSkirtBefore,
              Math.hypot(...oldPose.map((n, i) => n - rest[i])),
            );
            runSkirtAfter = Math.max(
              runSkirtAfter,
              Math.hypot(...newPose.map((n, i) => n - rest[i])),
            );
            runPanelSeparation = Math.max(
              runPanelSeparation,
              Math.hypot(...relativePose.map((n, i) => n - rest[i])),
            );
          }
    }
assert(
  runSkirtBefore > 1,
  "Original sprint must reproduce independent skirt opening",
);
assert(
  runSkirtAfter > 0.05 && runSkirtAfter < 0.5,
  "Sprint skirt needs a gentle, visible sway",
);
assert(
  runPanelSeparation < 1e-8,
  "Skirt panels and lining must share the same movement",
);
for (const value of Object.values(animations.run.bones.cloth.rotation))
  assert(
    value.every((n) => Math.abs(n) <= 2),
    "Skirt sway must stay within two degrees",
  );
for (const n of ["Root", "Head", "LeftArm", "RightArm", "LeftLeg", "RightLeg"])
  assert.deepEqual(
    animations.run.bones[n],
    originalRun[n],
    n + " sprint motion changed",
  );
console.log(
  JSON.stringify({ runSkirtBefore, runSkirtAfter, runPanelSeparation }),
);
// Reproduce the imported crouch flap and reject any independently moving pleat.
const poseChecks = {};
for (const clip of [
  "jump",
  "sneak",
  "sneaking",
  "sit",
  "boat",
  "ride",
  "ride_pig",
]) {
  const pose = animations[clip].bones;
  const channel = pose.cloth.rotation;
  const times = Array.isArray(channel) ? [0] : Object.keys(channel).map(Number);
  let maxY = -Infinity,
    originalMaxY = -Infinity,
    separation = 0;
  for (const time of times)
    for (const bone of skirtBones)
      for (const q of bone.cubes || [])
        for (const x of [0, 1])
          for (const y of [0, 1])
            for (const z of [0, 1]) {
              let rest = q.origin.map((n, i) => n + q.size[i] * [x, y, z][i]);
              if (q.rotation) rest = rotate(rest, q.rotation, q.pivot);
              const moved = skirtVertex(rest, bone, pose, time);
              const position = keyframeValue(
                pose.cloth.position,
                time,
                [0, 0, 0],
              );
              const scale = keyframeValue(pose.cloth.scale, time, [1, 1, 1]);
              const relative = inverseRotate(
                moved.map((n, axis) => n - position[axis]),
                keyframeValue(channel, time, [0, 0, 0]),
                by.cloth.pivot,
              ).map(
                (n, axis) =>
                  by.cloth.pivot[axis] +
                  (n - by.cloth.pivot[axis]) / scale[axis],
              );
              maxY = Math.max(maxY, moved[1]);
              originalMaxY = Math.max(
                originalMaxY,
                skirtVertex(
                  rest,
                  bone,
                  originalAnimations[clip].bones,
                  time,
                )[1],
              );
              separation = Math.max(
                separation,
                Math.hypot(...relative.map((n, i) => n - rest[i])),
              );
            }
  assert(separation < 1e-8, clip + " separates pleats from their lining");
  assert(maxY < 22, clip + " flips a skirt panel above the waist");
  if (clip === "sneaking")
    assert(originalMaxY > 23, "Original crouch must reproduce the upward flap");
  for (const n of [
    "Root",
    "Head",
    "UpBody",
    "DownBody",
    "LeftArm",
    "RightArm",
    "LeftLeg",
    "RightLeg",
  ]) {
    if (clip === "jump" && n.endsWith("Arm")) continue;
    assert.deepEqual(
      pose[n],
      originalAnimations[clip].bones[n],
      clip + " changed " + n,
    );
  }
  poseChecks[clip] = { maxY, originalMaxY, separation };
}
console.log(JSON.stringify({ skirtPoses: poseChecks }));
// Sample the rendered UV regions: sleeves retain navy hue with deeper folds;
// lining walls carry multiple broad pixel shades rather than one flat texel.
const atlas = require("./png.cjs").read(
  path.join(root, "textures/pink_bun.png"),
);
function faceColors(face) {
  const colors = [];
  for (let y = Math.floor(face.uv[1]); y < face.uv[1] + face.uv_size[1]; y++)
    for (
      let x = Math.floor(face.uv[0]);
      x < face.uv[0] + face.uv_size[0];
      x++
    ) {
      const i = (y * atlas.width + x) * 4;
      if (atlas.pixels[i + 3] > 128)
        colors.push([...atlas.pixels.subarray(i, i + 3)]);
    }
  return colors;
}
assert.equal(by.xiao.cubes.length, 1, "Open mouth must use one cutout");
assert(
  bones.filter((bone) => bone.parent === "xiao").every((bone) => !bone.cubes?.length),
  "Old mouth corners must stay hidden when the open mouth moves forward",
);
const jumpMouth = by.xiao.cubes[0];
assert(jumpMouth.size[0] < 1 && jumpMouth.size[2] < 0.1);
const { north: mouthFront, ...mouthSides } = jumpMouth.uv;
const mouthPixels = faceColors(mouthFront);
const [mouthWidth, mouthHeight] = mouthFront.uv_size;
assert(mouthPixels.length > 0 && mouthPixels.length < mouthWidth * mouthHeight);
for (const side of Object.values(mouthSides))
  assert.equal(faceColors(side).length, 0);
assert.deepEqual(
  animations.jump.bones.xiao,
  originalAnimations.jump.bones.xiao,
);

const sleeveColors = faceColors(by.LeftArm.cubes[0].uv.north);
const sleeveLight = sleeveColors.map(
  ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b,
);
assert(
  sleeveColors.every(([r, g, b]) => b > r && b > g),
  "Sleeves must keep their navy hue",
);
assert(
  Math.min(...sleeveLight) < Math.max(...sleeveLight) * 0.8,
  "Sleeve folds lost their contrast",
);
for (const q of by.CustomSkirtLining.cubes) {
  const colors = faceColors(q.uv.north);
  assert(
    new Set(colors.map((c) => c.join(","))).size >= 3,
    "Lining lost its pixel pleat shades",
  );
}
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

const expectedModelName = JSON.parse(
  fs.readFileSync(path.join(repo, "model.config.json"), "utf8"),
).name;
const { textureCoverage } = require("../src/texture-coverage.cjs");
const readModel = (folder, file) =>
  JSON.parse(fs.readFileSync(path.join(folder, file), "utf8"));
for (const [suffix, outfitTip] of [
  ["", "School Uniform"],
  ["_white", "White Shirt"],
]) {
  const name = "pink_bun_winefox" + suffix;
  const originalModel = path.join(repo, "dist", name);
  const squareModel = originalModel + "_square_eyes";
  const baseInfo = readModel(originalModel, "ysm.json");
  const squareInfo = readModel(squareModel, "ysm.json");
  const vendor = path.join(repo, "vendor", "winefox-jk");
  const { license } = readModel(vendor, "ysm.json").metadata;
  for (const [folder, tips] of [
    [originalModel, outfitTip],
    [squareModel, `${outfitTip} · Square Eyes`],
  ]) {
    const info = readModel(folder, "ysm.json");
    assert.deepEqual(info.metadata, {
      name: expectedModelName,
      tips,
      license,
    });
    assert.equal(info.properties.extra_animation.extra0, "Toggle Ribbon");
    assert(!/\p{Script=Thai}|\p{Script=Han}/u.test(JSON.stringify(info.properties)));
    for (const locale of fs.readdirSync(path.join(folder, "lang"))) {
      if (!locale.endsWith(".json")) continue;
      const file = `lang/${locale}`;
      const translations = Object.entries(readModel(vendor, file)).filter(
        ([key]) =>
          !key.startsWith("metadata.") &&
          key !== "properties.extra_animation.extra0",
      );
      assert.deepEqual(readModel(folder, file), Object.fromEntries(translations));
    }
    for (const file of ["ATTRIBUTION.md", "LICENSE"])
      assert(
        fs.readFileSync(path.join(folder, file)).equals(fs.readFileSync(path.join(repo, file))),
      );
  }
  assert.deepEqual(squareInfo.files, baseInfo.files);
  assert.deepEqual(squareInfo.properties, baseInfo.properties);
  const { model, animation, texture } = squareInfo.files.player;
  for (const file of [model.arm, animation.extra])
    assert(
      fs.readFileSync(path.join(squareModel, file)).equals(
        fs.readFileSync(path.join(originalModel, file)),
      ),
      `${name}: Square Eyes changed ${file}`,
    );
  const expectedMain = readModel(originalModel, animation.main);
  for (const side of ["Left", "Right"]) {
    const blink = expectedMain.animations.pre_parallel3.bones[side + "Eyelid"];
    for (const keyframe of Object.values(blink.scale)) delete keyframe.lerp_mode;
  }
  const variantMain = readModel(squareModel, animation.main);
  const boneNames = new Set(
    readModel(squareModel, model.main)["minecraft:geometry"][0].bones.map(({ name }) => name),
  );
  assert.deepEqual(
    variantMain.animations.elytra_fly.bones.Root,
    expectedMain.animations.elytra_fly.bones.Root,
    "Elytra flight must preserve its native root transform",
  );
  for (const clip of ["elytra_fly", "fly"]) {
    const pose = variantMain.animations[clip];
    assert.notDeepEqual(pose, expectedMain.animations[clip]);
    assert(pose.loop === true && pose.animation_length > 0);
    for (const bone of Object.keys(pose.bones))
      assert(boneNames.has(bone), `${name}: flight pose targets unknown bone ${bone}`);
    expectedMain.animations[clip] = pose;
  }
  assert.deepEqual(variantMain, expectedMain);

  const geometry = (folder) =>
    readModel(folder, model.main)["minecraft:geometry"][0];
  const baseGeometry = geometry(originalModel);
  const squareGeometry = geometry(squareModel);
  assert.notEqual(
    squareGeometry.description.identifier,
    baseGeometry.description.identifier,
  );
  const hierarchy = ({ bones }) => bones.map(({ name, parent }) => [name, parent]);
  const glowBones = squareGeometry.bones.filter(({ name }) => name.startsWith("ysmGlow"));
  const normalBones = squareGeometry.bones.filter((bone) => !glowBones.includes(bone));
  assert.deepEqual(hierarchy({ bones: normalBones }), hierarchy(baseGeometry));
  const faceBone =
    /^(?:(?:Left|Right)(?:Eyelid|EyelidBase|Eyebrow|EyePublic|EyeDot)|CustomRunIris(?:Left|Right)|weixiao)$/;
  assert.deepEqual(
    normalBones.filter(({ name }) => !faceBone.test(name)),
    baseGeometry.bones.filter(({ name }) => !faceBone.test(name)),
    `${name}: Square Eyes changed other body parts`,
  );
  for (const irisName of [
    "LeftEyePublic",
    "RightEyePublic",
    "CustomRunIrisLeft",
    "CustomRunIrisRight",
  ]) {
    const iris = ({ bones }) => bones.find(({ name }) => name === irisName);
    assert.notDeepEqual(iris(squareGeometry), iris(baseGeometry), `${name}: ${irisName}`);
  }

  const png = require("./png.cjs");
  const baseTexture = png.read(path.join(originalModel, texture[0]));
  const squareTexture = png.read(path.join(squareModel, texture[0]));
  const { width, height, pixels } = squareTexture;
  assert.equal(width, baseTexture.width);
  assert.equal(height, baseTexture.height);
  assert(!fs.existsSync(path.join(squareModel, "textures", "skin.png")));
  const coverage = textureCoverage([
    readModel(squareModel, model.main),
    readModel(squareModel, model.arm),
  ], width, height);
  const sameSpan = (y, x, endX) => {
    const start = (y * width + x) * 4;
    const end = (y * width + endX) * 4;
    return pixels
      .subarray(start, end)
      .equals(baseTexture.pixels.subarray(start, end));
  };
  for (let y = 0; y < height; y++) {
    const eyeArt = y >= 352 && y < 400;
    const expressionArt = (y >= 400 && y < 420) || (y >= 424 && y < 444);
    for (let x = 0; x < width; x++) {
      const index = y * width + x;
      const offset = index * 4;
      const actual = pixels.readUInt32LE(offset);
      if (!coverage[index]) {
        if (actual) assert.fail(`${name}: unused texel at ${x},${y}`);
      } else if (!(x >= 1800 && (eyeArt || (expressionArt && x < 1992)))) {
        const expected = baseTexture.pixels.readUInt32LE(offset);
        if (actual !== expected)
          assert.fail(`${name}: changed non-eye texel at ${x},${y}`);
      }
    }
  }
  const extra = readModel(squareModel, animation.extra).animations;
  const wheel = squareInfo.properties.extra_animation_classify.find(
    ({ id }) => id === "faces",
  );
  const clips = Object.keys(wheel.extra_animation);
  assert.equal(clips.length, 8);
  const glowParents = {
    LeftEyePublic: 1,
    RightEyePublic: 1,
    CustomRunIrisLeft: 1,
    CustomRunIrisRight: 1,
  };
  for (const [index, clip] of clips.entries()) {
    const boneName = `CustomExpression${index}`;
    const overlay = squareGeometry.bones.find(({ name }) => name === boneName);
    const {
      uv: [x, y],
      uv_size: [w, h],
    } = overlay.cubes[0].uv.north;
    assert(
      extra[clip]?.bones?.[boneName]?.position?.[2] < 0,
      `${name}: ${clip} wheel clip`,
    );
    assert(
      Array.from({ length: h }, (_, row) => y + row).some(
        (row) => !sameSpan(row, x, x + w),
      ),
      `${name}: ${clip} eye artwork did not change`,
    );
    if (clip !== "face_closed") glowParents[boneName] = clip === "face_wink" ? 1 : 2;
  }
  assert.equal(glowBones.length, Object.keys(glowParents).length);
  for (const [parent, count] of Object.entries(glowParents)) {
    const glow = glowBones.find(({ name }) => name === `ysmGlow${parent}`);
    assert.equal(glow?.parent, parent);
    assert.equal(glow.cubes.length, count);
    for (const { uv } of glow.cubes) {
      const [x, y] = uv.north.uv;
      const [w, h] = uv.north.uv_size;
      let lit = 0;
      for (let row = y; row < y + h; row++)
        for (let col = x; col < x + w; col++)
          lit += +(pixels[(row * width + col) * 4 + 3] > 0);
      assert(lit > 0 && lit < w * h, `${name}: glow must be an iris highlight`);
    }
  }
}

const auntFolder = path.join(repo, "dist", "satou_aunt");
const auntVendor = path.join(repo, "vendor", "winefox-matured");
const auntInfo = readModel(auntFolder, "ysm.json");
const auntSource = readModel(auntVendor, "ysm.json");
assert.deepEqual(auntInfo.metadata, {
  name: "Satou's Aunt",
  tips: "Pink Dress · Lavender Braid",
  license: auntSource.metadata.license,
});
const { model: auntModel, animation: auntAnimation, texture: auntTextures } =
  auntInfo.files.player;
for (const file of [
  ...Object.values(auntModel),
  ...Object.values(auntAnimation),
  ...auntTextures.map((texture) => texture.uv),
  "ATTRIBUTION.md",
  "LICENSE",
]) {
  const entry = fs.statSync(path.join(auntFolder, file));
  assert(
    entry.isFile() && entry.size > 0,
    `Aunt package has an empty or invalid resource: ${file}`,
  );
}
const auntGeometry = readModel(auntFolder, auntModel.main)["minecraft:geometry"][0];
const auntBones = new Map(auntGeometry.bones.map((bone) => [bone.name, bone]));
assert.equal(
  auntBones.get("ElytraLocator")?.parent,
  "Elytra",
  "Aunt's Elytra wing attachment is missing",
);
const auntClips = readModel(auntFolder, auntAnimation.main).animations;
const originalAuntClips = readModel(
  auntVendor,
  auntSource.files.player.animation.main,
).animations;
for (const clip of ["elytra_fly", "fly"]) {
  const pose = auntClips[clip];
  assert(
    pose?.loop === true &&
      Number.isFinite(pose.animation_length) &&
      pose.animation_length > 0,
    `Invalid Aunt flight loop: ${clip}`,
  );
  assert.notDeepEqual(
    pose,
    originalAuntClips[clip],
    `Aunt is using the original flight clip: ${clip}`,
  );
  const bones = Object.keys(pose.bones ?? {});
  assert(bones.length > 0, `Aunt flight clip has no bone tracks: ${clip}`);
  for (const bone of bones)
    assert(auntBones.has(bone), `Aunt ${clip} targets unknown bone ${bone}`);
}
assert.deepEqual(
  auntClips.elytra_fly.bones.Root,
  originalAuntClips.elytra_fly.bones.Root,
  "Aunt's Elytra flight must preserve the native root transform",
);

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
