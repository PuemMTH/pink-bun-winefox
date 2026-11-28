const { expressions, faceSwatches } = require("./expressions.cjs");

const palette = {
  ink: [30, 18, 29],
  white: [255, 240, 241],
  whiteShade: [232, 191, 203],
  rim: [114, 26, 60],
  plum: [133, 28, 68],
  pupil: [91, 18, 54],
  rose: [173, 36, 83],
  bright: [213, 49, 100],
  spiral: [73, 14, 41],
  highlight: [255, 222, 229],
};
const glyph = [
  "#########",
  "#........",
  "#.#####..",
  "#.#...#..",
  "#.#.###..",
  "#.#......",
  "#.#######",
  "#.......#",
  "#########",
];
const blank = { uv: [1793, 257], uv_size: [1, 1] };
const faceNames = ["north", "east", "south", "west", "up", "down"];

function paintIris(dot, spiral, side, glow) {
  for (let y = 0; y < 11; y++)
    for (let x = 0; x < 11; x++) {
      const border = y === 0 || y === 10 || x === 0 || x === 10;
      let shade = border ? "rim" : y < 5 ? "plum" : y < 8 ? "rose" : "bright";
      if (spiral && !border)
        shade = glyph[y - 1][x - 1] === "#" ? "spiral" : "bright";
      if (!spiral && x >= 3 && x <= 7 && y >= 3 && y <= 6) shade = "pupil";
      if (!spiral && y === 4 && x === (side < 0 ? 1 : 9)) shade = "highlight";
      dot(x, y, palette[shade]);
      if (shade === "bright" || shade === "highlight")
        glow?.(x, y, palette[shade]);
    }
}

