use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Only launch the Python sidecar on desktop platforms.
            // On Android, the backend runs separately (e.g. via Termux).
            #[cfg(not(target_os = "android"))]
            {
                let sidecar = app.shell()
                    .sidecar("termuxcode-server")
                    .expect("failed to create sidecar command");

                let (_rx, _child) = sidecar
                    .spawn()
                    .expect("failed to spawn termuxcode-server sidecar");

                std::mem::forget(_child);
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
