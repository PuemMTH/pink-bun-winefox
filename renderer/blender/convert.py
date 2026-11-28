"""Convert the built YSM assets into a rigid Blender armature and baked actions."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys


MAIN_CLIPS = [
    "idle",
    "walk",
    "run",
    "jump",
    "fly",
    "elytra_fly",
    "attacked",
    "death",
    "sneak",
    "sneaking",
    "swim",
    "swim_stand",
    "sit",
    "ride",
    "ride_pig",
    "sleep",
    "boat",
    "climb",
    "climbing",
    "use_mainhand",
    "use_offhand",
    "swing_hand",
    "hover_fadeout",
    "hover",
    "focus",
]
FACE_CLIPS = [
    "face_neutral",
    "face_soft_smile",
    "face_surprised",
    "face_concerned",
    "face_closed",
    "face_wink",
    "face_spiral_blank",
    "face_spiral_smile",
]
PHOTO_CLIPS = [
    "studio_photo_" + pose for pose in ("wave", "cheeks", "hip", "shy", "chest", "open")
]
CLIPS = MAIN_CLIPS + ["extra" + str(i) for i in range(8)] + PHOTO_CLIPS + FACE_CLIPS


def variables_for(clip, time):
    variables = {}
    if clip == "jump":
        variables = {
            "query.vertical_speed": 8 - 20 * min(0.75, time),
            "query.is_on_ground": 0,
        }
    if clip == "extra0":
        variables["v.roaming.a"] = int(time >= 1.2083)
    return variables


def prepare_model(root, model_dir, destination):
    """Run under regular Python, sharing the established YSM geometry adapter."""
    sys.path.insert(0, str(root / "renderer/python"))
    from ysm_render import load_model

    model_dir = model_dir.resolve()
    model = load_model(model_dir)
    metadata = json.loads((model_dir / "ysm.json").read_text(encoding="utf-8"))
    texture = metadata["files"]["player"]["texture"][0]
    texture = texture if isinstance(texture, str) else texture["uv"]
    payload = {
        "name": model.name,
        "model_directory": str(model_dir),
        "texture": str(model_dir / texture),
        "metadata": metadata,
        "bones": list(model.bones.values()),
        "scale": model.scale.tolist(),
        "animations": model.animations,
        "parts": [
            dict(bone=name, vertices=points.tolist(), start=start)
            for name, points, start in model._parts
        ],
        "uvs": model._uvs.tolist(),
        "triangles": model._triangles.tolist(),
        "cube_count": model.cube_count,
        "checks": [],
        "clip_ids": [clip for clip in CLIPS if clip in model.animations],
        "review_clips_not_in_source": [clip for clip in CLIPS if clip not in model.animations],
    }
    for clip, time in [
        ("idle", 1),
        ("run", 0.2),
        ("jump", 0.4),
        ("sit", 0),
        ("extra7", 4.8917),
        ("studio_photo_cheeks", 0),
        ("face_spiral_blank", 0),
        ("face_neutral", 0),
    ]:
        if clip not in model.animations:
            continue
        time = min(time, float(model.animations[clip].get('animation_length', 1)) or 1)
        mesh = model.mesh(
            clip, time, loop=False, blink=False, variables=variables_for(clip, time)
        )
        payload["checks"].append(
            dict(clip=clip, time=time, vertices=mesh.vertices.tolist())
        )
    assert all(clip in model.animations for clip in ['idle','walk','run','jump','sit'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(
        f"Prepared {model.name}: {model.cube_count} cubes, {model.triangle_count} triangles"
    )


def load_sampler(root):
    spec = importlib.util.spec_from_file_location(
        "ysm_animation_sampler", root / "renderer/python/ysm_render/animation.py"
    )
    sampler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sampler)
    return sampler.pose_for


def bposition(point):
    """Existing adapter Y-up coordinates to Blender Z-up, maintaining handedness."""
    return point[0], -point[2], point[1]


def pivot(bone):
    x, y, z = bone.get("pivot", [0, 0, 0])
    return -x / 16, -z / 16, y / 16


def channels(bone, pose):
    loc = pose.get("position", [0, 0, 0])
    rot = [
        a + b
        for a, b in zip(
            bone.get("rotation", [0, 0, 0]), pose.get("rotation", [0, 0, 0])
        )
    ]
    scl = pose.get("scale", [1, 1, 1])
    return [
        -loc[0] / 16,
        -loc[2] / 16,
        loc[1] / 16,
        -math.radians(rot[0]),
        -math.radians(rot[2]),
        -math.radians(rot[1]),
        scl[0],
        scl[2],
        scl[1],
    ]


def make_material(payload):
    import bpy

    texture = bpy.data.images.load(payload["texture"], check_existing=True)
    texture.pack()
    texture.filepath = "//textures/pink_bun.png"
    material = bpy.data.materials.new(payload["name"] + " - Pixel atlas")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    image = nodes.new("ShaderNodeTexImage")
    image.image = texture
    image.interpolation = "Closest"
    image.extension = "CLIP"
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Roughness"].default_value = 1
    shader.inputs["Specular IOR Level"].default_value = 0
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    cutoff = nodes.new("ShaderNodeMath")
    cutoff.operation = "GREATER_THAN"
    cutoff.inputs[1].default_value = 0.01
    mix = nodes.new("ShaderNodeMixShader")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(image.outputs["Color"], shader.inputs["Base Color"])
    links.new(image.outputs["Alpha"], cutoff.inputs[0])
    links.new(cutoff.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(shader.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    material.surface_render_method = "DITHERED"
    material.use_backface_culling = False
    return material


def action_curves(action, rig):
    """Blender 4.4+ actions store their curves in a slotted channel bag."""
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    layer = action.layers.new("YSM sampled pose")
    strip = layer.strips.new(type="KEYFRAME")
    return slot, strip.channelbag(slot, ensure=True).fcurves


def bake_actions(payload, rig, sample_pose, fps=30):
    import bpy

    actions = {}
    for clip in payload.get('clip_ids', CLIPS):
        duration = float(payload["animations"][clip].get("animation_length", 0))
        count = max(1, math.ceil(duration * fps))
        times = {min(i / fps, duration) for i in range(count + 1)} if duration else {0}
        for animation in (payload["animations"][clip],):
            for bone_channels in animation.get("bones", {}).values():
                for track in bone_channels.values():
                    if isinstance(track, dict):
                        for key in track:
                            try:
                                time = float(key)
                            except ValueError:
                                continue
                            if 0 <= time <= duration:
                                times.add(time)
        times.update(
            check["time"] for check in payload["checks"] if check["clip"] == clip
        )
        times = sorted(times)
        tracks = {b["name"]: [[] for _ in range(9)] for b in payload["bones"]}
        for time in times:
            pose = sample_pose(
                payload["animations"],
                clip,
                time,
                blink=False,
                speed=5.6 if clip == "run" else 3 if clip == "walk" else 0,
                variables=variables_for(clip, time),
            )
            for bone in payload["bones"]:
                for i, value in enumerate(channels(bone, pose.get(bone["name"], {}))):
                    tracks[bone["name"]][i].append(value)
        action = bpy.data.actions.new(f"{rig.name} | {clip}")
        action.use_fake_user = True
        action["ysm_clip"] = clip
        action["ysm_duration_seconds"] = duration
        action["ysm_sample_rate"] = fps
        action["ysm_loop"] = str(payload["animations"][clip].get("loop", False))
        slot, curves = action_curves(action, rig)
        for bone in payload["bones"]:
            name = bone["name"]
            for channel in range(9):
                values = tracks[name][channel]
                kind = ("location", "rotation_euler", "scale")[channel // 3]
                path = rig.pose.bones[name].path_from_id(kind)
                curve = curves.new(path, index=channel % 3, group_name=name)
                indices = (
                    [0] if max(values) - min(values) < 1e-8 else list(range(len(times)))
                )
                curve.keyframe_points.add(len(indices))
                curve.keyframe_points.foreach_set(
                    "co", [v for i in indices for v in (1 + times[i] * fps, values[i])]
                )
                for point in curve.keyframe_points:
                    point.interpolation = "LINEAR"
                curve.update()
        actions[clip] = (action, slot)
        print(f"Baked {rig.name}: {clip} ({len(times)} samples)", flush=True)
    return actions


def select_action(character, clip, time=0):
    import bpy

    if not isinstance(character, dict):
        rig = character
        actions = {
            action["ysm_clip"]: (action, next(iter(action.slots)))
            for action in bpy.data.actions
            if action.get("ysm_clip")
        }
        character = dict(rig=rig, actions=actions, fps=30)
    rig = character["rig"]
    action, slot = character["actions"][clip]
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = slot
    scene = bpy.context.scene
    scene.render.fps = character["fps"]
    scene.frame_start = 1
    scene.frame_end = max(
        1, math.ceil(float(action["ysm_duration_seconds"]) * character["fps"]) + 1
    )
    frame = 1 + time * character["fps"]
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def build_character(prepared, root, name=None, fps=30):
    """Create a rigid armature, packed atlas and the source's available review actions."""
    import bpy
    from mathutils import Vector

    payload = json.loads(Path(prepared).read_text(encoding="utf-8"))
    name = name or payload["name"]
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    container = bpy.data.objects.new(name + " - Root", None)
    collection.objects.link(container)
    sx, sy, sz = payload["scale"]
    container.scale = (sx, sz, sy)
    armature = bpy.data.armatures.new(name + " - Skeleton")
    rig = bpy.data.objects.new(name + " - Rig", armature)
    collection.objects.link(rig)
    rig.parent = container
    rig.show_in_front = True
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in payload["bones"]:
        edit = armature.edit_bones.new(bone["name"])
        edit.head = pivot(bone)
        edit.tail = Vector(edit.head) + Vector((0, 0.12, 0))
    for bone in payload["bones"]:
        if bone.get("parent"):
            armature.edit_bones[bone["name"]].parent = armature.edit_bones[
                bone["parent"]
            ]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "XZY"
    vertices = []
    lookup = {b["name"]: b for b in payload["bones"]}
    for part in payload["parts"]:
        origin = pivot(lookup[part["bone"]])
        vertices.extend(
            [
                tuple(a + b for a, b in zip(bposition(point), origin))
                for point in part["vertices"]
            ]
        )
    mesh = bpy.data.meshes.new(name + " - Cube surfaces")
    mesh.from_pydata(vertices, [], payload["triangles"])
    mesh.update()
    uv = mesh.uv_layers.new(name="YSM atlas UV")
    for loop in mesh.loops:
        u, v = payload["uvs"][loop.vertex_index]
        uv.data[loop.index].uv = (u, 1 - v)
    obj = bpy.data.objects.new(name + " - Mesh", mesh)
    collection.objects.link(obj)
    obj.parent = container
    obj.data.materials.append(make_material(payload))
    groups = {
        bone["name"]: obj.vertex_groups.new(name=bone["name"])
        for bone in payload["bones"]
    }
    for part in payload["parts"]:
        groups[part["bone"]].add(
            list(range(part["start"], part["start"] + len(part["vertices"]))),
            1,
            "REPLACE",
        )
    modifier = obj.modifiers.new("YSM rigid skeleton", "ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = False
    actions = bake_actions(payload, rig, load_sampler(root), fps)
    character = dict(
        root=container,
        rig=rig,
        mesh=obj,
        actions=actions,
        payload=payload,
        fps=fps,
        collection=collection,
    )
    credits = bpy.data.texts.new(name + " - YSM source and credits.json")
    credits.write(json.dumps(payload["metadata"], ensure_ascii=False, indent=2))
    rig["ysm_source_model"] = Path(payload["model_directory"]).name
    rig["ysm_baked_actions"] = len(actions)
    rig["ysm_license"] = "CC BY-NC-SA 4.0"
    select_action(character, "idle", 1)
    return character


def validate_character(character, tolerance=2e-5):
    import bpy

    results = []
    for check in character["payload"]["checks"]:
        select_action(character, check["clip"], check["time"])
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj = character["mesh"].evaluated_get(depsgraph)
        mesh = obj.to_mesh()
        try:
            assert len(mesh.vertices) == len(check["vertices"])
            error = max(
                (
                    obj.matrix_world @ v.co
                    - __import__("mathutils").Vector(bposition(p))
                ).length
                for v, p in zip(mesh.vertices, check["vertices"])
            )
            assert (
                error < tolerance
            ), f"{check['clip']}: Blender mesh error {error} exceeds {tolerance}"
            results.append(
                dict(clip=check["clip"], time=check["time"], max_vertex_error=error)
            )
        finally:
            obj.to_mesh_clear()
    select_action(character, "idle", 1)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--model", type=Path)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else None
    )
    if args.prepare:
        prepare_model(args.root, args.model, args.prepared)
        return
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    character = build_character(args.prepared, args.root)
    checks = validate_character(character)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.out.resolve()))
        args.out.with_suffix(".validation.json").write_text(
            json.dumps(checks, indent=2), encoding="utf-8"
        )
    print(json.dumps(dict(actions=len(character["actions"]), checks=checks)))


if __name__ == "__main__":
    main()
