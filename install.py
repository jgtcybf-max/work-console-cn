"""Build the pinned upstream web assets plus the public local overlays (stdlib only)."""
import concurrent.futures,hashlib,json,shutil,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
WEB=ROOT/'web'
def sha(data):return hashlib.sha256(data).hexdigest()

def install():
    meta=json.loads((ROOT/'UPSTREAM.json').read_text(encoding='utf8'))
    archive=ROOT/'.cache'/'upstream-web.zip'
    if archive.exists() and sha(archive.read_bytes())!=meta['archive_sha256']:raise ValueError('本地上游缓存校验失败。')
    if WEB.exists():
        if not (WEB/'.work-console-build').is_file():raise RuntimeError('web目录不是本工具生成，拒绝覆盖。')
    WEB.mkdir(exist_ok=True)
    (WEB/'.work-console-build').write_text('installation-in-progress\n',encoding='utf8')
    original=json.loads((ROOT/'upstream-manifest.json').read_text(encoding='utf8'))
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                target=(WEB/item.filename).resolve()
                if not target.is_relative_to(WEB.resolve()):raise ValueError('非法压缩包路径')
                if item.is_dir():target.mkdir(parents=True,exist_ok=True)
                else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
    else:
        def download(item):
            name,digest=item;target=(WEB/name.lstrip('/')).resolve()
            if not target.is_relative_to(WEB.resolve()):raise ValueError('非法资源路径')
            if target.exists() and hashlib.sha1(target.read_bytes()).hexdigest()==digest:return
            with urllib.request.urlopen(meta['download_origin']+name,timeout=40) as response:raw=response.read()
            if hashlib.sha1(raw).hexdigest()!=digest:raise ValueError('官方资源版本已变化：'+name)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        assets={**original['hashTable'],**meta['extra_assets_sha1']}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:list(executor.map(download,assets.items()))
    for name,digest in original['hashTable'].items():
        if hashlib.sha1((WEB/name.lstrip('/')).read_bytes()).hexdigest()!=digest:raise ValueError('上游资源校验失败：'+name)
    for patch in json.loads((ROOT/'patches.json').read_text(encoding='utf8')):
        p=WEB/patch['path'];text=p.read_text(encoding='utf8')
        if sha(text.encode())!=patch['sha256_before'] or text[patch['start']:patch['end']]!=patch['before']:raise ValueError('上游版本不匹配：'+patch['path'])
        text=text[:patch['start']]+patch['after']+text[patch['end']:]
        if sha(text.encode())!=patch['sha256_after']:raise ValueError('补丁校验失败：'+patch['path'])
        p.write_text(text,encoding='utf8',newline='\n')
    for source,destination in [('zh.json','assets/i18n/zh.json'),('tao-chinese.js','tao-chinese.js'),('tao-defaults.js','tao-defaults.js'),('demo-seed.json','tao-seed.json'),('library.html','library.html'),('plugin.js','assets/bundled-plugins/tao-codex-task-bridge/plugin.js'),('plugin-manifest.json','assets/bundled-plugins/tao-codex-task-bridge/manifest.json')]:
        p=WEB/destination;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/source,p)
    from branding import apply
    apply(WEB,ROOT)
    with zipfile.ZipFile(ROOT/'codex-task-bridge.zip','w',zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT/'plugin.js','plugin.js');z.write(ROOT/'plugin-manifest.json','manifest.json')
    (WEB/'.work-console-build').write_text('work-console-cn v0.1.0\n',encoding='utf8')
    print('安装完成：882项上游资源及6个补丁已校验。运行 python serve.py 后打开 http://127.0.0.1:18765/')

if __name__=='__main__':install()
