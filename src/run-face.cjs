module.exports = function runFace(geo, animations, add, mat) {
  const bones = geo["minecraft:geometry"][0].bones;
  const face = {
    name: "CustomRunFace",
    parent: "Head",
    pivot: [0, 33.7, -3.6],
    cubes: [],
  };
  bones.push(face);
  const blank = { uv: [1793, 257], uv_size: [1, 1] },
    eye = { uv: [1800, 264], uv_size: [64, 80] };
  const irises = [];
  for (const s of [-1, 1]) {
    const side = s < 0 ? "Right" : "Left",
      iris = {
        name: "CustomRunIris" + side,
        parent: side + "Eyelid",
        pivot: [s * 2.225, 32.7, -3.025],
        cubes: [],
      };
    const q = {
      origin: [s * 2.225 - 0.7, 32.7, -3.64],
      size: [1.4, 2, 0.025],
      uv: Object.fromEntries(
        ["north", "east", "south", "west", "up", "down"].map((f) => [
          f,
          structuredClone(blank),
        ]),
      ),
    };
    q.uv.north = structuredClone(eye);
    iris.cubes.push(q);
    bones.push(iris);
    irises.push(iris);
  }
  for (const [x, y, w, r] of [
    [-0.24, 31.95, 0.3, 7],
    [0.04, 31.94, 0.23, -9],
  ])
    face.cubes.push({
      origin: [x, y, -3.62],
      size: [w, 0.07, 0.025],
      pivot: [x, y, -3.62],
      rotation: [0, 0, r],
      uv: Object.fromEntries(
        ["north", "east", "south", "west", "up", "down"].map((f) => [
          f,
          mat("dark"),
        ]),
      ),
    });
  // Main locomotion clips own visibility. Blink/look animations remain children of Eyes,
  // so they cannot re-enable the normal eyes while the run face is visible.
  for (const [name, a] of Object.entries(animations.animations)) {
    if (/parallel/.test(name)) continue;
    a.bones ??= {};
    for (const n of [
      "CustomRunFace",
      "CustomRunIrisLeft",
      "CustomRunIrisRight",
    ])
      a.bones[n] = { scale: name === "run" ? 1 : 0 };
    for (const n of ["Mouth", "LeftEyelidBase", "RightEyelidBase"]) {
      a.bones[n] ??= {};
      a.bones[n].scale = name === "run" ? 0 : 1;
    }
  }
  function paint(pixels, W) {
    for (let y = 0; y < 80; y++)
      for (let x = 0; x < 64; x++) {
        const dx = x - 31.5,
          dy = y - 39.5,
          oval = (dx / 29) ** 2 + (dy / 37) ** 2;
        if (oval > 1) continue;
        let color = [248, 235, 237];
        if (oval > 0.88) color = [91, 69, 100];
        const ix = dx,
          iy = (dy - 1) * 0.78,
          r = Math.hypot(ix, iy),
          angle = Math.atan2(iy, ix);
        if (r < 27) {
          const t = Math.max(0, Math.min(1, (dy + 30) / 64));
          color = [
            Math.round(146 + 52 * t),
            Math.round(48 + 33 * t),
            Math.round(96 + 26 * t),
          ];
          let distance = Infinity;
          for (let turn = 0; turn < 4; turn++)
            distance = Math.min(
              distance,
              Math.abs(r - 1.45 * (angle + Math.PI + turn * 2 * Math.PI)),
            );
          if (distance < 1.1 || r < 2.2) color = [101, 39, 85];
          if (r > 25.5) color = [112, 43, 87];
        }
        const lid = 7 + 6 * (dx / 30) ** 2;
        if (y > lid && y < lid + 3 && Math.abs(dx) < 28) color = [77, 56, 86];
        const i = ((y + 264) * W + x + 1800) * 4;
        for (let k = 0; k < 3; k++) pixels[i + k] = color[k];
        pixels[i + 3] = 255;
      }
  }
  return { face, irises, animations, paint };
};
