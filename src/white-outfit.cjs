const assert = require("node:assert/strict");

const faces = ["north", "south", "east", "west", "up", "down"];
const palette = {
  fabric: ["fbf8ff", "f4effb", "ece4f6", "e0d7ee", "d2c5e3", "bdb0d1"],
  collar: ["fffcff", "f7f2fd", "ede5f7", "ddd1eb", "c9bcdb", "bbaecd"],
  button: ["f4e0df", "d9c3c8", "cbb1bd", "bba0b0", "ad91a3", "9c8096"],
  skin: ["feeede", "fce9da", "fbe5d4", "f8dece", "f2d0bf", "ecc4b4"],
};
const colors = Object.fromEntries(
  Object.entries(palette).map(([material, shades]) => [
    material,
    shades.map((shade) => Buffer.from(shade + "ff", "hex")),
  ]),
);

module.exports = function whiteOutfit({ geo, arm, atlas, width, height, animations }) {
  const geometry = geo["minecraft:geometry"][0];
  const bones = geometry.bones;
  const by = Object.fromEntries(bones.map((bone) => [bone.name, bone]));
  assert(width >= 1280 && height >= 256 && atlas.length === width * height * 4);

  // The two color tiles used by the school blazer and vest are free in this variant.
  let u = 769;
  let v = 1;
  let rowHeight = 0;
  function paint(material, face, w, h, pattern) {
    if (u + w + 1 > 1280) {
      v += rowHeight + 2;
      u = 769;
      rowHeight = 0;
    }
    assert(v + h + 1 <= 256, "White outfit UVs exceeded their atlas region");
    const uv = { uv: [u, v], uv_size: [w, h] };
    rowHeight = Math.max(rowHeight, h);
    // Copy edge texels into the two-pixel gutters. Antialiasing can sample
    // just outside a face's UV rectangle at an intersecting seam.
    for (let dy = -1; dy <= h; dy++)
      for (let dx = -1; dx <= w; dx++) {
        const x = Math.min(w - 1, Math.max(0, dx));
        const y = Math.min(h - 1, Math.max(0, dy));
        const across = (x + 0.5) / w;
        const down = (y + 0.5) / h;
        let shade = face === "up" ? 0 : face === "down" ? 4 : 1;
        if (material === "fabric") {
          const edge = across < 0.14 || across > 0.86;
          const diagonal = Math.abs(across - 0.28 - down * 0.36);
          shade += face === "east" || face === "west" ? 1 : 0;
          shade += Number(edge && down > 0.15);
          shade += Number(diagonal < 0.12 && down > 0.36 && down < 0.73);
          shade += Number(pattern === "fold" && down > 0.7 && across < 0.55);
          shade += Number(pattern === "seam" && (x === 0 || x === w - 1));
          shade -= Number(across > 0.4 && across < 0.65 && down < 0.3);
        }
        if (material === "skin") {
          shade += Number(face === "east" || face === "west");
          shade += Number(pattern === "thigh" && down < 0.25);
        }
        const pixel = colors[material][Math.max(0, Math.min(5, shade))];
        pixel.copy(atlas, ((v + dy) * width + u + dx) * 4);
      }
    u += w + 2;
    return uv;
  }
  function box(origin, size, material = "fabric", pattern, rotation) {
    const [x, y, z] = size.map((span) => Math.max(1, Math.round(span * 2)));
    const uv = Object.fromEntries(
      faces.map((face) => {
        const [w, h] =
          face === "up" || face === "down"
            ? [x, z]
            : face === "east" || face === "west"
              ? [z, y]
              : [x, y];
        return [face, paint(material, face, w, h, pattern)];
      }),
    );
    const cube = { origin, size, uv };
    if (rotation) {
      cube.rotation = rotation;
      cube.pivot = origin.map((start, i) => start + size[i] / 2);
    }
    return cube;
  }
  function clearSchoolWear() {
    const hidden = new Set([
      "bow",
      "cloth",
      "jk2",
      "CustomSkirtWaist",
      "CustomLeftThighJoin",
      "CustomRightThighJoin",
    ]);
    for (const bone of bones)
      for (let ancestor = bone; ancestor; ancestor = by[ancestor.parent])
        if (hidden.has(ancestor.name)) {
          delete bone.cubes;
          break;
        }
  }
  clearSchoolWear();

  // The upper shirt and its neck details share the animated chest. A separate
  // hip yoke overlaps it at the waist so sitting and crouching can bend the shirt.
  by.jk.cubes = [
    box([-3.78, 19.85, -2.45], [7.56, 9.7, 4.9]),
    box([-3.4, 29.49, -2.25], [6.8, 0.92, 4.5]),
    box([-1.47, 30.35, -1.44], [2.94, 0.52, 2.89], "skin"),
    box([-1.65, 30.36, 1.26], [3.3, 0.67, 0.39], "collar"),
    box([-1.75, 30.32, -1.5], [0.35, 0.61, 2.77], "collar"),
    box([1.4, 30.32, -1.5], [0.35, 0.61, 2.77], "collar"),
    box([-0.91, 29.63, -2.51], [1.82, 0.78, 0.17], "skin"),
    box([-0.49, 29.35, -2.52], [0.98, 0.29, 0.17], "skin"),
    box([-0.18, 29.22, -2.53], [0.36, 0.14, 0.17], "skin"),
    box([-1.93, 29.58, -2.68], [1.8, 0.93, 0.33], "collar", null, [0, 0, -31]),
    box([0.13, 29.58, -2.68], [1.8, 0.93, 0.33], "collar", null, [0, 0, 31]),
    box([-0.27, 20.05, -2.565], [0.54, 9.08, 0.13], "fabric", "seam"),
  ];
  for (const y of [21.8, 24.1, 26.4, 28.7])
    by.jk.cubes.push(box([-0.18, y, -2.72], [0.36, 0.35, 0.16], "button"));

  bones.push({
    name: "WhiteShirtYoke",
    parent: "DownBody",
    pivot: by.DownBody.pivot.slice(),
    cubes: [
      box([-4.06, 17.65, -2.53], [8.12, 4.1, 5.06]),
      box([-0.28, 17.67, -2.68], [0.56, 3.0, 0.13], "fabric", "seam"),
      box([-0.18, 19.42, -2.83], [0.36, 0.35, 0.17], "button"),
    ],
  });
  // In deep bends the stationary hip yoke sticks out behind the leaning
  // chest. Pull its rear edge toward the waist while keeping overlap with
  // the pieces attached to the thighs.
  for (const clip of ["sneaking", "sit", "boat"]) {
    animations.animations[clip].bones.WhiteShirtYoke = {
      scale: [1, 1, 0.78],
      position: [0, 0, -0.2],
    };
  }

  for (const [side, sign] of [
    ["Left", 1],
    ["Right", -1],
  ]) {
    const thigh = by[side + "Leg"];
    const mirroredX = (x, w) => (sign > 0 ? x : -x - w);

    // The two rounded shirt tails share the thigh pivots. The inner edges
    // overlap in the standing pose and the opaque tops stay under the yoke
    // as the hem follows the legs.
    const tailZ = sign > 0 ? -2.59 : -2.55;
    thigh.cubes = [
      box(
        [mirroredX(-0.31, 4.39), 14.25, tailZ],
        [4.39, 3.53, 4.75],
        "fabric",
        "fold",
      ),
      box([mirroredX(-0.35, 3.68), 13.75, tailZ + 0.11], [3.68, 0.53, 4.55]),
      // Taper back toward the thigh pivot so the hem's top cannot sweep
      // out behind the waist in a deep crouch. The lower box still overlaps
      // the yoke in the standing pose.
      box([mirroredX(-0.28, 4.2), 17.62, -2.23], [4.2, 2.05, 3.55]),
      box(
        [mirroredX(0.38, 3.28), 10.55, -1.74],
        [3.28, 4.48, 3.56],
        "skin",
        "thigh",
      ),
    ];
    // All skin above the hem is contained by the opaque cloth on the same bone.
    const [tail, , , skin] = thigh.cubes;
    for (const axis of [0, 2]) {
      assert(skin.origin[axis] > tail.origin[axis]);
      assert(
        skin.origin[axis] + skin.size[axis] <
          tail.origin[axis] + tail.size[axis],
      );
    }
    assert(skin.origin[1] + skin.size[1] < tail.origin[1] + tail.size[1]);

    by[side + "LowerLeg"].cubes = [
      box([mirroredX(0.4, 3.21), 2.38, -1.73], [3.21, 9.17, 3.54], "skin"),
      // A narrower knee cap keeps the two skin surfaces joined visually
      // without making the back of the knee square during a deep bend.
      box([mirroredX(0.55, 2.95), 10.67, -1.5], [2.95, 1.85, 2.9], "skin"),
    ];
    by[side + "Foot"].cubes = [
      box([mirroredX(0.39, 3.23), 0.1, -2.74], [3.23, 2.58, 4.57], "skin"),
    ];
  }

  function whiteSleeves(g) {
    for (const bone of g.bones) {
      if (/^(Left|Right)Arm$/.test(bone.name)) {
        const {
          origin: [x, y, z],
          size: [w, h, d],
        } = bone.cubes[0];
        bone.cubes = [
          box([x - 0.03, y - 0.13, z - 0.05], [w + 0.06, h + 0.2, d + 0.1]),
        ];
      } else if (/^(Left|Right)ForeArm$/.test(bone.name)) {
        const hand = bone.cubes.reduce((lowest, cube) =>
          cube.origin[1] < lowest.origin[1] ? cube : lowest,
        );
        const [x, y, z] = hand.origin;
        bone.cubes = [
          box(
            [x - 0.135, y + 3.04, z - 0.45],
            [3.27, 6.0, 3.9],
            "fabric",
            "fold",
          ),
          box([x - 0.19, y + 2.47, z - 0.51], [3.38, 1.04, 4.02], "collar"),
          box(hand.origin, hand.size, "skin"),
        ];
      }
    }
  }
  whiteSleeves(geometry);
  for (const firstPerson of arm["minecraft:geometry"])
    whiteSleeves(firstPerson);
};
