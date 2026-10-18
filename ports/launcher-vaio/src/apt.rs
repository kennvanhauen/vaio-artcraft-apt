//! Package state comes from dpkg/APT. Only the root-owned APT helper mutates it.
use artcraft_launcher_core::protocol::{Backend, Capabilities, Command, Event, JobPhase, LatestRelease, Origin, Source};
use artcraft_launcher_core::release::{Asset, Release};
use artcraft_launcher_core::{InstallSource, Installed, Platform, version};
use std::path::{Path, PathBuf};
use std::process::Command as Process;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, mpsc};

const PACKAGE: &str = "wordcraft-vaio";
const APP: &str = "wordcraft";

fn output(program: &str, args: &[&str]) -> Result<String, String> {
    let result = Process::new(program).args(args).env("LC_ALL", "C").output().map_err(|error| format!("Cannot run {program}: {error}"))?;
    if result.stdout.len() > 1024 * 1024 || result.stderr.len() > 1024 * 1024 {
        return Err(format!("Unexpectedly large answer from {program}"));
    }
    if !result.status.success() {
        return Err(format!("{program}: {}", String::from_utf8_lossy(&result.stderr).trim()));
    }
    Ok(String::from_utf8_lossy(&result.stdout).into_owned())
}

// Preserve Debian preview revision ordering in the UI's semantic-version model.
fn display_version(value: &str) -> Option<version::Version> {
    if let Some((base, revision)) = value.split_once("~vaio") {
        if !revision.is_empty() && revision.chars().all(|c| c.is_ascii_digit()) {
            return version::parse(&format!("{base}-vaio.{revision}"));
        }
        return None;
    }
    version::parse(value)
}

fn cache_directory() -> Result<PathBuf, String> {
    let root = std::env::var_os("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .filter(|path| path.is_absolute())
        .or_else(|| std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".cache")))
        .ok_or("Cannot locate the application cache")?;
    Ok(root.join("vaio-app-launcher/apt"))
}

fn apt_options(cache: &Path) -> Vec<String> {
    vec![
        "-o".into(),
        "Dir::Etc::sourcelist=/etc/apt/sources.list.d/vaio-artcraft.list".into(),
        "-o".into(),
        "Dir::Etc::sourceparts=-".into(),
        "-o".into(),
        format!("Dir::State::lists={}", cache.join("lists").display()),
        "-o".into(),
        format!("Dir::Cache={}", cache.display()),
        "-o".into(),
        format!("Dir::Cache::pkgcache={}", cache.join("pkgcache.bin").display()),
        "-o".into(),
        format!("Dir::Cache::srcpkgcache={}", cache.join("srcpkgcache.bin").display()),
        "-o".into(),
        "Debug::NoLocking=1".into(),
        "-o".into(),
        "Acquire::Languages=none".into(),
        "-o".into(),
        "Acquire::https::Timeout=15".into(),
        "-o".into(),
        "Acquire::Retries=0".into(),
    ]
}

