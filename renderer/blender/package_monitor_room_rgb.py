"""Package the verified room, source screens and all five refreshed characters."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from PIL import Image,ImageStat,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]


def main():
    folder=ROOT/'output/blender-scenes/monitor-room-rgb'
    library=ROOT/'output/blender/latest'
    assert json.loads((folder/'validation.json').read_text())['status']=='passed'
    rendered=['monitor-room-'+name+'.png' for name in ['reference','pc','layout','character','room-left','room-reverse','pc-side','character-side']]
    for name in rendered:
        with Image.open(folder/name) as im:
            assert im.size==(2560,1440)
            assert max(ImageStat.Stat(im).stddev)>15,(name,'blank image')
    sheet=Image.new('RGB',(1920,4*584),'#0b101a');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
    for i,name in enumerate(rendered):
        x=(i%2)*960;y=(i//2)*584
        with Image.open(folder/name) as im:sheet.paste(im.resize((960,540)),(x,y))
        draw.text((x+18,y+546),name.replace('monitor-room-','').replace('.png','').upper(),font=font,fill='#d0e2f6')
    sheet.save(folder/'all-views.jpg',quality=92)
    for sub in ['source','screens','library']:(folder/sub).mkdir(exist_ok=True)
    for name in ['monitor_room','pc_case','bookshelves','convert','prepare_monitor_screens','import_all_characters','check_monitor_room_rgb','package_monitor_room_rgb','sunset_city','sunset_landscape']:
        shutil.copy2(ROOT/f'renderer/blender/{name}.py',folder/f'source/{name}.py')
    shutil.copy2(ROOT/'renderer/blender/monitor_room_gallery.html',folder/'index.html')
    shutil.copy2(ROOT/'renderer/blender/MONITOR_ROOM_RGB.md',folder/'README.md')
    shutil.copy2(ROOT/'output/blender-scenes/monitor-room/CHARACTER-ATTRIBUTION.md',folder/'CHARACTER-ATTRIBUTION.md')
    # The aunt carries an additional original author block inside its packed blend.
    with (folder/'CHARACTER-ATTRIBUTION.md').open('a',encoding='utf-8') as f:
        f.write('\n\nThe aunt variant also retains its source author and license metadata in its own Blender Text blocks. See library/satou-aunt.validation.json for the source file fingerprints.\n')
    sources=json.loads((ROOT/'assets/monitor-screens/SOURCES.json').read_text(encoding='utf-8'))
    sources=[s for s in sources if s['file'].startswith(('game-','code-'))]
    assert len(sources)==10
    for source in sources:shutil.copy2(ROOT/'assets/monitor-screens'/source['file'],folder/'screens'/source['file'])
    (folder/'screens/SOURCES.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
    library_manifest=json.loads((library/'manifest.json').read_text(encoding='utf-8'))
    library_manifest['validation_scope']='Numerical Blender vs YSM adapter at the recorded per-model poses; rendered previews are not Minecraft runtime testing'
    (library/'manifest.json').write_text(json.dumps(library_manifest,indent=2)+'\n',encoding='utf-8')
    names=['manifest.json','README.md','all-characters.png','satou-all-characters.blend']
    for v in library_manifest['variants']:names.extend([v['blend'],v['blend'].replace('.blend','.validation.json')])
    for name in names:shutil.copy2(library/name,folder/'library'/name)
    backup=ROOT/'dist/blender/monitor-room-rgb-drafts'
    assert backup.resolve().is_relative_to(ROOT.resolve())
    backup.mkdir(parents=True,exist_ok=True)
    for p in [*folder.glob('*-draft.png'),*folder.glob('*.blend1')]:
        assert p.resolve().is_relative_to(folder.resolve())
        shutil.move(str(p),str(backup/p.name))
    manifest=json.loads((folder/'manifest.json').read_text())
    manifest.update(renders=rendered,fresh_character_variants=5,code_screens=2,main_screens_unique=6,cameras=8,graphics_card='RTX 5070',
                    floor_monitors=2,case_behind_floor_monitors=True,bookshelves='timber shelves with brick backing and varied books',
                    validation='validation.json',library='library/manifest.json')
    manifest['sha256']={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=ROOT/'output/satou-monitor-room-rgb.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(folder.parent))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert sum(n.endswith('.blend') for n in z.namelist())==7
    viewer=ROOT/'dist/viewer/monitor-room-rgb'
    shutil.copytree(folder,viewer,dirs_exist_ok=True)
    html=(viewer/'index.html').read_text(encoding='utf-8')
    links=set(re.findall(r'(?:href|src)="([^"#]+)"',html));links.update(rendered)
    for path in sorted(links):
        if '://' in path:continue
        expected=(viewer/path).stat().st_size
        with urllib.request.urlopen('http://127.0.0.1:4173/monitor-room-rgb/'+path) as response:
            assert response.status==200 and len(response.read())==expected
    print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,links_verified=len(links),models=5)),flush=True)


if __name__=='__main__':main()
