"""Apply the provided brand artwork to the generated application."""
from pathlib import Path
import json,re,shutil,zipfile

VERSION='xiefurn-20261117'

def brand_index(text):
    text=re.sub(r'(<link\b[^>]*href=")([^\"]+)("[^>]*(?:rel="(?:shortcut icon|icon|apple-touch-icon|mask-icon|manifest)")[^>]*>)',lambda m:m[1]+m[2].split('?')[0]+'?v='+VERSION+m[3],text)
    if 'brand.js?v=' not in text:text=text.replace('</body>','<script src="brand.js?v='+VERSION+'"></script></body>')
    return text

def apply(web,source):
    web=Path(web);source=Path(source);target=web/'brand';target.mkdir(exist_ok=True)
    if (source/'brand-assets.zip').exists():
        with zipfile.ZipFile(source/'brand-assets.zip') as archive:
            for item in archive.infolist():
                path=(target/item.filename).resolve()
                if not path.is_relative_to(target.resolve()):raise ValueError('非法图标路径')
                if not item.is_dir():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.read(item))
    else:
        for f in (source/'brand').glob('*'):
            if f.is_file():shutil.copy2(f,target/f.name)
    shutil.copy2(source/'brand.js',web/'brand.js')
    shutil.copy2(target/'favicon.ico',web/'favicon.ico')
    icons=web/'assets'/'icons';icons.mkdir(parents=True,exist_ok=True)
    for size in [72,96,128,144,192,512]:shutil.copy2(target/('icon-'+str(size)+'.png'),icons/('icon-'+str(size)+'x'+str(size)+'.png'))
    for filename,size in [('apple-touch-icon.png',180),('favicon-16x16.png',16),('favicon-32x32.png',32),('favicon-192x192.png',192)]:shutil.copy2(target/('icon-'+str(size)+'.png'),icons/filename)
    for size in [70,144,150,310]:
        matching=icons/('mstile-'+str(size)+'x'+str(size)+'.png')
        if matching.exists():shutil.copy2(target/'icon-512.png',matching)
    p=web/'manifest.json';m=json.loads(p.read_text(encoding='utf8'));m.update(name='工作总台',short_name='总台',start_url='/#/boards/TAO_CONSOLE')
    for item in m['icons']:item['src']='brand/icon-'+item['sizes'].split('x')[0]+'.png?v='+VERSION
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8',newline='\n')
    p=web/'index.html';p.write_text(brand_index(p.read_text(encoding='utf8')),encoding='utf8',newline='\n')

if __name__=='__main__':
    root=Path(__file__).resolve().parent;apply(root/'web',root)
