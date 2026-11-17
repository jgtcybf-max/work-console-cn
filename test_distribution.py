from pathlib import Path
import hashlib,json,unittest,zipfile

ROOT=Path(__file__).resolve().parent
class DistributionTests(unittest.TestCase):
    def test_pinned_archive_and_original_assets(self):
        meta=json.loads((ROOT/'UPSTREAM.json').read_text(encoding='utf8'))
        archive=ROOT/'.cache'/'upstream-web.zip'
        if not archive.exists():self.skipTest('Optional private upstream cache is not included in Git')
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),meta['archive_sha256'])
        manifest=json.loads((ROOT/'upstream-manifest.json').read_text(encoding='utf8'))
        with zipfile.ZipFile(archive) as z:
            for name,digest in manifest['hashTable'].items():self.assertEqual(hashlib.sha1(z.read(name.lstrip('/'))).hexdigest(),digest,name)
    def test_no_secrets_in_demo_configuration(self):
        data=json.loads((ROOT/'demo-seed.json').read_text(encoding='utf8'))['data']
        self.assertEqual(len(data['task']['ids']),13)
        self.assertEqual(data['globalConfig']['localization']['lng'],'zh')
        sync=data['globalConfig']['sync'];self.assertFalse(sync['isEnabled'])
        def walk(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ['password','accessToken','encryptKey','userName','loginName']:self.assertFalse(item,key)
                    walk(item)
            elif isinstance(value,list):
                for item in value:walk(item)
        walk(data)
        self.assertTrue(all(t['id'].startswith('demo-') for t in data['task']['entities'].values()))
    def test_generated_overlay_hashes(self):
        if not (ROOT/'web').exists():self.skipTest('Run python install.py first')
        for patch in json.loads((ROOT/'patches.json').read_text(encoding='utf8')):
            if patch['path']=='index.html':
                self.assertIn('brand.js?v=xiefurn-large-20261117',(ROOT/'web'/'index.html').read_text(encoding='utf8'))
                continue
            self.assertEqual(hashlib.sha256((ROOT/'web'/patch['path']).read_bytes()).hexdigest(),patch['sha256_after'])

if __name__=='__main__':unittest.main()
