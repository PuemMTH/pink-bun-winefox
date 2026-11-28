const assert = require("node:assert/strict");

const turn = (pitch, yaw = 0, roll = 0) => ({ rotation: [pitch, yaw, roll] });
const wave = "math.sin(q.anim_time*300)";
const drift = "math.sin(q.anim_time*240)";

module.exports = function satouFlight({ geo, animations, outfit }) {
  assert(outfit === "school" || outfit === "white", "Unknown flight outfit");
  const school = outfit === "school";
  const { elytra_fly: oldGlide } = animations.animations;
  const headPitch = "math.clamp(0.65*ysm.head_pitch,-24,24)";
  const headYaw = "math.clamp(ysm.head_yaw,-34,34)";
  const headAim = turn(headPitch, headYaw);
  // Keep the trailing locks aligned with the airflow while the head aims.
  const trailYaw = turn(0, `-${headYaw}`);
  // End sprint-only eye effects cleanly when entering flight.
  const faceState = {
    weixiao: { position: [0, 0, -1] },
    CustomRunFace: { scale: 0 },
    CustomRunIrisLeft: { scale: 0 },
    CustomRunIrisRight: { scale: 0 },
    Mouth: { scale: 1 },
    LeftEyelidBase: { scale: 1 },
    RightEyelidBase: { scale: 1 },
  };
  const glide = {
    loop: true,
    animation_length: 1.2,
    bones: {
      Root: structuredClone(oldGlide.bones.Root),
      AllBody: turn(0, "1.5*v.L6_P0", `${school ? 1 : 3}*${wave}+0.6*v.L6_P0`),
      UpBody: turn(school ? -9 : -6),
      UpperBody: turn(school ? -16 : -19, 0, `1.1*${wave}`),
      AllHead: turn(-16),
      MHead: headAim,
      Head: turn(-24),
      Bangs: turn(0, 0, `1.2*${wave}`),
      MLongHair: trailYaw,
      MLongLeftHair: trailYaw,
      MLongRightHair: trailYaw,
      LongHair: turn(`47-${headPitch}+2*${wave}`),
      bone20: turn(`-25+2.5*${wave}`),
      LongLeftHair: {
        ...turn(`${school ? 49 : 64}-${headPitch}+2*math.sin(q.anim_time*300+32)`, 0, school ? 12 : 4),
        position: [0, 0, school ? 1.8 : 0],
      },
      LongRightHair: {
        ...turn(`${school ? 49 : 64}-${headPitch}+2*math.sin(q.anim_time*300-32)`, 0, school ? -12 : -4),
        position: [0, 0, school ? 1.8 : 0],
      },
      LeftArm: school ? turn(`-25+1.8*${wave}`, 1, -11) : turn(`-22+2*${wave}`, -7, -26),
      RightArm: school ? turn(`-20+1.4*${wave}`, -1, 11) : turn(`-18-2*${wave}`, 5, 29),
      LeftForeArm: turn(school ? -12 : -15),
      RightForeArm: turn(school ? -9 : -17),
      LeftLeg: turn(school ? -4 : -5),
      RightLeg: turn(school ? -6 : -5),
      LeftLowerLeg: turn(`8+1.3*${wave}`),
      RightLowerLeg: turn(`11-1.3*${wave}`),
      LeftFoot: turn(13),
      RightFoot: turn(10),
      ...faceState,
    },
  };
  const creative = {
    loop: true,
    animation_length: 1.5,
    bones: {
      Root: { position: [0, `${school ? 0.5 : 0.66}+0.27*${drift}`, 0] },
      AllBody: turn(
        school
          ? "math.clamp(query.ground_speed*1.35,0,15)"
          : "math.clamp(query.ground_speed,0,12)",
        0,
        `${school ? 0.8 : 2}*${drift}`,
      ),
      UpBody: turn(-2),
      MHead: headAim,
      Head: turn(-3, 0, `-1*${drift}`),
      MLongHair: trailYaw,
      MLongLeftHair: trailYaw,
      MLongRightHair: trailYaw,
      LongHair: turn(`16-${headPitch}+2*${drift}`),
      LongLeftHair: turn(
        `${school ? 22 : 32}-${headPitch}+2*math.sin(q.anim_time*240+32)`, 0, school ? 0 : 4,
      ),
      LongRightHair: turn(
        `${school ? 22 : 32}-${headPitch}+2*math.sin(q.anim_time*240-32)`, 0, school ? 0 : -4,
      ),
      LeftArm: school ? turn(-26, 1, -2) : turn(-13, -4, `-11+2*${drift}`),
      RightArm: school ? turn(-23, -1, 2) : turn(-18, 4, `13-2*${drift}`),
      LeftForeArm: turn(school ? -16 : -10),
      RightForeArm: turn(school ? -12 : -15),
      LeftLeg: turn(-3),
      RightLeg: turn(school ? -6 : -3),
      LeftLowerLeg: turn(`9+1.3*${drift}`),
      RightLowerLeg: turn(`12-1.3*${drift}`),
      LeftFoot: turn(7),
      RightFoot: turn(10),
      ...faceState,
    },
  };
  // Keep the skirt and lining on their shared hip pivot through both clips.
  if (school) {
    glide.bones.cloth = turn(-5);
    creative.bones.cloth = turn(-4);
    // Seat the ribbon knot closer to the collar while the tails clear the vest.
    for (const { bones } of [glide, creative]) {
      bones.bow = { position: [0, 0, 0.35] };
      bones.bowL1 = { position: [0, 0, -0.28] };
      bones.bowR1 = { position: [0, 0, -0.28] };
    }
  }

  const boneNames = new Set(geo["minecraft:geometry"][0].bones.map(({ name }) => name));
  for (const clip of [glide, creative])
    for (const name of Object.keys(clip.bones))
      assert(boneNames.has(name), `Flight animation uses missing bone: ${name}`);
  animations.animations.elytra_fly = glide;
  animations.animations.fly = creative;
};
