import hashlib,json,os,subprocess
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test')
expected={'wordcraft-vaio':'0.8.0~vaio5','gridcraft-vaio':'0.8.0~vaio1','pdfcraft-vaio':'0.9.0~vaio1','deckcraft-vaio':'0.8.0~vaio1','vectorcraft-vaio':'0.13.1~vaio1','designcraft-vaio':'0.9.0~vaio1','artcraft-launcher-vaio':'0.5.1~vaio7'}
def output(args):return subprocess.check_output(args).decode().strip()
def digest(path):
 h=hashlib.sha256()
 with open(str(path),'rb') as file:
  for block in iter(lambda:file.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
r={'versions':{},'manifests':{},'checks':[]}
for name,version in expected.items():
 r['versions'][name]=output(['dpkg-query','-W','-f=${Version}',name]);assert r['versions'][name]==version
for package in ['designcraft-vaio','artcraft-launcher-vaio']:
 assert not output(['dpkg','-V',package])
 manifest=json.loads(Path('/usr/share/doc/'+package+'/build.json').read_text());r['manifests'][package]=manifest
 if package=='designcraft-vaio':
  for binary,sha in manifest['binary_sha256'].items():assert digest(Path('/usr/lib/'+package+'/bin/'+binary))==sha
 else:assert digest(Path('/usr/lib/'+package+'/bin/launcher'))==manifest['binary_sha256']
 assert output(['dpkg-query','-S','/usr/lib/'+package+'/lib/libxcb.so.1']).startswith(package+': ')
r['key_sha256']=digest(Path('/usr/share/keyrings/vaio-artcraft-archive-keyring.gpg'))
assert r['key_sha256']=='dfe2482d39a8785758534e312440b21fa494004e13a2726f1e4921c27cb561f1'
r['source']=Path('/etc/apt/sources.list.d/vaio-artcraft.list').read_text()
r['preferences']=Path('/etc/apt/preferences.d/vaio-artcraft').read_text()
assert set(r['preferences'].splitlines()[0].split()[1:])==set(expected)
r['mime']={}
for file in ['original.designcraft']:
 r['mime'][file]=output(['xdg-mime','query','filetype',str(base/file)]);assert r['mime'][file]=='application/x-designcraft'
r['policy']=output(['apt-cache','policy','designcraft-vaio','artcraft-launcher-vaio'])
r['kernel']=output(['uname','-r']);r['architecture']=output(['uname','-m'])
r['memory']=output(['free','-m'])
r['temperatures_millicelsius']=[int(p.read_text()) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')]
r['leftover_test_listeners']=[line for line in output(['ss','-lnt']).splitlines() if any(':'+str(port)+' ' in line for port in [7993,7994,7995])]
assert not r['leftover_test_listeners']
r['checks']=['seven installed versions','package integrity','manifest binary hashes','private XCB ownership','unchanged scoped key','seven-package APT preference','native MIME','no test control listeners']
r['passed']=True
(base/'installed-proof.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['manifests','policy','source','preferences']},indent=2))
