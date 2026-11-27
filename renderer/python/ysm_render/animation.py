"""Bedrock keyframes and the same safe Molang subset used by Model Studio."""

from functools import lru_cache
import math
import re

_TOKEN = re.compile(
    r"(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?|[a-z_]\w*(?:\.\w+)*|&&|\|\||==|!=|<=|>=|[+\-*/%()!,?:<>]",
    re.I,
)
_PRECEDENCE = {
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
}
_FUNCTIONS = {
    "sin": lambda x: math.sin(math.radians(x)),
    "cos": lambda x: math.cos(math.radians(x)),
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": lambda x: math.floor(x + 0.5),
    "sqrt": math.sqrt,
    "pow": math.pow,
    "exp": math.exp,
    "min": lambda *args: min(args) if args else math.inf,
    "max": lambda *args: max(args) if args else -math.inf,
    "mod": math.fmod,
    "clamp": lambda x, lo, hi: max(lo, min(hi, x)),
    "lerp": lambda a, b, t: a + (b - a) * t,
}


@lru_cache(maxsize=4096)
def _compile(source):
    # Never execute imported expressions, assignments or stateful native physics.
    matches = list(_TOKEN.finditer(source))
    cursor = 0
    for match in matches:
        if source[cursor : match.start()].strip():
            raise ValueError("Unsupported Molang syntax")
        cursor = match.end()
    if source[cursor:].strip() or len(matches) > 1024:
        raise ValueError("Unsupported Molang syntax")
    tokens = [m.group().lower() for m in matches]
    index = 0

    def take():
        nonlocal index
        if index >= len(tokens):
            raise ValueError("Incomplete expression")
        token = tokens[index]
        index += 1
        return token

    def peek():
        return tokens[index] if index < len(tokens) else None

    def expression(level=0):
        token = take()
        if token in ("-", "+", "!"):
            node = ("unary", token, expression(7))
        elif token == "(":
            node = expression()
            if take() != ")":
                raise ValueError("Unbalanced expression")
        elif token[0].isdigit() or token[0] == ".":
            node = ("number", float(token))
        elif re.fullmatch(r"[a-z_]\w*(?:\.\w+)*", token):
            if peek() == "(":
                take()
                args = []
                if peek() != ")":
                    args.append(expression())
                    while peek() == ",":
                        take()
                        args.append(expression())
                if take() != ")":
                    raise ValueError("Unbalanced call")
                node = ("call", token.removeprefix("math."), args)
            else:
                node = ("variable", token)
        else:
            raise ValueError("Unsupported token")
        while peek() in _PRECEDENCE and _PRECEDENCE[peek()] >= level:
            op = take()
            node = ("binary", op, node, expression(_PRECEDENCE[op] + 1))
        if level == 0 and peek() == "?":
            take()
            yes = expression()
            if take() != ":":
                raise ValueError("Incomplete conditional")
            node = ("conditional", node, yes, expression())
        return node

    result = expression()
    if index != len(tokens):
        raise ValueError("Unsupported expression")
    return result


def _run(node, context):
    kind, *parts = node
    if kind == "number":
        return parts[0]
    if kind == "variable":
        return {"true": 1, "false": 0, "math.pi": math.pi}.get(
            parts[0], context.get(parts[0], 0)
        )
    if kind == "call":
        fn = _FUNCTIONS.get(parts[0])
        return fn(*[_run(arg, context) for arg in parts[1]]) if fn else 0
    if kind == "conditional":
        return _run(parts[1] if _run(parts[0], context) else parts[2], context)
    if kind == "unary":
        value = _run(parts[1], context)
        return (
            -value if parts[0] == "-" else int(not value) if parts[0] == "!" else value
        )
    op, left, right = parts
    a, b = _run(left, context), _run(right, context)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b if b else 0
    if op == "%":
        return math.fmod(a, b) if b else 0
    if op == "<":
        return int(a < b)
    if op == ">":
        return int(a > b)
    if op == "<=":
        return int(a <= b)
    if op == ">=":
        return int(a >= b)
    if op == "==":
        return int(a == b)
    if op == "!=":
        return int(a != b)
    if op == "&&":
        return int(bool(a) and bool(b))
    if op == "||":
        return int(bool(a) or bool(b))
    return 0


