import { poseFor } from "./animation.mjs";

// Browser-only photo poses for the Wine Fox humanoid rig, in Bedrock degrees.
// Forearms bend at the existing elbow; the block hands have no finger joints.
const poses = {
  studio_photo_wave: {
    label: "ยกมือทักทาย",
    rotations: {
      UpperBody: [0, -10, 2],
      Head: [0, 10, -6],
      LeftArm: [15, -50, -97],
      LeftForeArm: [-85, 0, 0],
      RightArm: [15, -60, 27],
      RightForeArm: [-100, 0, 0],
      LeftLeg: [0, 0, -2],
      RightLeg: [6, 0, 3],
      RightLowerLeg: [18, 0, 0],
    },
  },
  studio_photo_cheeks: {
    label: "มือแนบแก้ม",
    rotations: {
      UpperBody: [0, 0, 0],
      Head: [0, 0, 5],
      LeftArm: [-20, -40, -42],
      LeftForeArm: [-125, 0, 0],
      RightArm: [-20, 40, 42],
      RightForeArm: [-125, 0, 0],
      LeftLeg: [0, 0, 1],
      RightLeg: [0, 0, -1],
    },
  },
  studio_photo_hip: {
    label: "เท้าเอวเอียงตัว",
    rotations: {
      UpperBody: [0, 12, -4],
      Head: [0, -12, 7],
      LeftArm: [15, 60, -27],
      LeftForeArm: [-100, 0, 0],
      RightArm: [-5, 0, -3],
      RightForeArm: [-12, 0, 0],
      LeftLeg: [0, 0, -2],
      RightLeg: [4, -5, 4],
      RightLowerLeg: [8, 0, 0],
    },
  },
  studio_photo_shy: {
    label: "ประสานมือเขิน",
    rotations: {
      UpperBody: [3, 0, 2],
      Head: [7, -8, -7],
      LeftArm: [-20, 60, -12],
      LeftForeArm: [-45, 0, 0],
      RightArm: [-20, -60, 12],
      RightForeArm: [-45, 0, 0],
      LeftLeg: [0, -3, 1],
      RightLeg: [0, 3, -1],
    },
  },
  studio_photo_chest: {
    label: "มือแนบอก",
    rotations: {
      UpperBody: [-2, -5, 0],
      Head: [-3, 5, 7],
      LeftArm: [-10, 30, -27],
      LeftForeArm: [-130, 0, 0],
      RightArm: [-10, -30, 27],
      RightForeArm: [-130, 0, 0],
      LeftLeg: [0, 0, 0],
      RightLeg: [0, 0, 0],
    },
  },
  studio_photo_open: {
    label: "กางแขนสดใส",
    rotations: {
      UpperBody: [0, -8, -5],
      Head: [-3, 8, 8],
      LeftArm: [-12, 0, -56],
      LeftForeArm: [-8, 0, 0],
      RightArm: [-12, 0, 56],
      RightForeArm: [-8, 0, 0],
      LeftLeg: [0, 0, -3],
      RightLeg: [6, -5, 6],
      RightLowerLeg: [30, 0, 0],
    },
  },
};
export const photoPoseLabels = Object.fromEntries(
  Object.entries(poses).map(([id, pose]) => [id, pose.label]),
);
export const isPhotoPose = (clip) => Object.hasOwn(poses, clip);
export const photoClips = (animations) =>
  Object.keys(poses).filter((id) => animations[id]);

export function makePhotoAnimations(animations, boneNames) {
  const names = new Set(boneNames);
  if (!animations.idle) return {};
  if (
    ![
      "Head",
      "UpperBody",
      "LeftArm",
      "RightArm",
      "LeftForeArm",
      "RightForeArm",
      "LeftLeg",
      "RightLeg",
    ].every((name) => names.has(name))
  )
    return {};
  const neutral = Object.fromEntries(
    poseFor(animations, "idle", 1, { blink: false }),
  );
  const generated = {};
  for (const [id, pose] of Object.entries(poses)) {
    if (animations[id]) continue;
    const bones = { ...neutral };
    for (const [name, rotation] of Object.entries(pose.rotations))
      if (names.has(name)) bones[name] = { ...bones[name], rotation };
    // Photo cards keep eyes open; normal animation blinking is unchanged.
    for (const name of ["LeftEyelid", "RightEyelid"])
      if (names.has(name)) bones[name] = { ...bones[name], scale: [1, 1, 1] };
    generated[id] = { loop: true, animation_length: 1, bones };
  }
  return generated;
}
