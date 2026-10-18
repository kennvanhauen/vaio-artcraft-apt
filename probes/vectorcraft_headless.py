#!/usr/bin/env python3
"""Small original vector workflow on the actual VAIO, with no display variables."""
import json, os, select, subprocess, time
from pathlib import Path
base = Path('/tmp/vaio-vectorcraft-test')
base.mkdir(parents=True, exist_ok=True)
cli = os.environ.get('VAIO_VECTOR_CLI', str(base/'vectorcraft-cli'))
env = dict(os.environ, VECTORCRAFT_NO_PREFS='1', XDG_CONFIG_HOME=str(base/'headless-config'), XDG_DATA_HOME=str(base/'headless-data'))
for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
    env.pop(key, None)
result = {'checks': [], 'timings': [], 'display_variables_absent': all(k not in env for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'))}
original = '''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320" viewBox="0 0 480 320">
<defs><linearGradient id="sky" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#12364e"/><stop offset="1" stop-color="#287d92"/></linearGradient></defs>
<rect width="480" height="320" fill="#f5f1e7"/>
<rect x="16" y="16" width="448" height="105" rx="12" fill="url(#sky)"/>
<text x="34" y="55" font-family="Inter" font-size="24" fill="#ffffff">THE REPAIR CLUB</text>
<text x="34" y="84" font-family="Inter" font-size="13" fill="#ffffff">An original vector illustration for the VAIO</text>
<path d="M 50 220 C 100 145 150 285 215 202 S 325 155 385 215" fill="none" stroke="#db7646" stroke-width="7" stroke-linecap="round"/>
<circle cx="405" cy="180" r="25" fill="#329385"/>
<path d="M395 180 L402 187 L416 171" fill="none" stroke="white" stroke-width="4"/>
<text x="34" y="285" font-family="Inter" font-size="15" fill="#12364e">Make, mend, and share.</text>
</svg>'''
(base/'original.svg').write_text(original)
def run(*args):
    at = time.monotonic()
    proc = subprocess.run([cli]+list(args), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=90)
    result['timings'].append({'action':' '.join(args[:2]),'seconds':round(time.monotonic()-at,3)})
    if proc.returncode:
        raise RuntimeError(str(args)+': '+proc.stderr[:1500])
    return proc.stdout
process = None
try:
    result['catalogue'] = json.loads(run('commands'))
    result['original_info'] = json.loads(run('info',str(base/'original.svg')))
    run('convert', str(base/'original.svg'), str(base/'original.vectorcraft'))
    result['native_info'] = json.loads(run('info',str(base/'original.vectorcraft')))
    for ext in ('svg','pdf','png','eps','dxf'):
        run('convert', str(base/'original.vectorcraft'), str(base/('export.'+ext)))
        assert (base/('export.'+ext)).stat().st_size > 80
    run('convert',str(base/'export.svg'),str(base/'roundtrip.vectorcraft'))
    result['roundtrip_info'] = json.loads(run('info',str(base/'roundtrip.vectorcraft')))
    assert (base/'export.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert (base/'export.pdf').read_bytes().startswith(b'%PDF-')
    result['checks'] += ['SVG import','native save/reopen','SVG round trip','PDF/PNG/EPS/DXF export']
    process = subprocess.Popen([cli,'mcp','--headless','--automation-read-root',str(base),'--automation-write-root',str(base)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(base/'mcp.log').open('w'),universal_newlines=True,bufsize=1)
    serial = 0
    def rpc(method, params):
        global serial
        serial += 1
        process.stdin.write(json.dumps({'jsonrpc':'2.0','id':serial,'method':method,'params':params})+'\n');process.stdin.flush()
        if not select.select([process.stdout],[],[],45)[0]:
            raise RuntimeError('MCP response timed out: '+method)
        reply = json.loads(process.stdout.readline())
        if 'error' in reply: raise RuntimeError(str(reply))
        return reply['result']
    result['mcp_initialize'] = rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'vaio-verification','version':'1'}})
    def tool(name, arguments):
        reply = rpc('tools/call',{'name':name,'arguments':arguments})
        if reply.get('isError'):raise RuntimeError(name+': '+str(reply))
        return json.loads(reply['content'][0]['text'])
    tool('open_file',{'path':str(base/'original.vectorcraft')})
    result['mcp_inspect'] = tool('doc_inspect',{'depth':2})
    added = tool('command_run',{'id':'text.create','params':{'x':34,'y':310,'text':'Headless MCP verified','font':'Inter','size':10}})
    tool('save_file',{'path':str(base/'mcp-edited.vectorcraft')})
    inspected = tool('doc_inspect',{'kind':'Type'})
    assert 'Headless MCP verified' in json.dumps(inspected), inspected
    result['mcp_text_id'] = added
    denied = rpc('tools/call',{'name':'open_file','arguments':{'path':'/etc/hostname'}})
    assert denied.get('isError'), 'Read confinement did not reject outside path'
    result['checks'] += ['explicit headless MCP','MCP text editing/save','automation path confinement']
    result['passed'] = True
except Exception as error:
    result.update(passed=False,error=str(error))
finally:
    if process:
        process.stdin.close()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
(base/'headless-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k != 'catalogue'},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
