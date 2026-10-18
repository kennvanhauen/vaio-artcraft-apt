//! VAIO shell for the original ArtCraft Launcher interface, using signed APT.
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

mod apt;
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
    if args.iter().any(|arg| arg == "--check") {
        match apt::snapshot() {
            Ok(snapshot) => println!("{}", snapshot),
            Err(error) => {
                eprintln!("{error}");
                std::process::exit(1);
            }
        }
        return Ok(());
    }
    let smoke = args.iter().any(|arg| arg == "--smoke");
    let viewport = egui::ViewportBuilder::default().with_inner_size([1100.0, 650.0]);
    eframe::run_native(
        "VAIO App Launcher",
        eframe::NativeOptions { renderer: eframe::Renderer::Glow, viewport, ..Default::default() },
        Box::new(move |cc| {
            let settings = Settings { close_to_tray: false, auto_update: false, preferred_kinds: vec![PackageKind::Deb], ..Default::default() };
            let mut launcher = LauncherUi::new(&cc.egui_ctx, Box::new(apt::AptBackend::new(cc.egui_ctx.clone())), settings);
            launcher.retain_apps(&["wordcraft"]);
            Ok(Box::new(Shell { launcher, host: Desktop::default(), smoke, start: Instant::now(), shot_requested: false }))
        }),
    )
}
