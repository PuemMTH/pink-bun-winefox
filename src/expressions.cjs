const expressions = {
  face_neutral: "Neutral",
  face_soft_smile: "Soft Smile",
  face_surprised: "Surprised",
  face_concerned: "Concerned",
  face_closed: "Eyes Closed",
  face_wink: "Wink",
  face_spiral_blank: "Spiral Stare",
  face_spiral_smile: "Spiral Smile",
};

const faceSwatches = {
  ink: [64, 42, 66],
  white: [255, 241, 241],
  rose: [186, 76, 113],
  plum: [137, 42, 87],
  pupil: [75, 30, 66],
  glow: [246, 159, 178],
  brow: [151, 83, 118],
};

// A north-facing pixel decal rests inside the head. The wheel clip brings only
// its own decal forward, so the normal face returns when the clip stops.
function addExpressions(geo, atlas, width) {
  const clips = {};
  const bones = geo["minecraft:geometry"][0].bones;

  for (const [index, id] of Object.keys(expressions).entries()) {
    const name = `CustomExpression${index}`;
    const ox = 1800 + (index % 4) * 48;
    const oy = 400 + Math.floor(index / 4) * 24;
    const surprised = id === "face_surprised";
    const concerned = id === "face_concerned";
    const smiling = id.includes("smile") || id === "face_wink";
    const spiral = id.includes("spiral");
    function dot(x, y, swatch) {
      const offset = ((oy + y) * width + ox + x) * 4;
      atlas.set([...faceSwatches[swatch], 255], offset);
    }

    for (const center of [11, 36]) {
      const side = center < 24 ? -1 : 1;
      for (let x = -4; x <= 4; x++) {
        const browY = concerned ? 3 + Math.round((side * x) / 4) : 2;
        dot(center + x, browY + (surprised ? -1 : 0), "brow");
      }
      if (id === "face_closed" || (id === "face_wink" && side < 0)) {
        for (let x = -5; x <= 5; x++)
          dot(center + x, 12 - Math.floor((5 - Math.abs(x)) / 2), "ink");
        dot(center + side * 6, 13, "ink");
        continue;
      }

      for (let y = -6; y <= 6; y++) {
        for (let x = -6; x <= 6; x++) {
          const bottom = smiling ? 5 : 6;
          const top = surprised ? -6 : -5;
          if (y < top || y > bottom || Math.abs(x) + Math.abs(y) > 10) continue;
          const radius = Math.hypot(x, y * 0.8);
          let color = "white";
          if (radius < (surprised ? 3.8 : 4.8)) {
            color = y > 0 ? "rose" : "plum";
            if (spiral) {
              const angle = Math.atan2(y, x);
              const phase = radius * 2.1 - angle;
              color = radius < 1 || Math.cos(phase) > 0.45 ? "pupil" : "rose";
              if (x === -2 && y === -2) color = "glow";
            } else if (radius < 2.7) color = "pupil";
            if (!spiral && x === -2 && y === -2) color = "white";
          }
          if (y === top || (y === top + 1 && Math.abs(x) >= 4)) color = "ink";
          dot(center + x, y + 11, color);
        }
      }
    }

    for (let x = -2; x <= 2; x++) {
      const edge = Math.abs(x) === 2;
      if (surprised) {
        dot(24 + x, edge ? 21 : 20, "ink");
        dot(24 + x, edge ? 22 : 23, "plum");
        if (!edge) dot(24 + x, 22, "rose");
      } else {
        dot(
          24 + x,
          21 + (smiling && !edge ? 1 : concerned && edge ? 1 : 0),
          "ink",
        );
      }
    }

    bones.push({
      name,
      parent: "Head",
      pivot: [0, 33.5, -3.25],
      cubes: [
        {
          origin: [-3.36, 31.75, -3.25],
          size: [6.72, 3.36, 0.015],
          uv: { north: { uv: [ox, oy], uv_size: [48, 24] } },
        },
      ],
    });
    clips[id] = {
      loop: true,
      animation_length: 1,
      bones: {
        Eyes: { scale: 0 },
        Mouth: { scale: 0 },
        CustomRunFace: { scale: 0 },
        [name]: { position: [0, 0, -0.42] },
      },
    };
  }
  return clips;
}

module.exports = { addExpressions, expressions, faceSwatches };
