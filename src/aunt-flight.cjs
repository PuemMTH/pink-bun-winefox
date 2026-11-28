const turn = (pitch, yaw = 0, roll = 0) => ({ rotation: [pitch, yaw, roll] });
const riseAndFall = "math.sin(q.anim_time*300)";

module.exports = function auntFlight(elytra) {
  const { Root, MAllbody, AllBody } = elytra.bones;
  const headPitch = "math.clamp(0.65*ysm.head_pitch,-24,24)";
  const headYaw = "math.clamp(ysm.head_yaw,-24,24)";
  const headAim = turn(headPitch, headYaw);
  const glide = {
    loop: true,
    animation_length: 1.2,
    bones: {
      Root,
      MAllbody,
      AllBody,
      UpBody: turn(`-8+1.2*${riseAndFall}`),
      UpperBody: turn(-17),
      AllHead: turn(-14),
      MHead: headAim,
      Head: turn(-21),
      Bangs: turn(0, 0, `1.1*${riseAndFall}`),
      LongHair: turn(`18+2*${riseAndFall}`),
      // Keep the braid clear of the dress while it follows the head turn.
      AuntBraid: {
        ...turn(`-2-0.65*${headPitch}`, 0, `16+1.6*${riseAndFall}`),
        position: [0.9, 0, -1],
      },
      AuntBraidTip: turn("7+3*math.sin(q.anim_time*300-45)", 0, `-4+2*${riseAndFall}`),
      clothe: turn(`5+1.6*${riseAndFall}`, 0, `1.2*${riseAndFall}`),
      LeftArm: turn(`15+1.8*${riseAndFall}`, 0, 3),
      RightArm: turn(`14+1.5*${riseAndFall}`, 0, -3),
      LeftForeArm: turn(-8),
      RightForeArm: turn(-9),
      LeftLeg: turn(-6, 0, -1),
      RightLeg: turn(-8, 0, 1),
      LeftLowerLeg: turn(`9+1.6*${riseAndFall}`),
      RightLowerLeg: turn(`10-1.6*${riseAndFall}`),
      LeftFoot: turn(14),
      RightFoot: turn(12),
    },
  };

  const spread = {
    ...glide,
    bones: {
      ...glide.bones,
      LeftArm: turn(8, -5, `-41+2*${riseAndFall}`),
      RightArm: turn(8, 5, `41-2*${riseAndFall}`),
      LeftForeArm: turn(-13),
      RightForeArm: turn(-13),
    },
  };
  const lead = {
    ...glide,
    bones: {
      ...glide.bones,
      RightArm: turn(`-146+1.5*${riseAndFall}`, 9, -50),
      RightForeArm: turn(-12),
      UpBody: turn(-8, 0, -5),
      Head: turn(-21, 5, 3),
    },
  };
  const creative = {
    loop: true,
    animation_length: 1.2,
    bones: {
      Root: { position: [0, `0.65+0.28*${riseAndFall}`, 0] },
      AllBody: turn("math.clamp(query.ground_speed*1.25,0,14)", 0, `1.2*${riseAndFall}`),
      UpBody: turn(-3),
      MHead: headAim,
      Head: turn(-3, 0, `-0.8*${riseAndFall}`),
      LongHair: turn(4, 0, `1.5*${riseAndFall}`),
      AuntBraid: {
        ...turn(
          `-18-0.9*${headPitch}`,
          `-0.25*${headYaw}`,
          `13+1.3*${riseAndFall}`,
        ),
        position: [1.1, 0, -0.85],
      },
      AuntBraidTip: turn(7, 0, "2*math.sin(q.anim_time*300-45)"),
      clothe: turn(`4+1.2*${riseAndFall}`, 0, `1.4*${riseAndFall}`),
      LeftArm: turn(6, 0, `-5+1.6*${riseAndFall}`),
      RightArm: turn(5, 0, `5-1.6*${riseAndFall}`),
      LeftForeArm: turn(-11),
      RightForeArm: turn(-9),
      LeftLeg: turn(-5, 0, -1),
      RightLeg: turn(1, 0, 2),
      LeftLowerLeg: turn(11),
      RightLowerLeg: turn(8),
      LeftFoot: turn(8),
      RightFoot: turn(10),
    },
  };
  return {
    glide,
    creative,
    alternatives: [
      {
        clip: "studio_flight_spread",
        label: "Open-Arm Glide",
        description: "Both arms spread to frame the dress and braid in the front view.",
        animation: spread,
      },
      {
        clip: "studio_flight_lead",
        label: "Leading Hand",
        description: "The right arm reaches forward as the body banks slightly.",
        animation: lead,
      },
    ],
  };
};
