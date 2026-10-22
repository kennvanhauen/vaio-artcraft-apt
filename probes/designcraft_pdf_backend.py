#!/usr/bin/env python3
"""Bounded original placed-PDF geometry, raster and export check on Xenial."""
import json,os,struct,subprocess
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test/pdf-backend');base.mkdir(parents=True,exist_ok=True)
cli=os.environ.get('VAIO_DESIGN_CLI','/usr/bin/designcraft-vaio-cli')
env=dict(os.environ,DESIGNCRAFT_NO_PREFS='1',DESIGNCRAFT_CONFIG_DIR=str(base/'profile'))
for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(key,None)
result={'passed':False}
def run(*args):
    return subprocess.check_output([cli]+list(args),env=env,stderr=subprocess.STDOUT,timeout=60)
try:
    content=b'0.1 0.4 0.7 rg 20 20 100 30 re f BT /F1 16 Tf 20 110 Td (Original VAIO placed PDF) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 180] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream']
    data=b'%PDF-1.4\n';offsets=[]
    for n,obj in enumerate(objects,1):
        offsets.append(len(data));data+=str(n).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
    at=len(data);data+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(('%010d 00000 n \n'%o).encode() for o in offsets)
    data+=('trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n'%at).encode()
    source=base/'original.pdf';source.write_bytes(data)
    native=base/'placed.designcraft';raster=base/'placed.png';export=base/'placed.pdf'
    run('run','--cmd','file.new='+json.dumps({'width':420,'height':300,'pages':1,'facingPages':False}),
        '--cmd','file.place='+json.dumps({'path':str(source),'pdfPage':1,'pdfCrop':'media','x':40,'y':40,'width':240}),'--export',str(native))
    run('run','--in',str(native),'--export',str(raster))
    png=raster.read_bytes();assert png.startswith(b'\x89PNG\r\n\x1a\n') and len(png)>500
    result['raster_dimensions']=list(struct.unpack('>II',png[16:24]))
    run('run','--in',str(native),'--export',str(export))
    text=subprocess.check_output(['pdftotext',str(export),'-'],stderr=subprocess.STDOUT,timeout=30).decode()
    assert 'Original VAIO placed PDF' in text,text
    info=subprocess.check_output(['pdfinfo',str(export)],timeout=30).decode()
    assert 'Pages:          1' in info,info
    result.update(passed=True,checks=['place original one-page PDF through shared reader','native save/reopen','CPU raster output','shared PDF writer preserves independently extracted text'])
except Exception as error:result['error']=str(error)
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
