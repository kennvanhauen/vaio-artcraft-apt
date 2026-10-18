#!/usr/bin/env python3
"""Prepare the pinned DeckCraft Atom/Glow tree without modifying upstream."""
from pathlib import Path
import difflib,io,subprocess,tarfile
root=Path(__file__).resolve().parents[1]
revision='cb78440a1618e6a2c1df55dd7bff74719685518c'
source=root/'upstream/deckcraft';target=root/'.build/deckcraft-port'
if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=revision:
    raise SystemExit('Unexpected upstream revision')
if target.exists():raise SystemExit('Build tree already exists; inspect it before reusing')
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as a:
    a.extractall(target,filter='data')
patch=root/'ports/deckcraft-xenial.patch'
if patch.exists():
    subprocess.run(['patch','-p1','-i',str(patch)],cwd=target,check=True)
else:
    f=target/'apps/deckcraft/Cargo.toml';f.write_text(f.read_text()+'''\n[target.'cfg(all(target_os = "linux", target_arch = "x86"))'.dependencies]\neframe = { workspace = true, features = ["glow"] }\n''')
    f=target/'apps/deckcraft/src/main.rs';s=f.read_text()
    s=s.replace('fn on_exit(&mut self) {','fn on_exit(&mut self, #[cfg(all(target_os = "linux", target_arch = "x86"))] _gl: Option<&eframe::glow::Context>) {')
    s=s.replace('    options.viewport = options.viewport.with_app_id(APP_ID);','''    #[cfg(all(target_os = "linux", target_arch = "x86"))]
    {
        options.renderer = eframe::Renderer::Glow;
        options.viewport = options.viewport.with_inner_size([1100.0, 650.0]);
    }
    options.viewport = options.viewport.with_app_id(APP_ID);''')
    f.write_text(s)
    diff=''
    for name in ['apps/deckcraft/Cargo.toml','apps/deckcraft/src/main.rs']:
        diff+=''.join(difflib.unified_diff((source/name).read_text().splitlines(True),(target/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    patch.write_text(diff)
lock=root/'ports/deckcraft-vaio.Cargo.lock'
if lock.exists():(target/'Cargo.lock').write_bytes(lock.read_bytes())
print(target)
