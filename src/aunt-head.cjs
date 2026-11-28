const faces = ["north", "south", "east", "west", "up", "down"];
const hairRamp = [
  [113, 91, 143],
  [145, 119, 172],
  [180, 155, 207],
  [201, 181, 223],
  [224, 208, 240],
];

module.exports = function fitAuntHead({ geo, atlas, width, animations, extra }) {
  const bones = geo["minecraft:geometry"][0].bones;
  const by = Object.fromEntries(bones.map((bone) => [bone.name, bone]));
  const offset = (x, y) => (y * width + x) * 4;
  const region = (x, y, w = 1, h = 1) => ({ uv: [x, y], uv_size: [w, h] });
  const clear = region(160, 1500);
  let nextTile = 162;
  function tile(rows, colors) {
    const u = nextTile;
    const v = 1500;
    const w = rows[0].length;
    nextTile += w + 2;
    for (const [y, row] of rows.entries())
      for (const [x, symbol] of [...row].entries())
        if (colors[symbol]) atlas.set([...colors[symbol], 255], offset(u + x, v + y));
    return region(u, v, w, rows.length);
  }
  function solid(color) {
    return tile(["#"], { "#": color });
  }
  function cube(origin, size, material, rotation) {
    const uv = Object.fromEntries(faces.map((face) => [face, material]));
    return rotation
      ? { origin, size, uv, rotation, pivot: origin.map((value, i) => value + size[i] / 2) }
      : { origin, size, uv };
  }
  function decal(origin, w, h, material, rotation) {
    const q = cube(origin, [w, h, 0.025], clear, rotation);
    q.uv.north = material;
    return q;
  }
  function add(name, parent, pivot, cubes) {
    const group = { name, parent, pivot, cubes };
    bones.push(group);
    return group;
  }

  // Reuse the native crown and side locks with the original pixel shading in lavender.
  for (let y = 0; y < 136; y++)
    for (let x = 0; x < 136; x++) {
      const i = offset(x, y);
      const opacity = atlas[i + 3];
      if (!opacity) continue;
      const green = atlas[i + 1];
      const shade = green < 125 ? 0 : green < 158 ? 1 : green < 194 ? 2 : green < 230 ? 3 : 4;
      atlas.set([...hairRamp[shade], opacity], offset(x, y + 1500));
    }
  by.BaseHair.cubes = by.BaseHair.cubes.filter(({ origin }) => origin[2] < 3.8);
  for (const name of ["BaseHair", "bone5", "Bangs", "RightSideHair", "LeftSideHair", "bone34"])
    for (const q of by[name].cubes)
      for (const face of Object.values(q.uv)) face.uv[1] += 1500;
  for (const name of [
    "LongHair", "LongHair2", "LongLeftHair", "LongLeftHair2", "LongRightHair", "LongRightHair2",
  ])
    delete by[name].cubes;

  const hairShades = hairRamp.map(solid);
  const strand = tile(["abbcc", "abbcc", "aabcc", "aabcc", "aabbc", "aabbb"], {
    a: hairRamp[1], b: hairRamp[2], c: hairRamp[3],
  });
  by.LongHair.cubes = [
    cube([-3.55, 31.15, 2.3], [7.1, 3.45, 1.8], strand, [3, 0, 0]),
    cube([-2.95, 30.48, 2.5], [5.7, 1.25, 1.45], strand, [4, 0, 0]),
    cube([-2.12, 29.85, 2.75], [3.98, 1.05, 1.1], hairShades[1], [7, 0, 3]),
  ];
  by.Bangs.cubes.push(
    cube([-0.33, 35.72, -4.23], [0.80, 2.45, 0.72], strand, [4, 0, -13]),
    cube([-0.66, 35.32, -4.18], [0.63, 1.24, 0.66], hairShades[1], [4, 0, -19]),
  );

  // Rounded segments alternate direction without requiring dense braid geometry.
  const braid = add("AuntBraid", "Hair", [3.1, 35.4, 0], [
    cube([2.62, 33.46, -1.90], [1.79, 2.42, 1.29], strand, [-17, 21, -12]),
    cube([2.83, 32.32, -2.58], [1.66, 1.85, 1.19], strand, [-24, 23, 22]),
    cube([2.62, 31.12, -3.57], [1.70, 1.96, 1.28], strand, [-29, 15, -20]),
    cube([2.43, 30.05, -4.06], [1.65, 1.72, 1.22], strand, [-20, 12, 24]),
  ]);
  const tail = add("AuntBraidTip", braid.name, [3.1, 30.6, -3.5], []);
  for (const [index, [x, y, z, breadth]] of [
    [3.15, 30.45, -4.33, 2.07],
    [2.94, 29.29, -4.45, 1.98],
    [2.79, 28.13, -4.49, 1.81],
    [2.65, 27.08, -4.45, 1.61],
    [2.56, 26.10, -4.43, 1.30],
  ].entries()) {
    const spin = index % 2 === 0 ? -22 : 22;
    tail.cubes.push(
      cube([x - breadth / 2, y - 1.02, z], [breadth, 1.7, 1.08], strand, [0, 0, spin]),
    );
  }
  tail.cubes.push(
    cube([2.11, 25.04, -4.43], [0.82, 0.32, 1.05], hairShades[0], [0, 0, 6]),
    cube([2.19, 23.96, -4.37], [0.70, 1.23, 0.95], strand, [4, 0, 12]),
    cube([2.35, 23.40, -4.28], [0.44, 0.86, 0.70], hairShades[2], [6, 0, 17]),
  );
  for (const [name, pitch, sway] of [
    ["idle", 0, 1.4], ["walk", 0, 3], ["run", 9, 4], ["jump", 5, 2],
  ]) {
    const clip = animations.animations[name];
    if (clip?.bones)
      clip.bones[tail.name] = { rotation: [pitch, 0, `math.sin(q.anim_time*360)*${sway}`] };
  }

  const skin = { p: [254, 237, 222], s: [246, 219, 207], t: [240, 213, 204] };
  const skinFront = tile(
    ["sssssss", "sppppps", "sppppps", "ppppppp", "ppppppp", "sppppps", "sspppss"], skin,
  );
  const skinSide = tile(
    ["sssssss", "sssssss", "sssssss", "sppppps", "sppppps", "sppppps", "tssssst"], skin,
  );
  const skinShade = solid(skin.t);
  by.Head.cubes[0].uv = {
    north: skinFront, east: skinSide, west: skinSide,
    down: skinShade, south: hairShades[1], up: hairShades[2],
  };
  by.AllHead.cubes[0].uv = Object.fromEntries(faces.map((face) => [face, skinShade]));

  const wrapColors = {
    a: [234, 233, 241], b: [206, 208, 223], c: [169, 174, 197], d: [146, 149, 174],
  };
  const forewrap = tile(["aaaaaaaa", "bbbbbbbb", "aaaaaaaa", "cccccccc"], wrapColors);
  const neckwrap = tile(["bbbbbb", "cccccc", "aaaaaa", "cccccc", "bbbbbb", "dddddd"], wrapColors);
  const cheek = tile([".aabbaa", "baacaaa", "baacaab", ".bbccbb"], wrapColors);
  const earring = tile([".l...", "lg...", "lg...", "lgg.g", ".lll.", "..l.."], {
    l: [243, 207, 118], g: [174, 125, 78],
  });
  add("AuntHeadWrap", "Head", by.Head.pivot, [
    decal([-3.08, 36.27, -3.23], 6.16, 1.56, forewrap),
    cube([-4.20, 37.08, -1.58], [0.18, 1.23, 4.07], forewrap, [-8, -4, 0]),
    cube([4.05, 37.13, -1.59], [0.18, 1.20, 4.08], forewrap, [-8, 5, 0]),
    cube([-3.36, 37.3, 3.74], [6.72, 1.13, 0.23], forewrap),
  ]);
  const mirroredCheek = region(cheek.uv[0] + 7, cheek.uv[1], -7, 4);
  add("AuntCheekWraps", "Head", by.Head.pivot, [
    decal([-2.75, 33.69, -3.24], 1.44, 0.72, cheek, [0, 0, -26]),
    decal([1.31, 33.69, -3.24], 1.44, 0.72, mirroredCheek, [0, 0, 26]),
    decal([-3.08, 33.66, -3.32], 0.43, 0.53, earring),
  ]);
  add("AuntNeckWrap", "AllHead", by.AllHead.pivot, [
    cube([-1.37, 32.07, -1.49], [2.74, 2.28, 2.98], neckwrap),
  ]);

  const eyeColors = {
    w: [247, 244, 250], s: [211, 216, 233],
    r: [57, 93, 149], b: [86, 151, 199], l: [139, 200, 222],
    p: [33, 48, 83], h: [245, 255, 255],
  };
  const white = tile(
    [".wwwwww.", "wwwwwwww", "wwwwwwww", "wwwwwwww", "wwwwwwww", ".ssssss."], eyeColors,
  );
  const iris = tile([".rrr.", "rhprr", "rpprr", "rbpbr", "rlllr", ".bbb."], eyeColors);
  const lash = tile([".kkkkk.", "kkkkkkk", "k.....k"], { k: [53, 42, 72] });
  for (const [side, sign] of [["Right", -1], ["Left", 1]]) {
    const center = sign * 1.67;
    const eyelid = by[`${side}Eyelid`];
    const eyeBase = by[`${side}EyelidBase`];
    eyelid.cubes = [decal([center - 1.01, 34.51, -3.27], 2.02, 1.38, white)];
    eyeBase.cubes = [decal([center - 0.66, 34.49, -3.32], 1.32, 1.41, iris)];
    by[`${side}Eyebrow`].cubes = [decal([center - 1.10, 35.54, -3.37], 2.20, 0.58, lash)];
    by[`ysmGlow${side}EyelidBase`].cubes = [];
    by[`ysmGlow${side}EyePublic`].cubes = [];
    by[`${side}EyeDot`].cubes = [];
    for (const group of [animations.animations, extra.animations])
      for (const clip of Object.values(group)) {
        const scale = clip.bones?.[eyelid.name]?.scale;
        if (scale && typeof scale === "object" && !Array.isArray(scale))
          for (const key of Object.values(scale)) if (!Array.isArray(key)) delete key.lerp_mode;
      }
  }

  for (const bone of bones)
    if (["Mouth", "xiao", "Expression_7"].includes(bone.parent) || bone.name === "ku_ku_yan")
      delete bone.cubes;
  const smile = tile(["m.....m", ".mmmmm."], { m: [108, 64, 80] });
  const grin = tile(["mmmmm", ".rrr.", "..r.."], { m: [104, 57, 75], r: [169, 100, 114] });
  const smileBone = add("AuntSmile", "Mouth", by.Mouth.pivot, [
    decal([-0.54, 33.99, -3.28], 1.08, 0.26, smile),
  ]);
  const openBone = add("AuntOpenSmile", "Mouth", by.Mouth.pivot, [
    decal([-0.41, 33.86, -2.91], 0.82, 0.43, grin),
  ]);
  for (const name of ["jump", "attacked"]) {
    const clip = animations.animations[name];
    if (!clip?.bones) continue;
    clip.bones[smileBone.name] = { scale: 0 };
    clip.bones[openBone.name] = { position: [0, 0, -0.46] };
  }
};
