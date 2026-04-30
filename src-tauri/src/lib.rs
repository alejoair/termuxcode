use std::sync::Mutex;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

static SIDECAR_CHILD: Mutex<Option<CommandChild>> = Mutex::new(None);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            // Only launch the Python sidecar on desktop platforms.
            // On Android, the backend runs separately (e.g. via Termux).
            #[cfg(not(target_os = "android"))]
            {
                let sidecar = app.shell()
                    .sidecar("termuxcode-server")
                    .expect("failed to create sidecar command");

                let (_rx, child) = sidecar
                    .spawn()
                    .expect("failed to spawn termuxcode-server sidecar");

                *SIDECAR_CHILD.lock().unwrap() = Some(child);
            }

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Ok(mut guard) = SIDECAR_CHILD.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                }
                // Also kill any remaining termuxcode-server processes
                #[cfg(target_os = "windows")]
                {
                    let _ = std::process::Command::new("taskkill")
                        .args(["/F", "/IM", "termuxcode-server.exe"])
                        .output();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
