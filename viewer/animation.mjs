// Bedrock/Molang subset used by this model. No eval or execution of imported code.
const radians = Math.PI / 180;
const functions = {
  sin: (x) => Math.sin(x * radians),
  cos: (x) => Math.cos(x * radians),
  abs: Math.abs,
  floor: Math.floor,
  ceil: Math.ceil,
  round: Math.round,
  sqrt: Math.sqrt,
  pow: Math.pow,
  exp: Math.exp,
  min: Math.min,
  max: Math.max,
  clamp: (x, lo, hi) => Math.max(lo, Math.min(hi, x)),
  lerp: (a, b, t) => a + (b - a) * t,
  mod: (a, b) => a % b,
  pi: Math.PI,
};
const precedence = {
  "||": 1,
  "&&": 2,
  "==": 3,
  "!=": 3,
  "<": 4,
  ">": 4,
  "<=": 4,
  ">=": 4,
  "+": 5,
  "-": 5,
  "*": 6,
  "/": 6,
  "%": 6,
};
const cache = new Map();

function compile(source) {
  const tokens =
    String(source).match(
      /(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?|[a-z_]\w*(?:\.\w+)*|&&|\|\||==|!=|<=|>=|[+\-*/%()!,?:<>]/gi,
    ) || [];
  let index = 0;
  function expression(level = 0) {
    let token = tokens[index++],
      left;
    if (["-", "+", "!"].includes(token)) {
      const value = expression(7);
      left = (ctx) =>
        token === "-" ? -value(ctx) : token === "!" ? +!value(ctx) : value(ctx);
    } else if (token === "(") {
      left = expression();
      if (tokens[index++] !== ")") throw Error("Unbalanced expression");
    } else if (token && /^\d|^\./.test(token)) {
      const value = Number(token);
      left = () => value;
    } else if (token) {
      const name = token.toLowerCase();
      if (tokens[index] === "(") {
        index++;
        const args = [];
        if (tokens[index] !== ")")
          do {
            args.push(expression());
          } while (tokens[index] === "," && ++index);
        if (tokens[index++] !== ")") throw Error("Unbalanced call");
        const fn = functions[name.replace(/^math\./, "")];
        left = (ctx) =>
          typeof fn === "function" ? fn(...args.map((f) => f(ctx))) : 0;
      } else
        left = (ctx) =>
          name === "true"
            ? 1
            : name === "false"
              ? 0
              : name === "math.pi"
                ? Math.PI
                : (ctx[name] ?? 0);
    } else throw Error("Empty expression");
    while (
      precedence[tokens[index]] !== undefined &&
      precedence[tokens[index]] >= level
    ) {
      const op = tokens[index++],
        a = left,
        b = expression(precedence[op] + 1);
      left = (ctx) => {
        const x = a(ctx),
          y = b(ctx);
        switch (op) {
          case "+":
            return x + y;
          case "-":
            return x - y;
          case "*":
            return x * y;
          case "/":
            return y ? x / y : 0;
          case "%":
            return y ? x % y : 0;
          case "<":
            return +(x < y);
          case ">":
            return +(x > y);
          case "<=":
            return +(x <= y);
          case ">=":
            return +(x >= y);
          case "==":
            return +(x === y);
          case "!=":
            return +(x !== y);
          case "&&":
            return +(!!x && !!y);
          case "||":
            return +(!!x || !!y);
        }
      };
    }
    if (level === 0 && tokens[index] === "?") {
      index++;
      const condition = left,
        yes = expression();
      if (tokens[index++] !== ":") throw Error("Incomplete conditional");
      const no = expression();
      left = (ctx) => (condition(ctx) ? yes(ctx) : no(ctx));
    }
    return left;
  }
  // Stateful physics expressions are deliberately not interpreted as JavaScript.
  if (/[;=]/.test(String(source).replace(/==|!=|<=|>=/g, ""))) return () => 0;
  const result = expression();
  if (index !== tokens.length) throw Error("Unsupported expression");
  return result;
}

export function evaluate(value, context = {}) {
  if (typeof value === "number") return value;
  if (typeof value !== "string") return 0;
  if (!cache.has(value)) {
    try {
      cache.set(value, compile(value));
    } catch {
      cache.set(value, () => 0);
    }
  }
  const result = cache.get(value)(context);
  return Number.isFinite(result) ? result : 0;
}

function vector(value, context, fallback) {
  if (Array.isArray(value))
    return [0, 1, 2].map((i) => evaluate(value[i] ?? fallback[i], context));
  if (value !== undefined && value !== null)
    return Array(3).fill(evaluate(value, context));
  return [...fallback];
}
function endpoint(frame, field, context, fallback) {
  if (Array.isArray(frame) || typeof frame !== "object")
    return vector(frame, context, fallback);
  return vector(frame[field] ?? frame.post ?? frame.pre, context, fallback);
}
const frameCache = new WeakMap();
export function sample(channel, time, context = {}, fallback = [0, 0, 0]) {
  if (channel == null) return [...fallback];
  if (Array.isArray(channel) || typeof channel !== "object")
    return vector(channel, context, fallback);
  if ("post" in channel || "pre" in channel)
    return endpoint(channel, "post", context, fallback);
  if (!frameCache.has(channel))
    frameCache.set(
      channel,
      Object.entries(channel)
        .map(([t, v]) => ({ time: Number(t), value: v }))
        .filter((f) => Number.isFinite(f.time))
        .sort((a, b) => a.time - b.time),
    );
  const frames = frameCache.get(channel);
  if (!frames.length) return [...fallback];
  if (time <= frames[0].time)
    return endpoint(frames[0].value, "post", context, fallback);
  const end = frames.length - 1;
  if (time >= frames[end].time)
    return endpoint(frames[end].value, "post", context, fallback);
  let next = 1;
  while (frames[next].time < time) next++;
  if (Math.abs(frames[next].time - time) < 1e-8)
    return endpoint(frames[next].value, "post", context, fallback);
  const first = frames[next - 1],
    last = frames[next],
    t = (time - first.time) / (last.time - first.time);
  const a = endpoint(first.value, "post", context, fallback),
    b = endpoint(last.value, "pre", context, fallback);
  const interpolation = last.value?.lerp_mode || first.value?.lerp_mode;
  if (interpolation === "step") return a;
  if (interpolation === "catmullrom") {
    const p = endpoint(
      frames[Math.max(0, next - 2)].value,
      "post",
      context,
      fallback,
    );
    const n = endpoint(
      frames[Math.min(end, next + 1)].value,
      "pre",
      context,
      fallback,
    );
    return a.map(
      (v, i) =>
        0.5 *
        (2 * v +
          (-p[i] + b[i]) * t +
          (2 * p[i] - 5 * v + 4 * b[i] - n[i]) * t * t +
          (-p[i] + 3 * v - 3 * b[i] + n[i]) * t * t * t),
    );
  }
  return a.map((v, i) => v + (b[i] - v) * t);
}

export function animationContext(time, state = {}) {
  return {
    "query.anim_time": time,
    "q.anim_time": time,
    "query.ground_speed": state.speed ?? 0,
    "q.ground_speed": state.speed ?? 0,
    "ysm.food_level": 20,
    "ysm.head_yaw": state.headYaw ?? 0,
    "ysm.head_pitch": state.headPitch ?? 0,
    "ysm.has_mainhand": 0,
    "ysm.has_offhand": 0,
    "query.is_on_ground": 1,
    "query.is_sprinting": +(state.clip === "run"),
    ...state.variables,
  };
}

export function poseFor(
  animations,
  clip,
  time,
  { blink = true, layerTime = time, ...state } = {},
) {
  const result = new Map();
  const layers = [
    "pre_parallel0",
    "pre_parallel1",
    ...(blink ? ["pre_parallel3"] : []),
    clip,
    "parallel0",
  ];
  for (const name of layers) {
    const animation = animations[name];
    if (!animation) continue;
    const duration = Number(animation.animation_length);
    const localTime =
      name === clip ? time : duration > 0 && animation.loop ? layerTime % duration : layerTime;
    const context = animationContext(localTime, { ...state, clip });
    // Some YSM rigs combine blink tracks and hair motion in pre_parallel1.
    const skipBlink = !blink && name === "pre_parallel1" &&
      typeof animation.bones?.LeftEyelid?.scale === "object";
    for (const [bone, channels] of Object.entries(animation.bones || {})) {
      if (skipBlink && /^(Left|Right)(Eyebrow|Eyelid|EyeDot)$/.test(bone))
        continue;
      if (!result.has(bone)) result.set(bone, {});
      const pose = result.get(bone);
      for (const kind of ["rotation", "position", "scale"])
        if (channels[kind] !== undefined)
          pose[kind] = sample(
            channels[kind],
            localTime,
            context,
            kind === "scale" ? [1, 1, 1] : [0, 0, 0],
          );
    }
  }
  return result;
}
