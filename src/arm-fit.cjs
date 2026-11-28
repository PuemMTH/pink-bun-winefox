module.exports = function fitWheelArms(clips) {
  // The left sleeve passes through the chest at the crest of this dance move.
  // Open the shoulder yaw at the two keys surrounding the contact.
  const shoulder = clips.extra7.bones.LeftArm.rotation;
  shoulder["4.875"].post[1] -= 8;
  shoulder["4.9167"][1] -= 8;
};
