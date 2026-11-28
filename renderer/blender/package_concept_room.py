"""Publish a local review gallery and a portable scene archive."""
import html
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT/'output/blender-scenes/monitor-room-concept'


def main():
    review = json.loads((SCENE/'reviews/scores.json').read_text(encoding='utf-8'))
    rounds = review['rounds']
    final = rounds[-1]
    assert len(final['tiles']) == 8
    assert json.loads((SCENE/'validation.json').read_text())['status'] == 'passed'
    labels = ['หน้าต่างและชั้นซ้าย','ชั้นบนและจอฝั่งซ้าย','ชั้นบนและจอหลัก',
              'ชั้นขวาและจอโค้ด','เคสและจอพื้น','คีย์บอร์ดและท่านั่ง',
              'เก้าอี้และพรม','ตู้ลิ้นชักและมุมขวา']
    review_rows = []
    for run in rounds:
        scores = [t['score'] for t in run['tiles']]
        assert len(scores) == 8
        summary = f"{run['label']} · {sum(scores)/8:.1f}/100"
        tiles = []
        for tile, name in zip(run['tiles'],labels):
            path = f"reviews/{run['folder']}/{tile['tile']:02}"
            assert (SCENE/path/'original.png').is_file() and (SCENE/path/'render.png').is_file()
            note = html.escape(tile['note'])
            tiles.append(f'<figure><figcaption>{name} <strong>{tile["score"]}/100</strong></figcaption>'
                         f'<a href="{path}/comparison.png"><img loading="lazy" src="{path}/comparison.png" alt="{name} เทียบต้นฉบับกับ Blender"></a><p>{note}</p></figure>')
        opened = ' open' if run is final else ''
        review_rows.append(f'<details{opened}><summary>{summary}</summary><div class="grid">'+''.join(tiles)+'</div></details>')
    page = '''<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ห้อง Blender เทียบกับภาพต้นแบบ</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b0e15;color:#e7edf8;font:16px/1.55 system-ui,sans-serif}main{max-width:1460px;margin:auto;padding:28px clamp(16px,4vw,48px)}h1{font-size:clamp(27px,4vw,44px);line-height:1.25}a{color:#a8d2ff;text-underline-offset:4px}.files{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:22px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}figure{margin:0;border:1px solid #313b4d;border-radius:9px;overflow:hidden;background:#151a26}figcaption,p{margin:0;padding:12px 14px}figcaption strong{float:right}figure img{width:100%;display:block}details{margin:20px 0}summary{cursor:pointer;padding:13px;background:#232d3d;margin-bottom:12px;border-radius:7px}section{margin:25px 0}@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style><main><h1>ฉาก Blender เทียบภาพต้นแบบ</h1><div class="files"><a href="room.blend" download>ดาวน์โหลดฉาก Blender</a><a href="reference.png">ต้นฉบับ</a><a href="validation.json">ผลตรวจไฟล์</a><a href="reviews/scores.json">คะแนนรายช่อง</a></div>
<figure><a href="room.png"><img src="room.png" alt="ภาพเรนเดอร์ห้อง Blender"></a><figcaption>ภาพเรนเดอร์ฉบับล่าสุด</figcaption></figure>
<section class="grid"><figure><a href="floor-detail.png"><img loading="lazy" src="floor-detail.png" alt="จอคู่ เคส คีย์บอร์ด และตัวละคร"></a><figcaption>มุมชุดคอมพื้น</figcaption></figure><figure><a href="library-angle.png"><img loading="lazy" src="library-angle.png" alt="มุมโต๊ะและชั้นหนังสือ"></a><figcaption>มุมโต๊ะและชั้นหนังสือ</figcaption></figure></section>
<h2>เทียบ 8 ช่องในแต่ละรอบ</h2><p>Subagent ให้คะแนนจากองค์ประกอบและรูปทรง 35 คะแนน วัสดุ 25 คะแนน แสงและสี 20 คะแนน และรายละเอียด 20 คะแนน คะแนนเป็นการประเมินด้วยสายตา</p>
'''+''.join(review_rows)+'</main></html>\n'
    (SCENE/'index.html').write_text(page,encoding='utf-8')
    average = sum(t['score'] for t in final['tiles'])/8
    minimum = min(t['score'] for t in final['tiles'])
    (SCENE/'README.md').write_text(f'''# ฉากห้อง Blender จากภาพต้นแบบ

เปิด `room.blend` ใน Blender 5.3 ตั้ง OptiX ใน Preferences แล้วกด F12 เพื่อเรนเดอร์มุมหลัก ภาพมุมหลักอยู่ใน `room.png` และอีกสองมุมอยู่ใน `floor-detail.png` กับ `library-angle.png`

ชั้นไม้ ผนังอิฐ หนังสือ โต๊ะ เก้าอี้ จอ พรม และอุปกรณ์คอมเป็นวัตถุ 3D แก้ไขแยกได้ ภาพบนจอและลายพื้นผิวฝังอยู่ในไฟล์ Blender แล้ว จอหลักใช้ภาพจากเกม จอโค้ดใช้ภาพโค้ดของโปรเจกต์ และจอวางพื้นใช้ภาพที่แยกจากจอทั้งสองในภาพอ้างอิง ใช้ตัวอย่างลายไม้ สันหนังสือ และพรมจากพื้นผิวเฉพาะส่วนในภาพแนบ

เปิด `index.html` เพื่อเทียบต้นฉบับกับเรนเดอร์ทุกช่อง ใช้กริด 4 × 2 ตัดตามพิกัดเดียวกันทุกครั้ง และส่งต้นฉบับกับเรนเดอร์ของแต่ละช่องให้ subagent ดูแยกกัน หลังตรวจ {len(rounds)} รอบ คะแนนเฉลี่ยของรอบล่าสุดคือ {average:.1f}/100 ช่องต่ำสุดได้ {minimum}/100 คะแนนนี้มาจากการประเมินด้วยสายตาตามสี่เกณฑ์ใน `reviews/scores.json` เป้าหมายคือ 90 คะแนนต่อช่อง

`source/` เก็บสคริปต์ที่ใช้สร้างฉากและตัดภาพเทียบ เมื่อรันในโปรเจกต์เดิม วางสคริปต์ใน `renderer/blender/` และใช้ `assets/monitor-screens/` กับไฟล์ตัวละครใน `output/blender/latest/` เครดิตโมเดลอยู่ใน `CHARACTER-ATTRIBUTION.md` และ Text blocks ของฉาก
''',encoding='utf-8')
    source = SCENE/'source'
    source.mkdir(exist_ok=True)
    modules = ['concept_room','concept_architecture','concept_furniture','concept_library','concept_review',
               'check_concept_room','package_concept_room','monitor_room','bookshelves','pc_case',
               'sunset_city','sunset_landscape','convert']
    for module in modules:
        shutil.copy2(ROOT/f'renderer/blender/{module}.py',source/f'{module}.py')
    shutil.copy2(ROOT/'output/blender-scenes/monitor-room-rgb/CHARACTER-ATTRIBUTION.md', SCENE/'CHARACTER-ATTRIBUTION.md')
    files = ['index.html','README.md','room.blend','room.png','reference.png','floor-detail.png','library-angle.png',
             'validation.json','CHARACTER-ATTRIBUTION.md']
    paths = [SCENE/name for name in files]
    for name in ['source','reviews','textures']:
        paths.extend(path for path in (SCENE/name).rglob('*') if path.is_file())
    archive = ROOT/'output/satou-monitor-room-concept.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as zipped:
        for path in paths:
            zipped.write(path, path.relative_to(SCENE.parent))
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert sum(name.endswith('.blend') for name in zipped.namelist()) == 1
    preview = ROOT/'dist/viewer/monitor-room-concept'
    for path in paths:
        target = preview/path.relative_to(SCENE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path,target)
    print(f'PACKED {archive} ({len(paths)} files)',flush=True)


if __name__ == '__main__':
    main()
