#!/usr/bin/env python3
"""Keep original opaque chart parts through PPTX/native/native/PPTX on the Atom."""
import io,json,os,posixpath,subprocess,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('/tmp/vaio-deckcraft-test')
cli=os.environ.get('VAIO_DECK_CLI',str(base/'deckcraft-cli'))
result={'passed':False}
def convert(source,target):
    subprocess.check_output([cli,'convert',str(source),str(target)],stderr=subprocess.STDOUT,timeout=45)
try:
    with zipfile.ZipFile(str(base/'original.pptx')) as z:
        entries={n:z.read(n) for n in z.namelist()}
    chart=next(n for n in entries if n.startswith('ppt/charts/chart') and n.endswith('.xml'))
    c='http://schemas.openxmlformats.org/drawingml/2006/chart'
    r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    ct='http://schemas.openxmlformats.org/package/2006/content-types'
    root=ET.fromstring(entries[chart])
    ET.SubElement(root,'{'+c+'}externalData',{'{'+r+'}id':'rOwnedWorkbook'})
    ET.SubElement(root,'{'+c+'}userShapes',{'{'+r+'}id':'rOwnedDrawing'})
    entries[chart]=ET.tostring(root,encoding='utf-8')
    relpath=posixpath.dirname(chart)+'/_rels/'+posixpath.basename(chart)+'.rels'
    rels=ET.fromstring(entries[relpath]) if relpath in entries else ET.Element('{'+relns+'}Relationships')
    payloads=[('ppt/embeddings/owned.xlsx',b'original-synthetic-workbook\x00\xff\x80','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','package','rOwnedWorkbook'),
              ('ppt/drawings/owned.xml',b'<c:userShapes xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>','application/vnd.openxmlformats-officedocument.drawingml.chartshapes+xml','chartUserShapes','rOwnedDrawing')]
    types=ET.fromstring(entries['[Content_Types].xml'])
    for name,data,content,kind,rid in payloads:
        entries[name]=data
        ET.SubElement(rels,'{'+relns+'}Relationship',{'Id':rid,'Type':r+'/'+kind,'Target':posixpath.relpath(name,posixpath.dirname(chart))})
        ET.SubElement(types,'{'+ct+'}Override',{'PartName':'/'+name,'ContentType':content})
    entries[relpath]=ET.tostring(rels,encoding='utf-8')
    entries['[Content_Types].xml']=ET.tostring(types,encoding='utf-8')
    source=base/'owned-chart.pptx'
    with zipfile.ZipFile(str(source),'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in entries.items():z.writestr(name,data)
    first=base/'owned-chart.deckcraft';second=base/'owned-chart-again.deckcraft';back=base/'owned-chart-back.pptx'
    convert(source,first);convert(first,second);convert(second,back)
    with zipfile.ZipFile(str(back)) as z:
        contents=[z.read(n) for n in z.namelist()]
        for name,data,content,kind,rid in payloads:
            assert data in contents,'Opaque chart part lost: '+name
    result.update(passed=True,checks=['two native save/reopen cycles preserve original opaque workbook and chart drawing bytes'])
except Exception as error:result['error']=str(error)
(base/'chart-roundtrip-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