// Apply only to the alternate model's cloned geometry and texture. The
// original blink, look, sprint and expression-wheel tracks still own visibility.
module.exports = function applySquareEyes({ geo, animations, atlas, width }) {
  const bones = geo["minecraft:geometry"][0].bones;
  const by = Object.fromEntries(
    bones.map((bone) => [bone.name, bone]),
  );
  const offset = (x, y) => (y * width + x) * 4;
  const painter = (u, v) => (x, y, color) =>
    atlas.set([...color, 255], offset(u + x, v + y));
  const region = (x, y, w, h) => ({ uv: [x, y], uv_size: [w, h] });
  function plane(x, y, z, w, h, image) {
    return {
      origin: [x, y, z],
      size: [w, h, 0.02],
      uv: Object.fromEntries(
        faceNames.map((face) => [face, face === "north" ? image : blank]),
      ),
    };
  }
  function addGlow(parent, cubes) {
    // YSM renders the named group fullbright. The parent still owns eye motion.
    bones.push({
      name: `ysmGlow${parent.name}`,
      parent: parent.name,
      pivot: parent.pivot.slice(),
      cubes,
    });
  }
  function glowFor(iris, uv) {
    const [x, y, z] = iris.origin;
    const [w, h] = iris.size;
    return plane(x, y, z - 0.025, w, h, uv);
  }

  const scleraUV = region(1800, 354, 15, 13);
  const spiralUV = region(1848, 354, 11, 11);
  const spiralGlow = region(1848, 374, 11, 11);
  const gazeGlow = {
    "-1": region(1820, 374, 11, 11),
    "1": region(1834, 374, 11, 11),
  };
  const inkUV = region(1862, 354, 1, 1);
  const sclera = painter(...scleraUV.uv);
  for (let y = 0; y < 13; y++)
    for (let x = 0; x < 15; x++) {
      if (y === 12 && (x === 0 || x === 14)) continue;
      const edge = y === 12 || x === 0 || x === 14;
      sclera(x, y, edge ? palette.whiteShade : palette.white);
    }
  paintIris(painter(...spiralUV.uv), true, 0, painter(...spiralGlow.uv));
  painter(...inkUV.uv)(0, 0, palette.ink);

  for (const [name, side, u] of [
    ["Right", -1, 1820],
    ["Left", 1, 1834],
  ]) {
    const gazeUV = region(u, 354, 11, 11);
    paintIris(painter(...gazeUV.uv), false, side, painter(...gazeGlow[side].uv));
    const center = side * 2.08;
    by[name + "Eyelid"].cubes = [
      plane(center - 1.11, 32.7, -3.52, 2.22, 1.9, scleraUV),
    ];
    by[name + "EyelidBase"].cubes = [];
    by[name + "EyeDot"].cubes = [];
    const normal = by[name + "EyePublic"];
    const sprint = by["CustomRunIris" + name];
    normal.cubes = [
      plane(center - 0.76, 32.73, -3.62, 1.52, 1.73, gazeUV),
    ];
    sprint.cubes = [
      plane(center - 0.76, 32.73, -3.62, 1.52, 1.73, spiralUV),
    ];
    addGlow(normal, [glowFor(normal.cubes[0], gazeGlow[side])]);
    addGlow(sprint, [glowFor(sprint.cubes[0], spiralGlow)]);
    by[name + "Eyebrow"].cubes = [
      plane(center - 1.19, 34.37, -3.77, 2.38, 0.39, inkUV),
      plane(center + side * 1.08 - 0.27, 34.2, -3.78, 0.54, 0.42, inkUV),
    ];
    // Cubic interpolation dips below zero in the closed hold and inverts the iris.
    const blink = animations.animations.pre_parallel3.bones[name + "Eyelid"];
    for (const keyframe of Object.values(blink.scale)) delete keyframe.lerp_mode;
  }

  // Keep the native mouth track and use the short neutral mark from the reference.
  const mouthUV = region(1793, 454, 1, 1);
  by.weixiao.cubes = [plane(-0.23, 32.14, -2.61, 0.46, 0.08, mouthUV)];

  for (const [index, id] of Object.keys(expressions).entries()) {
    const expression = by[`CustomExpression${index}`];
    const face = expression.cubes[0];
    const {
      uv: [u, v],
      uv_size: [w, h],
    } = face.uv.north;
    const pixelWidth = face.size[0] / w;
    const pixelHeight = face.size[1] / h;
    // The expression tiles already contain the mouth shapes in their last rows.
    for (let y = 0; y < 20; y++)
      atlas.fill(0, offset(u, v + y), offset(u + w, v + y));
    const dot = painter(u, v);
    const surprised = id === "face_surprised";
    const concerned = id === "face_concerned";
    const spiral = id.includes("spiral");
    const glowCubes = [];
    for (const [center, side] of [
      [9, -1],
      [38, 1],
    ]) {
      for (let x = -4; x <= 4; x++) {
        const brow = surprised ? 1 : concerned ? 3 + Math.round((side * x) / 4) : 3;
        dot(center + x, brow, faceSwatches.brow);
      }
      if (id === "face_closed" || (id === "face_wink" && side < 0)) {
        for (let y = 12; y <= 13; y++)
          for (let x = -7; x <= 7; x++) dot(center + x, y, palette.ink);
        continue;
      }
      const top = surprised ? 4 : 6;
      const bottom = surprised ? 19 : 18;
      for (let y = top + 2; y <= bottom; y++)
        for (let x = -7; x <= 7; x++) {
          if (y === bottom && Math.abs(x) === 7) continue;
          dot(center + x, y, y === bottom ? palette.whiteShade : palette.white);
        }
      paintIris(
        (x, y, color) => dot(center + x - 5, bottom + y - 10, color),
        spiral,
        side,
      );
      glowCubes.push(
        plane(
          face.origin[0] + (center - 5) * pixelWidth,
          face.origin[1] + (h - bottom - 1) * pixelHeight,
          face.origin[2] - 0.025,
          11 * pixelWidth,
          11 * pixelHeight,
          spiral ? spiralGlow : gazeGlow[side],
        ),
      );
      for (let x = -8; x <= 8; x++)
        for (let y = top + (Math.abs(x) === 8 ? 1 : -1); y <= top + 1; y++)
          dot(center + x, y, palette.ink);
      for (let y = top + 2; y <= top + 3; y++)
        dot(center + side * 8, y, palette.ink);
    }
    if (glowCubes.length) addGlow(expression, glowCubes);
  }
};
