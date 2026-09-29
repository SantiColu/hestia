// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // WebKitGTK renders the schematic blurry when it switches to accelerated compositing
    // (seen with WebKitGTK 2.42 on Intel + NVIDIA, X11). Without compositing it stays sharp.
    // Set only if not already set, so it can still be overridden to compare.
    #[cfg(target_os = "linux")]
    if std::env::var_os("WEBKIT_DISABLE_COMPOSITING_MODE").is_none() {
        // SAFETY: called before any other thread starts (Tauri and WebKit start later).
        unsafe { std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1") };
    }
    hestia_lib::run();
}
