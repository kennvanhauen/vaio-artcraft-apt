//! Original VAIO validation fixture. Output only; never creates a recorder.
use serde_json::{Value, json};
use soundcraft_engine::Engine;
use soundcraft_playback::{AudioConfig, Player};
use soundcraft_time::Range;
use std::time::{Duration, Instant};

fn run() -> Result<Value, String> {
    let file = std::env::args().nth(1).ok_or("pass the synthetic session's WAV")?;
    let seconds = std::env::args().nth(2).unwrap_or_else(|| "10".into()).parse::<u64>().map_err(|e| e.to_string())?;
    if !(2..=30).contains(&seconds) {
        return Err("duration must be between 2 and 30 seconds".into());
    }
    let gain_db = std::env::args().nth(3).unwrap_or_else(|| "-12".into()).parse::<f32>().map_err(|e| e.to_string())?;
    if !gain_db.is_finite() || !(-24.0..=6.0).contains(&gain_db) {
        return Err("fixture gain must be between -24 and +6 dB".into());
    }
    let mut engine = Engine::default();
    engine.execute("session.new", &json!({"name":"VAIO output check","sample_rate":48000})).map_err(|e| e.to_string())?;
    engine.execute("file.import_audio", &json!({"path":file})).map_err(|e| e.to_string())?;
    engine.execute("edit.select_all", &json!({})).map_err(|e| e.to_string())?;
    // Additional attenuation on already quiet, synthetic media.
    engine.execute("mix.volume", &json!({"db":gain_db})).map_err(|e| e.to_string())?;
    let end = engine.session().content_end();
    if end < 48000 {
        return Err("synthetic source must last at least one second".into());
    }
    let config = AudioConfig { sample_rate: Some(48000), buffer_size: Some(4096), ..Default::default() };
    let player = Player::with_config(engine.session_arc(), &config);
    if player.silent {
        return Err("SoundCraft could not open a real output stream (silent-clock fallback)".into());
    }
    let device = player.device_name.clone();
    let rate = player.device_rate;
    let channels = player.device_channels;
    let buffer = player.device_buffer;
    let start = Instant::now();
    player.play(0, None, Some(Range::new(0, end)));
    let mut positions = Vec::new();
    let mut max_peak = 0.0_f32;
    while start.elapsed() < Duration::from_secs(seconds) {
        std::thread::sleep(Duration::from_millis(100));
        if let Some(trouble) = player.trouble() {
            return Err(format!("output trouble: {trouble:?}"));
        }
        positions.push(player.position());
        for peak in player.meters().main.peak {
            max_peak = max_peak.max(peak);
        }
        if !player.is_playing() {
            return Err("output stopped unexpectedly".into());
        }
    }
    player.stop();
    std::thread::sleep(Duration::from_millis(200));
    if let Some(trouble) = player.trouble() {
        return Err(format!("output trouble at stop: {trouble:?}"));
    }
    let changes = positions.windows(2).filter(|pair| pair.first() != pair.get(1)).count();
    if changes < (seconds * 5) as usize {
        return Err(format!("transport advanced only {changes} times"));
    }
    if !(0.00001..0.15).contains(&max_peak) {
        return Err(format!("unexpected output peak {max_peak}"));
    }
    let result = json!({"passed":true,"device":device,"rate":rate,"channels":channels,
                       "buffer":buffer,"silent":false,"seconds":seconds,
                       "position_changes":changes,"elapsed_seconds":start.elapsed().as_secs_f64(),
                       "stopped":!player.is_playing(),"recorder_created":false,"max_peak":max_peak,"track_gain_db":gain_db});
    drop(player);
    Ok(result)
}

fn main() -> std::process::ExitCode {
    match run() {
        Ok(result) => {
            println!("{result}");
            std::process::ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("{}", json!({"passed":false,"error":error}));
            std::process::ExitCode::FAILURE
        }
    }
}
