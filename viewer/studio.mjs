// Pure file parsing and playback state, also exercised by check:viewer.
import { photoClips } from "./photo-poses.mjs";
export const mainClips = (animations) =>
  Object.keys(animations).filter(
    (name) => !/parallel|^gui$|——|^empty$|\$/.test(name),
  );
export const poseClips = (animations) =>
  [
    ...new Set([
      ...photoClips(animations),
      "idle",
      "walk",
      "run",
      "jump",
      "sneak",
      "sit",
      ...mainClips(animations),
    ]),
  ].filter((name) => animations[name]);
export function playback(animations) {
  return {
    clip: animations.idle ? "idle" : mainClips(animations)[0] || null,
    elapsed: 0,
    layerTime: 0,
    playing: true,
    rate: 1,
    loop: true,
    blink: true,
  };
}
export const durationOf = (model, clip = model.clip) =>
  Number(model.character.animations[clip]?.animation_length) || 1;
export function advance(model, dt, duration = durationOf(model)) {
  if (!model.playing || !model.clip) return;
  const step = dt * model.rate;
  const elapsed = model.loop ? model.elapsed + step : Math.min(duration, model.elapsed + step);
  model.layerTime = (model.layerTime ?? model.elapsed) + (elapsed - model.elapsed);
  model.elapsed = elapsed;
  if (model.elapsed >= duration) {
    if (model.loop) model.elapsed %= duration;
    else {
      model.playing = false;
    }
  }
}
export const shownIn = (model, selection) =>
  model.visible && (selection === "all" || String(model.id) === selection);
export async function readModelFolders(files, manifest) {
  const entries = new Map(
    [...files].map((file) => [
      (file.webkitRelativePath || file.name).replaceAll("\\", "/"),
      file,
    ]),
  );
  const manifests = [...entries.keys()].filter(
    (name) =>
      (name === "ysm.json" || name.endsWith("/ysm.json")) &&
      (!manifest || name === manifest),
  );
  if (!manifests.length)
    throw Error("Choose a YSM model folder or a parent that contains ysm.json");
  return Promise.all(
    manifests.map(async (name) => {
      const base = name.slice(0, -"ysm.json".length);
      const info = JSON.parse(await entries.get(name).text());
      const player = info.files?.player;
      if (typeof player?.model?.main !== "string")
        throw Error(name + ": Missing the main model");
      const get = (relative) => {
        const parts = (base + relative).replaceAll("\\", "/").split("/"),
          normalized = [];
        for (const part of parts) {
          if (part === "..") normalized.pop();
          else if (part && part !== ".") normalized.push(part);
        }
        const file = entries.get(normalized.join("/"));
        if (!file) throw Error(name + ": Missing file " + relative);
        return file;
      };
      const geometry = JSON.parse(await get(player.model.main).text()),
        animations = { animations: {} };
      for (const file of Object.values(player.animation || {})) {
        const data = JSON.parse(await get(file).text());
        Object.assign(animations.animations, data.animations || {});
      }
      const choice = player.texture?.[0],
        texture = typeof choice === "string" ? choice : choice?.uv;
      if (!texture) throw Error(name + ": Missing texture");
      return {
        geometry,
        animations,
        info,
        texture: get(texture),
        source: { files, manifest: name },
      };
    }),
  );
}
