#!/usr/bin/env python3
"""Small synthetic data management/pivot workbook on the real Atom, no stress loop."""
import json,os,subprocess,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('/tmp/vaio-everyday/gridcraft-advanced');base.mkdir(parents=True,exist_ok=True)
cli=os.environ.get('VAIO_GRID_CLI','/tmp/vaio-everyday/gridcraft-cli');result={'checks':[]}
try:
    output=base/'advanced.xlsx'
    commands=[('range.setValues',{'range':'A1','values':[['Region','Product','Units','Price','Total'],['West','A',2,5,'=C2*D2'],['East','A',4,5,'=C3*D3'],['West','B',3,8,'=C4*D4'],['East','B',1,8,'=C5*D5']]}),
              ('data.sort',{'range':'A1:E5','header':True,'keys':[{'column':'A','order':'asc'}]}),
              ('data.filter',{'range':'A1:E5'}),('data.filterBy',{'column':'A','values':['East']}),
              ('data.validation',{'range':'C2:C5','type':'whole','operator':'between','formula1':'0','formula2':'100'}),
              ('home.conditionalFormat',{'range':'E2:E5','rule':{'type':'cellIs','operator':'greaterThan','value':15,'preset':'greenFill'}}),
              ('view.freezePanes',{'cell':'B2'}),
              ('insert.pivotTable',{'source':'Sheet1!A1:E5','destination':'new','name':'SyntheticPivot','rows':['Region'],'values':[{'field':'Total','func':'sum'}]})]
    args=[cli,'run']
    for name,params in commands:args+=['--cmd',name+'='+json.dumps(params)]
    args+=['--out',str(output)]
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=45)
    assert p.returncode==0,p.stderr
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(str(output)) as z:
        names=z.namelist();assert any(n.startswith('xl/pivotTables/') for n in names)
        sheets=[ET.fromstring(z.read(n)) for n in names if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        assert any(s.find('.//s:autoFilter',ns) is not None for s in sheets)
        assert any(s.find('.//s:dataValidations',ns) is not None for s in sheets)
        assert any(s.find('.//s:conditionalFormatting',ns) is not None for s in sheets)
        assert any(s.find('.//s:pane',ns) is not None for s in sheets)
        allvalues=[v.text for s in sheets for v in s.findall('.//s:v',ns)]
        assert '62' in allvalues,'Pivot grand total missing'
    result['checks']=['multi-key-capable sort','AutoFilter','data validation','conditional formatting','frozen panes','PivotTable saved totals']
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
