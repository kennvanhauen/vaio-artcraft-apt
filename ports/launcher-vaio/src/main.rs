//! VAIO shell for the original ArtCraft Launcher interface, using signed APT.
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

mod apt;
mod apt_jobs;
use artcraft_launcher_core::PackageKind;
use artcraft_launcher_ui_egui::{Host, LauncherUi, Settings};
use std::time::{Duration, Instant};

#[derive(Default)]
struct Desktop {
    quit: bool,
}
impl Host for Desktop {
    fn reduce_motion(&self) -> bool {
        true
    }
    fn quit(&mut self) {
        self.quit = true;
    }
}
struct Shell {
    launcher: LauncherUi,
    host: Desktop,
    smoke: bool,
    start: Instant,
    shot_requested: bool,
}
impl eframe::App for Shell {
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(storage, "vaio-launcher-settings", &self.launcher.settings);
    }
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.launcher.logic(ctx, &mut self.host);
        if self.host.quit {
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
        }
        if self.smoke {
            let elapsed = self.start.elapsed();
            if elapsed >= Duration::from_secs(15) {
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            } else {
                let next = if elapsed < Duration::from_secs(4) { Duration::from_secs(4) } else { Duration::from_secs(15) };
                ctx.request_repaint_after(next.saturating_sub(elapsed));
            }
        }
    }
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        self.launcher.ui(ui, &mut self.host);
        if self.smoke && self.start.elapsed() > Duration::from_secs(3) && !self.shot_requested {
            self.shot_requested = true;
            ui.ctx().send_viewport_cmd(egui::ViewportCommand::Screenshot(egui::UserData::default()));
        }
        ui.input(|input| {
            for event in &input.events {
                if let egui::Event::Screenshot { image, .. } = event {
                    let bytes: Vec<u8> = image.pixels.iter().flat_map(|pixel| pixel.to_array()).collect();
                    if let Err(error) =
                        image::save_buffer("/tmp/vaio-launcher-ui.png", &bytes, image.size[0] as u32, image.size[1] as u32, image::ColorType::Rgba8)
                    {
                        eprintln!("Screenshot failed: {error}");
                    }
                }
            }
        });
    }
}
fn main() -> eframe::Result {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|arg| arg == "--version") {
        println!("VAIO App Launcher {} (APT preview)", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }
    if args.iter().any(|arg| arg == "--check" || arg == "--refresh") {
        match if args.iter().any(|arg| arg == "--refresh") { apt::refresh() } else { apt::snapshot() } {
            Ok(snapshot) => println!("{}", snapshot),
            Err(error) => {
                eprintln!("{error}");
                std::process::exit(1);
            }
        }
        return Ok(());
    }
    let smoke = args.iter().any(|arg| arg == "--smoke");
    let pixels = (0..64)
        .flat_map(|y| {
            (0..64).flat_map(move |x| {
                let tile = ((12..29).contains(&x) || (35..52).contains(&x)) && ((12..29).contains(&y) || (35..52).contains(&y));
                if tile { [135, 184, 250, 255] } else { [32, 38, 48, 255] }
            })
        })
        .collect();
    let viewport = egui::ViewportBuilder::default()
        .with_app_id("vaio-app-launcher")
        .with_icon(egui::IconData { rgba: pixels, width: 64, height: 64 })
        .with_inner_size([1540.0, 650.0]);
    eframe::run_native(
        "VAIO App Launcher",
        eframe::NativeOptions { renderer: eframe::Renderer::Glow, viewport, persist_window: true, ..Default::default() },
        Box::new(move |cc| {
            let mut settings: Settings = cc.storage.and_then(|storage| eframe::get_value(storage, "vaio-launcher-settings")).unwrap_or_default();
            settings.close_to_tray = false;
            settings.preferred_kinds = vec![PackageKind::Deb];
            let mut launcher = LauncherUi::new(&cc.egui_ctx, Box::new(apt::AptBackend::new(cc.egui_ctx.clone())), settings);
            launcher.retain_apps(&["wordcraft", "gridcraft", "pdfcraft", "deckcraft", "vectorcraft"]);
            Ok(Box::new(Shell { launcher, host: Desktop::default(), smoke, start: Instant::now(), shot_requested: false }))
        }),
    )
}