/// Fetch only signed project metadata, unprivileged. No system index/package changes.
pub fn refresh() -> Result<serde_json::Value, String> {
    let cache = cache_directory()?;
    for child in ["lists/partial", "archives/partial"] {
        std::fs::create_dir_all(cache.join(child)).map_err(|error| format!("Cannot prepare APT cache: {error}"))?;
    }
    let mut args = apt_options(&cache);
    args.push("update".into());
    let output =
        Process::new("apt-get").args(&args).env("LC_ALL", "C").output().map_err(|error| format!("Cannot check the signed archive: {error}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    // APT 1.2 can exit successfully after an acquisition failed and it kept old lists.
    if !output.status.success()
        || stdout.lines().any(|line| line.starts_with("Err:"))
        || stderr.lines().any(|line| line.starts_with("W:") || line.starts_with("E:"))
    {
        return Err(format!(
            "Could not refresh the signed archive; saved package state is still available. {}",
            stderr.chars().take(1200).collect::<String>()
        ));
    }
    snapshot()
}

pub fn snapshot() -> Result<serde_json::Value, String> {
    let installed = output("dpkg-query", &["-W", "-f=${db:Status-Abbrev}\t${Version}\n", PACKAGE])
        .ok()
        .and_then(|line| line.strip_prefix("ii ").and_then(|v| v.split_whitespace().next()).map(str::to_owned));
    let mut args = cache_directory().ok().filter(|cache| cache.join("lists").is_dir()).map(|cache| apt_options(&cache)).unwrap_or_default();
    args.extend(["policy".to_string(), PACKAGE.to_string()]);
    let refs: Vec<&str> = args.iter().map(String::as_str).collect();
    let policy = output("apt-cache", &refs)?;
    let candidate = policy.lines().find_map(|line| line.trim().strip_prefix("Candidate: ")).filter(|value| *value != "(none)").map(str::to_owned);
    Ok(serde_json::json!({"package": PACKAGE, "installed": installed, "candidate": candidate,
        "binary": "/usr/bin/wordcraft-vaio", "updates": "APT", "policy": policy}))
}

fn state_events() -> Result<Vec<Event>, String> {
    let snapshot = snapshot()?;
    let installed = snapshot.get("installed").and_then(|v| v.as_str()).map(|value| Installed {
        version: display_version(value),
        source: InstallSource::Deb,
        location: "/usr/bin/wordcraft-vaio".into(),
        package: Some(PACKAGE.into()),
    });
    let latest = snapshot
        .get("candidate")
        .and_then(|v| v.as_str())
        .map(|value| {
            LatestRelease::Found(Release {
                tag: value.into(),
                version: display_version(value),
                name: format!("WordCraft {value}"),
                html_url: "https://github.com/kennvanhauen/vaio-artcraft-apt/releases".into(),
                notes: "VAIO preview. Installations and updates use the signed APT archive.".into(),
                assets: vec![Asset { name: format!("wordcraft-vaio_{value}_i386.deb"), ..Default::default() }],
                ..Default::default()
            })
        })
        .unwrap_or(LatestRelease::None);
    Ok(vec![Event::Detected { app: APP.into(), installed }, Event::Latest { app: APP.into(), latest, from: Origin::Apt }])
}

pub struct AptBackend {
    sender: mpsc::Sender<Event>,
    receiver: mpsc::Receiver<Event>,
    context: egui::Context,
    query_busy: Arc<AtomicBool>,
    job_busy: Arc<AtomicBool>,
}
impl AptBackend {
    pub fn new(context: egui::Context) -> Self {
        let (sender, receiver) = mpsc::channel();
        Self { sender, receiver, context, query_busy: Arc::new(AtomicBool::new(false)), job_busy: Arc::new(AtomicBool::new(false)) }
    }
    fn query(&self, online: bool) {
        if self.query_busy.swap(true, Ordering::SeqCst) {
            return;
        }
        let sender = self.sender.clone();
        let context = self.context.clone();
        let busy = self.query_busy.clone();
        std::thread::spawn(move || {
            let _ = sender.send(Event::CheckStarted);
            let source = if online {
                match refresh() {
                    Ok(_) => Source::Apt,
                    Err(error) => {
                        let _ = sender.send(Event::JobFinished { app: APP.into(), result: Err(error) });
                        Source::Cache
                    }
                }
            } else {
                Source::Cache
            };
            match state_events() {
                Ok(events) => {
                    for event in events {
                        let _ = sender.send(event);
                    }
                }
                Err(error) => {
                    let _ = sender.send(Event::Latest { app: APP.into(), latest: LatestRelease::Failed(error), from: Origin::Apt });
                }
            }
            let _ = sender.send(Event::CheckFinished { at: now(), source, rate_limited_until: None });
            busy.store(false, Ordering::SeqCst);
            context.request_repaint();
        });
    }
    fn job(&self, app: &str, remove: bool) {
        if app != APP || self.job_busy.swap(true, Ordering::SeqCst) {
            return;
        }
        let sender = self.sender.clone();
        let context = self.context.clone();
        let busy = self.job_busy.clone();
        std::thread::spawn(move || {
            let phase = if remove { JobPhase::Removing } else { JobPhase::Installing };
            let _ = sender.send(Event::Progress { app: APP.into(), phase });
            context.request_repaint();
            // All privileged executable paths and arguments are fixed. No remote shell scripts,
            // unverified downloads, mutable user helper files or interpolated input.
            let command = if remove {
                "/usr/bin/uxterm -T 'VAIO App Launcher - APT' -e /usr/lib/artcraft-launcher-vaio/apt-action remove wordcraft-vaio"
            } else {
                "/usr/bin/uxterm -T 'VAIO App Launcher - APT' -e /usr/lib/artcraft-launcher-vaio/apt-action install wordcraft-vaio"
            };
            let expected = snapshot().ok().and_then(|state| state.get("candidate").and_then(|v| v.as_str()).map(str::to_owned));
            let result = Process::new("/usr/bin/gksu")
                .args([
                    "-S",
                    "-m",
                    "VAIO App Launcher will use APT for the WordCraft preview. Review and confirm the package operation in the terminal.",
                    command,
                ])
                .status()
                .map_err(|error| error.to_string())
                .and_then(|status| {
                    if status.success() {
                        Ok("APT operation completed".to_string())
                    } else {
                        Err("APT operation was cancelled or failed. See the APT terminal output.".into())
                    }
                });
            let result = result.and_then(|message| {
                let state = snapshot()?;
                let installed = state.get("installed").and_then(|value| value.as_str());
                let completed = if remove {
                    installed.is_none()
                } else {
                    installed.is_some_and(|actual| {
                        expected.as_deref().is_none_or(|candidate| {
                            Process::new("/usr/bin/dpkg")
                                .args(["--compare-versions", actual, "ge", candidate])
                                .status()
                                .is_ok_and(|status| status.success())
                        })
                    })
                };
                if completed {
                    Ok(message)
                } else {
                    Err("The requested package change was not completed. Your existing package state was retained.".into())
                }
            });
            if let Ok(events) = state_events() {
                for event in events {
                    let _ = sender.send(event);
                }
            }
            let _ = sender.send(Event::JobFinished { app: APP.into(), result });
            busy.store(false, Ordering::SeqCst);
            context.request_repaint();
        });
    }
}
fn now() -> i64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |value| i64::try_from(value.as_secs()).unwrap_or(i64::MAX))
}
impl Backend for AptBackend {
    fn send(&mut self, command: Command) {
        match command {
            Command::CheckForUpdates { .. } => self.query(true),
            Command::Detect => self.query(false),
            Command::Install { app } => self.job(&app, false),
            Command::Uninstall { app } => self.job(&app, true),
            Command::Launch { app } if app == APP => match Process::new("/usr/bin/wordcraft-vaio").spawn() {
                Ok(mut child) => {
                    std::thread::spawn(move || {
                        let _ = child.wait();
                    });
                }
                Err(error) => {
                    let _ = self.sender.send(Event::JobFinished { app, result: Err(error.to_string()) });
                }
            },
            Command::Reveal { app } if app == APP => {
                let _ = Process::new("xdg-open").arg("/usr/share/doc/wordcraft-vaio").spawn();
            }
            Command::FetchScreenshots { app } => {
                // The small VAIO build does not download catalog pictures.
                let _ = self.sender.send(Event::Screenshot {
                    app,
                    key: String::new(),
                    result: Err("Pictures are not included in the VAIO preview".into()),
                });
            }
            Command::Configure(_) | Command::Pause { .. } | Command::Cancel { .. } => (),
            // Self-update and replacements are exclusively owned by APT.
            _ => (),
        }
    }
    fn poll(&mut self) -> Vec<Event> {
        self.receiver.try_iter().collect()
    }
    fn capabilities(&self) -> Capabilities {
        Capabilities { manage_apps: true, reveal_label: "Show in Files", self_update: false }
    }
    fn platform(&self) -> Option<Platform> {
        Platform::current()
    }
    fn now(&self) -> i64 {
        now()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn debian_preview_revisions_keep_numeric_order() {
        assert!(display_version("0.8.0~vaio10") > display_version("0.8.0~vaio3"));
        assert!(display_version("0.8.0") > display_version("0.8.0~vaio3"));
        assert_eq!(display_version("0.8.0~vaiooops"), None);
    }
}
