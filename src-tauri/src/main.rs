#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

// src-tauri/src/main.rs
use std::process::Command;
use std::path::Path;
use std::fs;
use std::env;
use std::io::Write;
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

// App state to hold cached Maya executable path and script path
struct AppState {
    maya_exe_path: Mutex<Option<String>>,
    script_path: Mutex<Option<String>>,
}

// Embed the Python script directly into the executable as a byte array
// This will be extracted at runtime to a temporary file
const EMBEDDED_SCRIPT: &[u8] = include_bytes!("../utils.py");

fn main() {
    // Extract the script on startup instead of searching for it
    let script_path = match extract_script_to_temp() {
        Ok(path) => path,
        Err(e) => {
            eprintln!("Warning: Could not extract cleaner script: {}", e);
            String::new()
        }
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .manage(AppState {
            maya_exe_path: Mutex::new(None),
            script_path: Mutex::new(Some(script_path)),
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

// Extract the embedded script to a temporary file
fn extract_script_to_temp() -> Result<String, String> {
    let temp_dir = env::temp_dir();
    let script_path = temp_dir.join("utils.py");
    
    // Write the embedded script to the temporary file
    let mut file = fs::File::create(&script_path)
        .map_err(|e| format!("Failed to create temporary script file: {}", e))?;
    
    file.write_all(EMBEDDED_SCRIPT)
        .map_err(|e| format!("Failed to write script content: {}", e))?;
    
    println!("Extracted script to: {:?}", script_path);
    Ok(script_path.to_string_lossy().to_string())
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
fn run_utils(
    mode: &str, 
    path: Option<&str>, 
    maya_exe: &str,
    state: State<AppState>
) -> Result<CleaningResult, String> {
    // Get the script path from state
    let script_path = {
        let script_path_lock = state.script_path.lock().unwrap();
        match &*script_path_lock {
            Some(path) => path.clone(),
            None => return Err("Cleaner script not available".to_string())
        }
    };
    
    // Check if the script exists
    if !Path::new(&script_path).exists() {
        return Err(format!("Cleaner script not found at: {}", script_path));
    }
    
    // Temporary files for results and logs
    let temp_dir = env::temp_dir();
    let results_file = temp_dir.join("maya_cleaner_results.json");
    let log_file = temp_dir.join("maya_cleaner_log.txt");
    
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
    
    println!("Running command: {:?}", cmd);
    
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
    let maya_exe = find_maya_exe(state.clone())?;
    run_utils("scene", Some(&file_path), &maya_exe, state)
}

// Clean a directory of Maya files
#[tauri::command]
fn clean_maya_directory(dir_path: String, state: State<AppState>) -> Result<CleaningResult, String> {
    // Check if directory exists
    let path = Path::new(&dir_path);
    if !path.exists() || !path.is_dir() {
        return Err(format!("Directory not found: {}", dir_path));
    }
    
    let maya_exe = find_maya_exe(state.clone())?;
    run_utils("directory", Some(&dir_path), &maya_exe, state)
}

// Clean Maya user directories
#[tauri::command]
fn clean_maya_user_dirs(state: State<AppState>) -> Result<CleaningResult, String> {
    let maya_exe = find_maya_exe(state.clone())?;
    run_utils("user", None, &maya_exe, state)
}