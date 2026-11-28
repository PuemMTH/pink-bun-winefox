const { faceSwatches } = require("./expressions.cjs");

module.exports = function fitHead({ geo, animations, atlas, width }) {
  const byName = new Map(
    geo["minecraft:geometry"][0].bones.map((b) => [b.name, b]),
  );
  const pixel = (x, y) => (y * width + x) * 4;

  // The upper lash cubes move with the original eyebrow tracks and blink.
  // Keep their vertical rhythm while thinning the outside steps.
  const ink = { uv: [1793, 454], uv_size: [1, 1] };
  atlas.set([...faceSwatches.ink, 255], pixel(...ink.uv));
  for (const side of ["Left", "Right"]) {
    const [outer, inner] = byName.get(side + "Eyebrow").cubes;
    const sign = side === "Left" ? 1 : -1;
    outer.origin[0] = sign > 0 ? 3.15 : -3.89;
    outer.origin[1] = 34.37;
    outer.size[0] = 0.74;
    outer.size[1] = 0.32;
    inner.origin[0] = sign > 0 ? 1.275 : -3.21;
    inner.origin[1] = 34.63;
    inner.size[0] = 1.935;
    inner.size[1] = 0.43;
    for (const cube of [outer, inner])
      for (const face of Object.keys(cube.uv))
        cube.uv[face] = structuredClone(ink);
  }

  // Keep the inherited mouth track, with a single cutout so the lip and
  // interior cannot overlap while the head tilts during a jump.
  const mouth = [".###.", "#ppp#", "#prp#", ".###."];
  const mouthColors = {
    "#": faceSwatches.ink,
    p: faceSwatches.plum,
    r: faceSwatches.rose,
  };
  const [mouthU, mouthV] = [1793, 455];
  for (const [y, row] of mouth.entries())
    for (const [x, symbol] of [...row].entries()) {
      const color = mouthColors[symbol];
      if (color) atlas.set([...color, 255], pixel(mouthU + x, mouthV + y));
    }
  const transparent = { uv: [1793, 257], uv_size: [1, 1] };
  byName.get("xiao").cubes = [
    {
      origin: [-0.35, 31.93, -2.59],
      size: [0.7, 0.5, 0.02],
      uv: {
        north: {
          uv: [mouthU, mouthV],
          uv_size: [mouth[0].length, mouth.length],
        },
        east: transparent,
        south: transparent,
        west: transparent,
        up: transparent,
        down: transparent,
      },
    },
  ];
  for (const bone of byName.values()) {
    if (bone.parent === "xiao") delete bone.cubes;
  }

  // The crawl inherited tracking for LeftLongHair/RightLongHair, while this
  // rig puts the visible side locks on LongLeftHair/LongRightHair. Bring them
  // into the same pitch as LongHair with small mirrored movement.
  for (const [side, sign] of [
    ["Left", 1],
    ["Right", -1],
  ]) {
    const name = `Long${side}Hair`;
    animations.animations.elytra_fly.bones[name].rotation = [
      `24+math.sin(query.anim_time*720+${sign * 30})*1.5`,
      0,
      sign * 2,
    ];
    for (const state of ["climb", "climbing"]) {
      animations.animations[state].bones[name] = {
        rotation: [
          state === "climb"
            ? `83+math.sin(query.anim_time*360+${sign * 35})*2`
            : 83,
          0,
          sign * 2,
        ],
        position: [0, -0.9, -0.1],
      };
    }
  }
  // The lower center lock has a 40-degree bind bend. Relax that bend only
  // in flight, where the old bend formed a straight spike above the back.
  animations.animations.elytra_fly.bones.bone20 = {
    rotation: ["-23+math.sin(query.anim_time*720)*1.5", 0, 0],
  };

  // Give the central back panels dedicated texels with a shared shade ramp
  // and two vertical strands. Keep the transparent edge pixels and the mesh.
  const back = byName
    .get("BaseHair")
    .cubes.filter(
      (cube) => cube.size[1] >= 6 && cube.size[0] >= 3 && cube.origin[2] >= 3,
    );
  back.push(byName.get("LongHair").cubes.find((cube) => cube.size[0] === 8));
  back.push(...byName.get("bone20").cubes);
  let x = 1793;
  const y = 460;
  for (const cube of back) {
    const face = cube.uv.south;
    const [uw, uh] = face.uv_size;
    const sx = uw * 2;
    const sy = uh * 2;
    for (let v = 0; v < sy; v++)
      for (let u = 0; u < sx; u++) {
        const origin = pixel(
          face.uv[0] + Math.floor(u / 2),
          face.uv[1] + Math.floor(v / 2),
        );
        if (!atlas[origin + 3]) continue;
        const worldX = cube.origin[0] + ((u + 0.5) / sx) * cube.size[0];
        const worldY = cube.origin[1] + (1 - (v + 0.5) / sy) * cube.size[1];
        const shade =
          Math.round(Math.max(0, Math.min(1, (39 - worldY) / 19)) * 5) / 5;
        const strand =
          Math.abs(worldX - 1.4) < 0.32 || Math.abs(worldX + 1.35) < 0.34
            ? 6
            : 0;
        const grain = Math.round((atlas[origin] - 215) * 0.14);
        const rgb = [232 - 17 * shade, 157 - 16 * shade, 187 - 16 * shade].map(
          (channel) => Math.round(channel + grain + strand),
        );
        atlas.set([...rgb, atlas[origin + 3]], pixel(x + u, y + v));
      }
    face.uv = [x, y];
    face.uv_size = [sx, sy];
    x += sx + 2;
  }
};
