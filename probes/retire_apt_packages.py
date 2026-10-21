#!/usr/bin/env python3
"""Retire only unindexed Pages packages after verified public Release downloads."""
import argparse,concurrent.futures,fcntl,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'.build/apt-public'
BACKUP=ROOT/'.build/apt-retired'
REPO='kennvanhauen/vaio-artcraft-apt'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def indexed_files(index):
    names={line[10:].strip() for line in index.read_text().splitlines() if line.startswith('Filename: ')}
    if not names or any(not name.startswith('pool/main/') or '..' in Path(name).parts for name in names):raise RuntimeError('Invalid package index')
    return names
def select(index,pool):
    keep=indexed_files(index)
    if any(not (index.parents[4]/name).is_file() for name in keep):raise RuntimeError('Indexed package is missing')
    return [p for p in sorted(pool.glob('*.deb')) if 'pool/main/'+p.name not in keep]
def plan(path):
    if subprocess.check_output(['git','-C',str(PUBLIC),'status','--porcelain'],text=True).strip():raise RuntimeError('Public checkout must be clean')
    index=PUBLIC/'dists/xenial/main/binary-i386/Packages'
    releases=json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/releases?per_page=100']))
    assets={a['name']:(r,a) for r in releases if not r['draft'] for a in r['assets']}
    rows=[]
    for package in select(index,PUBLIC/'pool/main'):
        r,a=assets[package.name.replace('~','.')]
        digest=sha(package)
        if a.get('digest')!='sha256:'+digest or a['size']!=package.stat().st_size:raise RuntimeError('Release mismatch: '+package.name)
        rows.append(dict(filename='pool/main/'+package.name,sha256=digest,size=package.stat().st_size,asset_name=a['name'],download_url=a['browser_download_url'],release_url=r['html_url']))
    BACKUP.mkdir(parents=True,exist_ok=True)
    def verify(row):
        backup=BACKUP/Path(row['filename']).name
        if not backup.exists():
            subprocess.run(['curl','--fail','--location','--retry','2','--silent','--show-error','--output',str(backup)+'.partial',row['download_url']],check=True,timeout=300)
            partial=backup.with_name(backup.name+'.partial')
            if sha(partial)!=row['sha256']:raise RuntimeError('Downloaded backup hash mismatch')
            partial.replace(backup)
        if sha(backup)!=row['sha256']:raise RuntimeError('Local backup hash mismatch')
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(verify,rows))
    result=dict(schema=1,index_sha256=sha(index),public_head=subprocess.check_output(['git','-C',str(PUBLIC),'rev-parse','HEAD'],text=True).strip(),files=rows,total_bytes=sum(r['size'] for r in rows))
    dump(path,result)
    print(json.dumps(dict(plan=str(path),files=len(rows),retired_mib=round(result['total_bytes']/1048576,2),verified_downloads=True),indent=2))
def apply(path):
    data=json.loads(path.read_text());index=PUBLIC/'dists/xenial/main/binary-i386/Packages'
    if sha(index)!=data['index_sha256'] or subprocess.check_output(['git','-C',str(PUBLIC),'rev-parse','HEAD'],text=True).strip()!=data['public_head']:raise RuntimeError('Archive advanced; make a fresh plan')
    if subprocess.check_output(['git','-C',str(PUBLIC),'status','--porcelain'],text=True).strip():raise RuntimeError('Public checkout must be clean')
    allowed={str(p.relative_to(PUBLIC)) for p in select(index,PUBLIC/'pool/main')}
    if len({row['filename'] for row in data['files']})!=len(data['files']):raise RuntimeError('Duplicate retirement path')
    if not data['files']:
        print('No unindexed packages to retire');return
    for row in data['files']:
        if row['filename'] not in allowed:raise RuntimeError('Refusing to retire an indexed or unexpected path')
        package=PUBLIC/row['filename'];backup=BACKUP/package.name
        if sha(package)!=row['sha256'] or sha(backup)!=row['sha256']:raise RuntimeError('Package/backup changed')
    record=PUBLIC/'retired-packages.json'
    old=json.loads(record.read_text()) if record.exists() else {'schema':1,'files':[]}
    known={r['filename']:r for r in old['files']}
    for row in data['files']:known[row['filename']]=row
    readme=PUBLIC/'README.md'
    readme_text=readme.read_text().replace('Previous packages remain in\nthe pool for rollback.',
        'Previous packages remain available in GitHub Releases for rollback.\nOlder unindexed Pages copies may be retired after verifying downloaded backups;\n[retired-packages.json](retired-packages.json) records their URLs and SHA256 hashes.')
    guide=(ROOT/'maintenance/README.md').read_bytes()
    # All package, backup and document preflights finish before any tracked file is removed.
    for row in data['files']:subprocess.run(['git','-C',str(PUBLIC),'rm','--',row['filename']],check=True,stdout=subprocess.DEVNULL)
    dump(record,dict(schema=1,files=list(known.values())))
    readme.write_text(readme_text)
    (PUBLIC/'maintenance/README.md').write_bytes(guide)
    if sha(index)!=data['index_sha256']:raise RuntimeError('Package index unexpectedly changed')
    subprocess.run(['git','-C',str(PUBLIC),'add','retired-packages.json','README.md','maintenance/README.md'],check=True)
    subprocess.run(['git','-C',str(PUBLIC),'commit','-m','Archive unindexed packages in verified GitHub Release backups'],check=True)
    subprocess.run(['git','-C',str(PUBLIC),'push','origin','main'],check=True)
    print('Retired unindexed Pages copies; signed current index unchanged; rollback URLs in retired-packages.json')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('plan','apply'));parser.add_argument('--plan',type=Path,required=True);args=parser.parse_args()
    if args.action=='plan':plan(args.plan)
    else:
        with (ROOT/'.build/updates/coordinator.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            apply(args.plan)
