"""Publish before-and-after comparisons for the editable monitor room."""

import argparse
import shutil

from polish_review import ROOT, SCENE as BEFORE, THAI_LABELS, split

OUTPUT = BEFORE.with_name('monitor-room-lighting')
VIEWS = {
    'room.png': 'มุมหลัก',
    'floor-detail.png': 'มือถือ จอพื้น และเคส',
    'library-angle.png': 'โต๊ะและชั้นหนังสือ',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--layout', action='store_true')
    mode.add_argument('--assembled', action='store_true')
    args = parser.parse_args()
    layout = OUTPUT.with_name('monitor-room-layout')
    output = OUTPUT.with_name('monitor-room-assembled') if args.assembled else layout if args.layout else OUTPUT
    preview = ROOT / 'dist/viewer' / output.name
    previous = layout if args.assembled else OUTPUT if args.layout else BEFORE
    view_titles = {'top-view.png': 'มุมสูงของห้อง', **VIEWS} if args.layout or args.assembled else VIEWS
    if args.assembled:
        title, labels = 'ฉากห้องคอมฉบับประกอบโมเดล', ('ฉากก่อนประกอบ', 'ฉากประกอบแล้ว')
    elif args.layout:
        title, labels = 'เทียบตำแหน่งห้องคอมใน Blender', ('ก่อนย้าย', 'หลังย้าย')
    else:
        title, labels = 'เทียบแสงห้องคอมใน Blender', ('ก่อนจัดแสง', 'หลังจัดแสง')
    comparison_view = 'top-view.png' if args.layout else 'room.png'

    before = output / 'before'
    before.mkdir(exist_ok=True)
    for filename in view_titles:
        shutil.copy2(previous / filename, before / filename)
    split(before / comparison_view, output / comparison_view, output / 'review')

    views = []
    for filename, view_title in view_titles.items():
        images = ''.join(f'<figure><figcaption>{label}</figcaption><a href="{path}">'
                         f'<img src="{path}" loading="lazy" alt="{view_title} {label}"></a></figure>'
                         for label, path in zip(labels, (f'before/{filename}', filename)))
        anchor = {'top-view.png': ' id="top-view"', 'floor-detail.png': ' id="floor-view"'}.get(filename, '')
        views.append(f'<section{anchor}><h2>{view_title}</h2><div class="pair">{images}</div></section>')
    tiles = []
    for index, label in enumerate(THAI_LABELS, 1):
        tile_title = f'ช่อง {index:02}' if args.layout else label
        path = f'review/{index:02}/comparison.png'
        tiles.append(f'<figure><figcaption>{tile_title}</figcaption><a href="{path}">'
                     f'<img src="{path}" loading="lazy" alt="ภาพเทียบ {tile_title}"></a></figure>')

    top_preview = '''<section id="top-view"><h2>มุมสูงของห้อง</h2><figure><a href="top-view.png">
<img src="top-view.png" alt="ภาพจากกล้องมุมสูง เห็นโต๊ะ ชั้นหนังสือ จอพื้น และตัวละครบนพรม"></a></figure></section>
'''
    heading = 'เทียบมุมสูง 8 ช่อง' if args.layout else 'เทียบมุมหลัก 8 ช่อง'
    page = '''<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PAGE_TITLE</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#12131a;color:#f2ede6;font:16px/1.55 system-ui,sans-serif}
main{max-width:1500px;margin:auto;padding:26px clamp(14px,4vw,50px)}h1,h2{line-height:1.2}h1{font-size:clamp(26px,4vw,44px)}
a{color:#ffd6a3;text-underline-offset:4px}section{margin:34px 0}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
figure{margin:0;border:1px solid #383544;border-radius:8px;overflow:hidden;background:#201e28}
figcaption{padding:8px 12px}img{width:100%;height:auto;display:block}
@media(max-width:680px){.pair{grid-template-columns:1fr}}
</style></head><body><main><h1>PAGE_TITLE</h1>
<p><a href="room.blend" download>ดาวน์โหลดฉาก Blender</a> · <a href="validation.json">ผลตรวจฉาก</a></p>
'''.replace('PAGE_TITLE', title)
    page += ('' if 'top-view.png' in view_titles else top_preview) + ''.join(views)
    page += f'<section><h2>{heading}</h2><div class="pair">{"".join(tiles)}</div></section></main></body></html>\n'
    (output / 'index.html').write_text(page, encoding='utf-8')

    paths = [output / filename for filename in ('index.html', 'validation.json', 'room.blend', 'top-view.png', *VIEWS)]
    paths += sorted(before.glob('*.png')) + sorted((output / 'review').rglob('*.png'))
    for path in paths:
        target = preview / path.relative_to(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


if __name__ == '__main__':
    main()
