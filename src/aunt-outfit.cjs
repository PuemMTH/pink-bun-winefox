const assert = require("node:assert/strict");

const faces = ["north", "south", "east", "west", "up", "down"];
const colors = Object.fromEntries(
  Object.entries({
    pink: ["efc1e2", "e4afd8", "dba2cd", "ce94c0", "bb81ae"],
    skin: ["fff1e6", "f8e4da", "eed8d1", "e4c9c8", "dab9bd"],
    bandage: ["f5f3f6", "e7e5ed", "dad8e5", "c5c3d4", "b5b2c9"],
    cream: ["fff7f5", "f3eaf0", "e6dbe8", "d7c9df", "cebfd7"],
    gold: ["fff0b6", "edd998", "d5bd7e", "bca16b", "a08a5f"],
  }).map(([key, ramp]) => [key, ramp.map((hex) => Buffer.from(`${hex}ff`, "hex"))]),
);

module.exports = function auntOutfit({ geo, arm, atlas, width, height, animations }) {
  const geometry = geo["minecraft:geometry"][0];
  const bones = geometry.bones;
  const by = Object.fromEntries(bones.map((bone) => [bone.name, bone]));
  let u = 802;
  let v = 1502;
  let rowHeight = 0;

  function paint(w, h, colorAt) {
    if (u + w + 1 >= width) {
      u = 802;
      v += rowHeight + 2;
      rowHeight = 0;
    }
    assert(v + h + 1 < height, "Pink dress atlas region is full");
    for (let y = -1; y <= h; y++)
      for (let x = -1; x <= w; x++) {
        const color = colorAt(Math.min(w - 1, Math.max(0, x)), Math.min(h - 1, Math.max(0, y)));
        if (color) color.copy(atlas, ((v + y) * width + u + x) * 4);
      }
    const tile = { uv: [u, v], uv_size: [w, h] };
    rowHeight = Math.max(rowHeight, h);
    u += w + 2;
    return tile;
  }

  function fabric(size, material, detail) {
    const [x, y, z] = size.map((span) => Math.max(1, Math.round(span)));
    return Object.fromEntries(faces.map((face) => {
      const side = face === "east" || face === "west";
      const horizontal = face === "up" || face === "down";
      const w = side ? z : x;
      const h = horizontal ? z : material === "bandage" ? y * 2 : y;
      const uv = paint(w, h, (column, row) => {
        const across = (column + 0.5) / w;
        const down = (row + 0.5) / h;
        let shade = face === "up" ? 0 : face === "down" ? 4 : side ? 2 : 1;
        if (material === "pink" && !horizontal) {
          const crease = down > 0.38 && Math.abs(across - (0.41 + down * 0.31)) < 0.19;
          shade += Number(detail === "fold" && crease);
          shade += Number(detail === "hem" && row === h - 1);
        } else if (material === "bandage" && !horizontal) {
          // Overlapping fabric stripes are texels on one fitted surface.
          shade += Number((row + (column >= Math.ceil(w / 2) ? 1 : 0)) % 3 === 2) * 2;
        }
        return colors[material][Math.max(0, Math.min(4, shade))];
      });
      return [face, uv];
    }));
  }

  function box(origin, size, material = "pink", detail) {
    return { origin, size, uv: fabric(size, material, detail) };
  }

  const neckline = [
    "..CCSssssSCC..",
    ".CCCSssssSCCC.",
    ".CCCCssssCCCC.",
    ".CCCCCssCCCCC.",
    ".CCCCCssCCCCC.",
    ".CCCCC..CCCCC.",
    "..CCCD..DCCC..",
    "...DD....DD...",
  ];
  const collarColors = {
    C: colors.cream[0],
    D: colors.cream[1],
    S: colors.skin[2],
    s: colors.skin[1],
  };
  const collar = paint(neckline[0].length, neckline.length, (x, y) => collarColors[neckline[y][x]]);
  const neckButton = [".00.", "0112", "1122", ".22."];
  const button = paint(4, 4, (x, y) => colors.gold[neckButton[y][x]]);

  // The dress follows the inherited upper-body and waist pivots.
  by.UpperBody.cubes = [
    box([-3.77, 24.06, -2.43], [7.54, 8.17, 4.86], "pink", "fold"),
    box([-3.92, 30.72, -2.18], [7.84, 1.77, 4.36]),
    box([-1.44, 32.42, -1.4], [2.88, 0.48, 2.8], "skin"),
    { origin: [-3.09, 29.32, -2.47], size: [6.18, 3.17, 0.02], uv: { north: collar } },
    { origin: [-0.32, 29.22, -2.5], size: [0.64, 0.64, 0.02], uv: { north: button } },
  ];
  by.UpBody.cubes = [box([-3.72, 19.82, -2.35], [7.44, 5.28, 4.7], "pink", "fold")];
  delete by.RichOppai.cubes;
  delete by.RichOppai2.cubes;

  // Preserve the separate Matured skirt panels and their motion. The inner
  // dress surface replaces the stock overlapping apron in front.
  const skirt = new Set(["clothe"]);
  const folds = new Set(["FM1", "FR1", "FL1", "RM2", "LM2", "BR2", "BL2"]);
  for (const bone of bones) {
    if (!skirt.has(bone.parent)) continue;
    skirt.add(bone.name);
    if (bone.name.startsWith("FFM")) {
      delete bone.cubes;
      continue;
    }
    for (const cube of bone.cubes || [])
      cube.uv = fabric(cube.size, "pink", cube.origin[1] < 11 ? "hem" : folds.has(bone.name) ? "fold" : undefined);
  }

  // Lift and deepen the whole skirt for crouch walking so the hem clears
  // the heels and knees while the adjacent pleats move together.
  animations.animations.sneak.bones.clothe.scale = [1, 0.83, 1.15];

  for (const [side, sign] of [["Left", 1], ["Right", -1]]) {
    const mirrored = (x, w) => sign > 0 ? x : -x - w;
    by[side + "Leg"].cubes = [
      box([mirrored(0.67, 2.96), 10.57, -1.45], [2.96, 6.45, 2.95], "skin"),
    ];
    by[side + "LowerLeg"].cubes = [
      box([mirrored(0.63, 2.98), 2.46, -1.45], [2.98, 9.14, 3.0], "skin"),
    ];
    if (side === "Left")
      by.LeftLowerLeg.cubes.push(
        box([0.56, 4.33, -1.53], [3.12, 5.83, 3.16], "bandage"),
      );
    by[side + "Foot"].cubes = [
      box([mirrored(0.62, 3.0), 0.16, -3.18], [3.0, 1.33, 4.87], "skin"),
      box([mirrored(0.76, 2.73), 1.22, -1.61], [2.73, 2.21, 3.16], "skin"),
    ];
  }

  function sleeves(skeleton) {
    const parts = Object.fromEntries(skeleton.bones.map((bone) => [bone.name, bone]));
    for (const [side, sign, fist] of [["Left", 1, "leftfist"], ["Right", -1, "Rightfist"]]) {
      const upper = parts[side + "Arm"];
      const fore = parts[side + "ForeArm"];
      const [dx, dy, dz] = upper.pivot.map((value, axis) => value - by[side + "Arm"].pivot[axis]);
      const sleeve = (x, y, z, w, h, d, material, detail) => box(
        [(sign > 0 ? x : -x - w) + dx, y + dy, z + dz], [w, h, d], material, detail,
      );
      upper.cubes = [
        sleeve(1.98, 24.87, -1.87, 3.22, 6.9, 3.77, "pink", "fold"),
        sleeve(2.10, 30.64, -1.79, 3.01, 1.88, 3.62),
      ];
      fore.cubes = [
        sleeve(1.88, 21.4, -1.97, 3.45, 4.23, 3.99, "pink", "fold"),
        sleeve(1.97, 20.75, -1.88, 3.25, 0.83, 3.81, "cream"),
        sleeve(2.23, 18.5, -1.31, 2.68, 2.43, 2.71, "skin"),
      ];
      if (side === "Right")
        fore.cubes.push(sleeve(2.16, 18.59, -1.4, 2.82, 2.1, 2.88, "bandage"));
      parts[fist].cubes = [sleeve(2.13, 16.76, -1.35, 2.8, 2.25, 2.76, "skin")];
      delete parts[side + "Hand"].cubes;
    }
    delete parts.LeftForeArm5.cubes;
  }
  sleeves(geometry);
  for (const firstPerson of arm["minecraft:geometry"]) sleeves(firstPerson);
};