def evaluate(value, context=None):
    try:
        result = (
            value
            if isinstance(value, (int, float))
            else _run(_compile(value), context or {}) if isinstance(value, str) else 0
        )
        return float(result) if math.isfinite(result) else 0.0
    except (ValueError, TypeError, OverflowError, ZeroDivisionError, RecursionError):
        return 0.0


def _vector(value, context, fallback):
    if isinstance(value, list):
        return [
            evaluate(value[i] if i < len(value) else fallback[i], context)
            for i in range(3)
        ]
    return [evaluate(value, context)] * 3 if value is not None else list(fallback)


def _endpoint(frame, field, context, fallback):
    if isinstance(frame, dict):
        frame = next(
            (frame[k] for k in (field, "post", "pre") if frame.get(k) is not None), None
        )
    return _vector(frame, context, fallback)


def sample(channel, time, context=None, fallback=(0, 0, 0)):
    context = context or {}
    if not isinstance(channel, dict):
        return _vector(channel, context, fallback)
    if "post" in channel or "pre" in channel:
        return _endpoint(channel, "post", context, fallback)
    frames = []
    for key, value in channel.items():
        try:
            t = float(key)
            if math.isfinite(t):
                frames.append((t, value))
        except (ValueError, TypeError):
            continue
    frames.sort(key=lambda f: f[0])
    if not frames:
        return list(fallback)
    if time <= frames[0][0]:
        return _endpoint(frames[0][1], "post", context, fallback)
    if time >= frames[-1][0]:
        return _endpoint(frames[-1][1], "post", context, fallback)
    next_index = next(i for i in range(1, len(frames)) if frames[i][0] >= time)
    if abs(frames[next_index][0] - time) < 1e-8:
        return _endpoint(frames[next_index][1], "post", context, fallback)
    start, end = frames[next_index - 1], frames[next_index]
    t = (time - start[0]) / (end[0] - start[0])
    a = _endpoint(start[1], "post", context, fallback)
    b = _endpoint(end[1], "pre", context, fallback)
    mode = (end[1].get("lerp_mode") if isinstance(end[1], dict) else None) or (
        start[1].get("lerp_mode") if isinstance(start[1], dict) else None
    )
    if mode == "step":
        return a
    if mode == "catmullrom":
        p = _endpoint(frames[max(0, next_index - 2)][1], "post", context, fallback)
        n = _endpoint(
            frames[min(len(frames) - 1, next_index + 1)][1], "pre", context, fallback
        )
        return [
            0.5
            * (
                2 * v
                + (-p[i] + b[i]) * t
                + (2 * p[i] - 5 * v + 4 * b[i] - n[i]) * t * t
                + (-p[i] + 3 * v - 3 * b[i] + n[i]) * t * t * t
            )
            for i, v in enumerate(a)
        ]
    return [v + (b[i] - v) * t for i, v in enumerate(a)]


def pose_for(
    animations,
    clip,
    time,
    *,
    blink=True,
    speed=0,
    head_yaw=0,
    head_pitch=0,
    variables=None
):
    result = {}
    for name in [
        "pre_parallel0",
        "pre_parallel1",
        *(["pre_parallel3"] if blink else []),
        clip,
    ]:
        animation = animations.get(name)
        if not animation:
            continue
        duration = float(animation.get("animation_length", 1)) or 1
        local_time = time if name == clip else time % duration
        context = {
            "query.anim_time": local_time,
            "q.anim_time": local_time,
            "query.ground_speed": speed,
            "q.ground_speed": speed,
            "ysm.food_level": 20,
            "ysm.head_yaw": head_yaw,
            "ysm.head_pitch": head_pitch,
            "ysm.has_mainhand": 0,
            "ysm.has_offhand": 0,
            "query.is_on_ground": 1,
            "query.is_sprinting": int(clip == "run"),
            **(variables or {}),
        }
        for bone, channels in animation.get("bones", {}).items():
            target = result.setdefault(bone, {})
            for kind in ("rotation", "position", "scale"):
                if kind in channels:
                    target[kind] = sample(
                        channels[kind],
                        local_time,
                        context,
                        (1, 1, 1) if kind == "scale" else (0, 0, 0),
                    )
    return result
