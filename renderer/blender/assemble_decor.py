"""Put the standalone shelf and decor models back at their scene anchors."""

from collections import defaultdict
import re

import bpy
from mathutils import Matrix, Vector

from item_decor import BANKS, LEDGE, SHELF_PARTS, _bounds, _parts


STUDIO = {'RIGHT', 'LEFT', 'FRONT', 'BACK', 'BUTTOM', 'TOP', 'Key softbox',
          'Front fill', 'Back softbox', 'Underside fill'}
WALL = ('Uneven bonded terracotta brick', 'Recess mortar back')


def _load(asset, directory, collection, exclude=()):
    with bpy.data.libraries.load(str(directory / asset / 'model.blend'), link=False) as (available, ready):
        names = [name for name in available.objects if name not in STUDIO and not name.startswith(exclude)]
        ready.objects = list(names)
    model = bpy.data.collections.new(f'Decor · {asset}')
    collection.children.link(model)
    objects = dict(zip(names, ready.objects))
    for name, obj in objects.items():
        assert obj and obj.type in {'MESH', 'CURVE', 'FONT'}, name
        model.objects.link(obj)
        obj.name = f'Decor {asset} / {name}'
    bpy.context.view_layer.update()
    return objects


def _move(objects, matrix):
    for obj in objects:
        obj.matrix_world = matrix @ obj.matrix_world


def _replace(objects, originals):
    for old in originals:
        old.hide_render = True
        old.hide_set(True)
    return {'inserted': len(objects), 'superseded': len(originals)}


def _bookshelves(scene, objects):
    offset = 0
    originals = []
    fits = []
    # The standalone file puts the two banks edge-to-edge with a 0.15-unit gap.
    # The wall contributed to its frame, so keep it as an anchor even though it is separate here.
    for bank in BANKS:
        parts = _parts(scene.objects[bank].children, SHELF_PARTS)
        low, high = _bounds(parts)
        width = high.x - low.x
        originals.extend(part for part in parts if not part.name.startswith(WALL))
        fits.append((offset + width + .075, Matrix.Translation((low.x - offset, low.y, low.z))))
        offset += width + .15
    for obj in objects.values():
        i = 0 if obj.matrix_world.translation.x < fits[0][0] else 1
        _move([obj], fits[i][1])
    return _replace(objects, originals)


def _books(scene, objects):
    original_groups = {
        'Upright book': sorted((o for o in scene.objects if o.name.startswith('Leather-bound volume')),
                               key=lambda o: o.name),
        'Flat book': sorted((o for o in scene.objects if o.name.startswith('Stacked volume')),
                            key=lambda o: o.name),
    }
    by_volume = defaultdict(dict)
    bands = []
    for name, obj in objects.items():
        if ' / ' in name:
            label, part = name.split(' / ', 1)
            by_volume[label][part] = obj
        else:
            bands.append(obj)
    assert len(by_volume) == 101
    originals = []
    candidates = []
    for kind, roots in original_groups.items():
        for i, old in enumerate(roots, 1):
            parts = by_volume[f'{kind} {i:02}']
            old_spine = next(o for o in old.children if o.name.startswith('Rounded book spine'))
            new_spine = next(o for name, o in parts.items() if name.startswith('Rounded book spine'))
            fit = old_spine.matrix_world @ new_spine.matrix_world.inverted()
            pages = next(o for name, o in parts.items() if name.startswith('Paper signatures'))
            for sign in (-1, 1):
                offset = Vector((0, -.5*pages.dimensions.y + .008, sign*(.5*pages.dimensions.z + .0007)))
                candidates.append((pages.matrix_world @ offset, fit))
            _move(parts.values(), fit)
            originals.extend(_parts(old.children))
    for band in bands:
        position = band.matrix_world.translation
        point, fit = min(candidates, key=lambda candidate: (candidate[0] - position).length_squared)
        assert (point - position).length < .012, band.name
        _move([band], fit)
    return {**_replace(objects, originals), 'volumes': len(by_volume)}


def _ivy(scene, objects):
    offset = 0
    originals = []
    fits = []
    for bank in (*BANKS, LEDGE):
        parts = _parts(scene.objects[bank].children_recursive, ('Ivy · ', 'Raised central vein',
                                                              'Trailing ivy stem', 'Leaf petiole'))
        low, high = _bounds(parts)
        width = high.x - low.x
        originals.extend(parts)
        fits.append((offset + width + .06, Matrix.Translation((low.x - offset, low.y, high.z))))
        offset += width + .12
    for name, obj in objects.items():
        if name.startswith('Ivy secondary leaf veins'):
            match = re.search(r'\.(\d+)$', name)
            i = int(match.group(1)) if match else 0
        else:
            x = obj.matrix_world.translation.x
            i = sum(x > limit for limit, _ in fits[:-1])
        _move([obj], fits[i][1])
    return _replace(objects, originals)


def _strips(scene, objects):
    fixtures = sorted(_parts(scene.objects, ('Concealed warm light strip',)), key=lambda obj: obj.name)
    assert len(fixtures) == 6
    for name, obj in objects.items():
        # The studio lays out fixtures as six parallel rows on 0.075-unit centers.
        if name.startswith('LED low-voltage input lead'):
            y = obj.data.splines[0].points[0].co.y
        else:
            y = obj.matrix_world.translation.y
        i = round(y / .075)
        assert 0 <= i < len(fixtures), name
        fixture = fixtures[i]
        if name.startswith('Continuous opal diffuser'):
            obj.data.materials[0] = fixture.data.materials[0]
        _move([obj], fixture.matrix_world @ Matrix.Translation((0, -i*.075, -.013)))
    return {**_replace(objects, fixtures), 'fixtures': len(fixtures)}


def apply_decor(scene, assets):
    """Insert the standalone objects and hide the corresponding staging proxies."""
    collection = bpy.data.collections.new('Assembled · Shelf and decor models')
    scene.collection.children.link(collection)
    bpy.context.view_layer.update()
    receipts = {}
    for slug, apply in [('bookshelf', _bookshelves), ('books', _books), ('ivy', _ivy), ('led-strip', _strips)]:
        objects = _load(slug, assets, collection, exclude=WALL if slug == 'bookshelf' else ())
        receipts[slug] = apply(scene, objects)

    ledge = scene.objects[LEDGE]
    frame = scene.objects['Antiqued framed pixel print']
    originals = {
        'bridge-shelf': _parts(ledge.children, ('Long furniture bridge', 'Bridge inner back')),
        'archive-box': _parts(ledge.children, ('Canvas archive box', 'Archive box ')),
        'pixel-frame': [frame, *_parts(frame.children_recursive)],
        'amber-lantern': _parts(scene.objects[BANKS[0]].children, ('Lantern ',)),
        'pixel-lantern': _parts(ledge.children, ('Pixel window keepsake', 'Pixel lantern window')),
        'creeper-head': _parts(ledge.children, ('Olive ceramic pixel sculpture', 'Sculpture dark inlay')),
        'armillary': _parts(scene.objects[BANKS[1]].children, ('Armillary ',)),
        'potted-plant': [scene.objects[name] for name in ('Foreground planter', 'Planter rim', 'Planter soil',
                                                           'Foreground olive plant', 'Foreground olive stems')],
    }
    for slug, old in originals.items():
        objects = _load(slug, assets, collection)
        if slug in {'bridge-shelf', 'creeper-head'}:
            _move(objects.values(), ledge.matrix_world)
        receipts[slug] = _replace(objects, old)
    bpy.context.view_layer.update()
    return receipts
