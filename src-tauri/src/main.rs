// src-tauri/src/main.rs
use std::process::Command;
use std::path::{Path, PathBuf};
use std::fs;
use std::env;
use serde::{Deserialize, Serialize};
use tauri::State;
use std::sync::Mutex;

// Define the result structure that matches our Python script output
#[derive(Debug, Serialize, Deserialize)]
struct CleaningResult {
    status: String,
    message: String,
    details: Vec<String>,
    cleaned_count: u32,
    processed_count: u32,
}

// App state to hold cached Maya executable path
struct AppState {
    maya_exe_path: Mutex<Option<String>>,
}

fn main() {
    // Copy the cleaner script to necessary locations
    if let Err(e) = setup_cleaner_script() {
        eprintln!("Warning: Could not setup cleaner script: {}", e);
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .manage(AppState {
            maya_exe_path: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            find_maya_exe,
            clean_maya_scene,
            clean_maya_directory,
            clean_maya_user_dirs
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// Ensure cleaner script is in both required locations
fn setup_cleaner_script() -> Result<(), String> {
    // Source script path
    let tauri_dir = match std::env::current_dir() {
        Ok(path) => path,
        Err(e) => return Err(format!("Failed to get current directory: {}", e))
    };
    
    let source_script = tauri_dir.join("cleaner_script.py");
    
    // Target script path in debug directory
    let debug_dir = tauri_dir.join("target").join("debug");
    let debug_script = debug_dir.join("cleaner_script.py");
    
    if source_script.exists() {
        // Create directories if they don't exist
        if !debug_dir.exists() {
            if let Err(e) = fs::create_dir_all(&debug_dir) {
                return Err(format!("Failed to create debug directory: {}", e));
            }
        }
        
        // Copy script to debug directory
        if let Err(e) = fs::copy(&source_script, &debug_script) {
            return Err(format!("Failed to copy script to debug directory: {}", e));
        }
        
        Ok(())
    } else {
        Err(format!("Source script not found at: {:?}", source_script))
    }
}

// Find Maya's Python executable (mayapy.exe)
#[tauri::command]
fn find_maya_exe(state: State<AppState>) -> Result<String, String> {
    // Check if we already found the path
    {
        let cached_path = state.maya_exe_path.lock().unwrap();
        if let Some(path) = &*cached_path {
            return Ok(path.clone());
        }
    }
    
    // Common locations to check for Maya installation
    let mut possible_locations = Vec::new();
    
    // Check Program Files (newest versions first)
    for year in (2020..=2025).rev() {
        possible_locations.push(format!("C:\\Program Files\\Autodesk\\Maya{}\\bin\\mayapy.exe", year));
    }
    
    // Try to find mayapy.exe
    for location in possible_locations {
        if Path::new(&location).exists() {
            // Cache the found path
            let mut cached_path = state.maya_exe_path.lock().unwrap();
            *cached_path = Some(location.clone());
            
            return Ok(location);
        }
    }
    
    Err("Maya Python executable (mayapy.exe) not found. Please install Maya or specify the path manually.".to_string())
}

// Run the cleaner script with Maya Python
fn run_cleaner_script(
    mode: &str, 
    path: Option<&str>, 
    maya_exe: &str
) -> Result<CleaningResult, String> {
    // Temporary files for results and logs
    let temp_dir = env::temp_dir();
    let results_file = temp_dir.join("maya_cleaner_results.json");
    let log_file = temp_dir.join("maya_cleaner_log.txt");
    
    // First check both possible script locations
    let tauri_dir = match std::env::current_dir() {
        Ok(path) => path,
        Err(e) => return Err(format!("Failed to get current directory: {}", e))
    };
    
    let script_path_1 = tauri_dir.join("cleaner_script.py");
    let script_path_2 = tauri_dir.join("target").join("debug").join("cleaner_script.py");
    
    let script_path = if script_path_2.exists() {
        script_path_2
    } else if script_path_1.exists() {
        script_path_1
    } else {
        return Err(format!("Cleaner script not found. Checked locations:\n1. {:?}\n2. {:?}", 
                          script_path_1, script_path_2));
    };
    
    // Build the command
    let mut cmd = Command::new(maya_exe);
    cmd.arg(&script_path)
       .arg("--mode")
       .arg(mode)
       .arg("--log")
       .arg(&log_file)
       .arg("--json")
       .arg(&results_file);
    
    // Add path if provided
    if let Some(p) = path {
        cmd.arg("--path").arg(p);
    }
    
    // Run the command
    let output = cmd.output().map_err(|e| format!("Failed to run Maya Python: {}", e))?;
    
    if !output.status.success() {
        // Read the log file if available
        let error_message = if log_file.exists() {
            fs::read_to_string(&log_file).unwrap_or_else(|_| {
                String::from_utf8_lossy(&output.stderr).to_string()
            })
        } else {
            String::from_utf8_lossy(&output.stderr).to_string()
        };
        
        return Err(format!("Maya cleaner script failed: {}", error_message));
    }
    
    // Read the results JSON
    if !results_file.exists() {
        return Err("Results file not created".to_string());
    }
    
    let results_json = fs::read_to_string(&results_file)
        .map_err(|e| format!("Failed to read results file: {}", e))?;
    
    let results: CleaningResult = serde_json::from_str(&results_json)
        .map_err(|e| format!("Failed to parse results: {}", e))?;
    
    Ok(results)
}

// Clean a Maya scene file
#[tauri::command]
fn clean_maya_scene(file_path: String, state: State<AppState>) -> Result<CleaningResult, String> {
    println!("Called clean_maya_scene with path: {}", file_path);
    
    // Validate the path exists
    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("File not found: {}. Please check if the file exists and you have permission to access it.", file_path));
    }
    
    // Check if it's a Maya file
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    if ext.to_lowercase() != "ma" && ext.to_lowercase() != "mb" {
        return Err(format!("File is not a Maya file (.ma or .mb): {}", file_path));
    }
    
    println!("File exists at: {}", file_path);
    let maya_exe = find_maya_exe(state)?;
    run_cleaner_script("scene", Some(&file_path), &maya_exe)
}

// Clean a directory of Maya files
#[tauri::command]
fn clean_maya_directory(dir_path: String, state: State<AppState>) -> Result<CleaningResult, String> {
    // Check if directory exists
    let path = Path::new(&dir_path);
    if !path.exists() || !path.is_dir() {
        return Err(format!("Directory not found: {}", dir_path));
    }
    
    let maya_exe = find_maya_exe(state)?;
    run_cleaner_script("directory", Some(&dir_path), &maya_exe)
}

// Clean Maya user directories
#[tauri::command]
fn clean_maya_user_dirs(state: State<AppState>) -> Result<CleaningResult, String> {
    let maya_exe = find_maya_exe(state)?;
    run_cleaner_script("user", None, &maya_exe)
}