// Keep skirt motion in the hip frame; the jacket may lean independently while running.
module.exports = function fixSkirt(geo, liningUv, animations) {
  const bones = geo["minecraft:geometry"][0].bones,
    by = Object.fromEntries(bones.map((b) => [b.name, b]));
  by.cloth.parent = "DownBody";
  for (const name of ["LeftLeg", "RightLeg"])
    for (const q of [...(by[name].cubes || [])]) {
      if (q.rotation || q.origin[1] + q.size[1] <= 16.2) continue;
      const oldHeight = q.size[1],
        newHeight = 16.2 - q.origin[1];
      if (newHeight <= 0) throw Error("Unexpected thigh geometry");
      q.size[1] = newHeight;
      // Preserve the UV scale of the visible thigh when removing its concealed upper end.
      for (const f of ["north", "south", "east", "west"]) {
        const u = q.uv[f],
          cut = ((oldHeight - newHeight) / oldHeight) * u.uv_size[1];
        u.uv[1] += cut;
        u.uv_size[1] -= cut;
      }
      // Preserve the exposed knee/thigh contour; taper only the section under the hem.
      const split = 14.3,
        upper = structuredClone(q),
        lowerHeight = split - q.origin[1];
      upper.origin[1] = split;
      upper.size[1] = 16.2 - split;
      upper.origin[0] += 0.3;
      upper.size[0] -= 0.6;
      upper.origin[2] += 1.2;
      upper.size[2] -= 2.4;
      for (const f of ["north", "south", "east", "west"]) {
        const scale = q.uv[f].uv_size[1] / q.size[1];
        upper.uv[f].uv_size[1] = upper.size[1] * scale;
        q.uv[f].uv[1] += upper.size[1] * scale;
        q.uv[f].uv_size[1] = lowerHeight * scale;
      }
      q.size[1] = lowerHeight;
      by[name].cubes.push(upper);
    }
  const lining = {
    name: "CustomSkirtLining",
    parent: "cloth",
    pivot: [0, 19.7, 0],
    cubes: [],
  };
  const green = liningUv || by.FrontClothe.cubes[0].uv;
  if (liningUv) {
    // The reverse faces of the original pleats read as one matte lining.
    // Sample inside the opaque green tile, safely away from unused atlas texels.
    const [x, y] = green.north.uv;
    const inner = { uv: [x + 4.25, y + 73.25], uv_size: [0.5, 0.5] };
    for (const [name, face] of [
      ["FrontClothe", "south"],
      ["BackClothe", "north"],
      ["LeftClothe", "east"],
      ["RightClothe", "west"],
    ])
      for (const cube of by[name].cubes) {
        cube.uv[face] = structuredClone(inner);
        cube.uv.down = structuredClone(inner);
      }
  }
  // The waistband stays at the hip when the lower skirt tilts forward.
  // Its hidden top overlaps the jacket so that bend cannot open a waist gap.
  const waistbandUv = structuredClone(green);
  for (const face of Object.values(waistbandUv)) {
    face.uv[1] += face.uv_size[1] * 0.68;
    face.uv_size[1] *= 0.26;
  }
  bones.push({
    name: "CustomSkirtWaist",
    parent: "DownBody",
    pivot: by.DownBody.pivot.slice(),
    cubes: [
      {
        origin: [-3.58, 18.95, -2.04],
        size: [7.16, 2.87, 3.46],
        uv: waistbandUv,
      },
    ],
  });
  // The visible skin stops short of the hip pivot to keep it inside the
  // skirt during a stride. A narrow fabric join must still reach the hinge
  // when the knee lifts, or the exposed thigh can look detached in profile.
  for (const side of ["Left", "Right"]) {
    const leg = by[side + "Leg"];
    const [x, y, z] = leg.pivot;
    const name = "Custom" + side + "ThighJoin";
    const uv = structuredClone(green);
    for (const face of Object.values(uv)) {
      face.uv[1] += face.uv_size[1] * 0.72;
      face.uv_size[1] *= 0.24;
    }
    bones.push({
      name,
      parent: leg.name,
      pivot: leg.pivot.slice(),
      cubes: [
        {
          origin: [x - 1.2, 15.55, z - 0.65],
          size: [2.4, y - 14.73, 2.55],
          uv,
        },
      ],
    });
  }
  // Three stepped rectangular frames match the block construction of the JK pleats.
  // The walls meet at the corners, keeping a closed lining with twelve cubes.
  const bands = 3,
    bottom = 14.8,
    top = 21,
    thickness = 0.18;
  for (let j = 0; j < bands; j++) {
    const t = j / bands,
      y = bottom + t * (top - bottom);
    const height = (top - bottom) / bands;
    const profile = (j + 0.5) / bands;
    const rx = 4.8 - profile * 0.95,
      rz = 3.25 - profile * 1.05;
    const walls = [
      { origin: [-rx, y, -rz], size: [2 * rx, height, thickness] },
      { origin: [-rx, y, rz - thickness], size: [2 * rx, height, thickness] },
      // Butt the side walls against the front and back panels. Their former
      // overlap left duplicate top and bottom planes at the four corners.
      { origin: [-rx, y, -rz + thickness], size: [thickness, height, 2 * (rz - thickness)] },
      { origin: [rx - thickness, y, -rz + thickness], size: [thickness, height, 2 * (rz - thickness)] },
    ];
    for (const wall of walls) {
      wall.uv = structuredClone(green);
      for (const [name, face] of Object.entries(wall.uv)) {
        // Carry the same broad pixel pleats through all three lining tiers.
        const fullHeight = face.uv_size[1];
        face.uv[1] += ((bands - j - 1) / bands) * fullHeight;
        face.uv_size[1] = fullHeight / bands;
        if (name === "up" || name === "down") {
          face.uv[0] += 1;
          face.uv_size = [1, 1];
        }
      }
      lining.cubes.push(wall);
    }
  }
  bones.push(lining);
  // Keep the pleats and lining together, with a small shared sway at the waist.
  // Individual panels still retain their bind transforms so no seams open.
  const skirtBones = bones.filter((b) => {
    let parent = b;
    while (parent && parent.name !== "cloth") parent = by[parent.parent];
    return Boolean(parent);
  });
  const seatedPitch = { sit: -40, boat: -40, ride: -38, ride_pig: -38 };
  for (const clip of [
    "run",
    "jump",
    "sneak",
    "sneaking",
    ...Object.keys(seatedPitch),
  ])
    for (const b of skirtBones)
      animations.animations[clip].bones[b.name] = {
        rotation: [0, 0, 0],
        position: [0, 0, 0],
        scale: [1, 1, 1],
      };
  const run = animations.animations.run.bones;
  const duration = animations.animations.run.animation_length;
  const sway = [1.2, 1.8, 0.8]; // pitch, yaw and roll amplitudes in degrees
  run.cloth.rotation = Object.fromEntries(
    Array.from({ length: 9 }, (_, i) => {
      const phase = (i / 8) * Math.PI * 2;
      return [
        ((duration * i) / 8).toFixed(4),
        [
          sway[0] * Math.cos(phase),
          sway[1] * Math.sin(phase),
          sway[2] * Math.cos(phase),
        ].map((n) => Math.round(n * 10000) / 10000),
      ];
    }),
  );
  // Move the assembled skirt with the raised thighs, rather than animating
  // individual pleats as rigid slabs that can drift away from the hip.
  const sneak = animations.animations.sneak;
  sneak.bones.cloth.rotation = Object.fromEntries(
    Object.entries(run.cloth.rotation).map(([time, rotation]) => [
      ((Number(time) / duration) * sneak.animation_length).toFixed(4),
      rotation.map((n) => Math.round(n * 0.4 * 10000) / 10000),
    ]),
  );
  animations.animations.sneaking.bones.cloth.rotation = [-47, 0, 0];
  animations.animations.sneaking.bones.cloth.position = [0, -0.95, 0];
  // The shared crouch tilt still closes the waist. Shorten the assembly
  // slightly along its own length and depth to clear the raised heels.
  animations.animations.sneaking.bones.cloth.scale = [1, 0.88, 0.92];
  animations.animations.jump.bones.cloth.rotation = [-29, 0, 0];
  animations.animations.jump.bones.cloth.position = [0, -0.55, -0.32];
  for (const [clip, pitch] of Object.entries(seatedPitch)) {
    const pose = animations.animations[clip].bones.cloth;
    pose.rotation = [pitch, 0, 0];
    pose.position = [0, -0.7, -0.45];
    pose.scale = [1, 0.85, 1];
  }
  // During the prone swim, retract the lower blazer into the chest as it
  // rolls independently from the waist. This leaves the green pleats visible.
  animations.animations.swim.bones.jk2 = { position: [0, 1.5, 0.15] };
  return geo;
};
