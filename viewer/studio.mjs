// Pure file parsing and playback state, also exercised by check:viewer.
export const mainClips = (animations) =>
  Object.keys(animations).filter(
    (name) => !/parallel|^gui$|——|^empty$|\$/.test(name),
  );
export function playback(animations) {
  return {
    clip: animations.idle ? "idle" : mainClips(animations)[0] || null,
    elapsed: 0,
    playing: true,
    rate: 1,
    loop: true,
    blink: true,
  };
}
export const durationOf = (model) =>
  Number(model.character.animations[model.clip]?.animation_length) || 1;
export function advance(model, dt) {
  if (!model.playing || !model.clip) return;
  const duration = durationOf(model);
  model.elapsed += dt * model.rate;
  if (model.elapsed >= duration) {
    if (model.loop) model.elapsed %= duration;
    else {
      model.elapsed = duration;
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
    throw Error("เลือกโฟลเดอร์โมเดล หรือโฟลเดอร์รวมที่มี ysm.json");
  return Promise.all(
    manifests.map(async (name) => {
      const base = name.slice(0, -"ysm.json".length);
      const info = JSON.parse(await entries.get(name).text());
      const player = info.files?.player;
      if (typeof player?.model?.main !== "string")
        throw Error(name + ": ไม่พบโมเดลหลัก");
      const get = (relative) => {
        const parts = (base + relative).replaceAll("\\", "/").split("/"),
          normalized = [];
        for (const part of parts) {
          if (part === "..") normalized.pop();
          else if (part && part !== ".") normalized.push(part);
        }
        const file = entries.get(normalized.join("/"));
        if (!file) throw Error(name + ": ไม่พบไฟล์ " + relative);
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
      if (!texture) throw Error(name + ": ไม่พบพื้นผิว");
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
