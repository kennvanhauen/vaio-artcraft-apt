#!/usr/bin/env python3
"""Regenerate patches only for explicitly owned downstream source files."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1]
owned={
 'deckcraft':['Cargo.lock','apps/deckcraft/Cargo.toml','apps/deckcraft/src/main.rs','apps/deckcraft/src/save_names.rs','apps/deckcraft/src/screensaver.rs','crates/ui-egui/src/canvas.rs','crates/ui-egui/src/lib.rs','crates/ui-egui/src/show.rs'],
 'gridcraft':['Cargo.lock','apps/gridcraft/Cargo.toml','apps/gridcraft/src/main.rs','crates/ui-egui/src/lib.rs'],
 'pdfcraft':['Cargo.lock','apps/pdfcraft/src/main.rs','crates/ui-egui/src/widgets.rs','crates/ocr/src/lib.rs','crates/ui-egui/src/pickers.rs','crates/ui-egui/src/editing.rs','crates/ui-egui/src/print_ui.rs','crates/ui-egui/src/create_ui.rs','crates/ui-egui/src/sign_ui.rs'],
 'launcher':['crates/core/src/protocol.rs','crates/ui-egui/src/app.rs','crates/ui-egui/src/model.rs','crates/ui-egui/src/views.rs','crates/ui-egui/src/icons.rs','crates/ui-egui/src/dialogs.rs']}
for app,names in owned.items():
 upstream=root/'upstream'/('craft-launcher' if app=='launcher' else app)
 target=root/'.build'/(app+'-port')
 diff=''
 for name in names:diff+=''.join(difflib.unified_diff(((upstream/name).read_text() if (upstream/name).exists() else '').splitlines(True),(target/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
 (root/'ports'/(app+'-xenial.patch')).write_text(diff)
 (root/'ports'/(app+'-vaio.Cargo.lock')).write_bytes((target/'Cargo.lock').read_bytes())
