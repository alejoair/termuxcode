// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Only launch the Python sidecar on desktop platforms.
            // On Android, the backend runs separately (e.g. via Termux).
            #[cfg(not(target_os = "android"))]
            {
                let sidecar = app.shell()
                    .sidecar("termuxcode-server")
                    .expect("failed to create sidecar command");

                let (mut _rx, _child) = sidecar
                    .spawn()
                    .expect("failed to spawn termuxcode-server sidecar");

                // Keep the child process handle alive by leaking it
                // (it will be killed when the app exits)
                std::mem::forget(_child);
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
