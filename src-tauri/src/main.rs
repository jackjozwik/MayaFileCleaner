// src-tauri/src/main.rs
use std::process::Command;
use std::path::Path;
use std::fs;
use std::env;
use serde::{Deserialize, Serialize};
use tauri::State;
use std::sync::Mutex;
use std::path::PathBuf;
use tauri::Runtime;
use std::io::Read;

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

// Add this function somewhere in your code
// Update these functions in your main.rs

fn resolve_path(file_path: &str) -> PathBuf {
    println!("Resolving path for: {}", file_path);
    let path = Path::new(file_path);
    
    // If it's already an absolute path, use it directly
    if path.is_absolute() {
        println!("  Path is absolute: {}", file_path);
        return path.to_path_buf();
    }
    
    // If it's just a filename, check in current directory first
    if let Ok(current_dir) = env::current_dir() {
        let full_path = current_dir.join(path);
        println!("  Checking current dir: {}", full_path.display());
        if full_path.exists() {
            println!("  Found in current dir: {}", full_path.display());
            return full_path;
        }
    }
    
    // Also check in the Tauri app directory
    if let Ok(exe_path) = env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            let app_path = exe_dir.join(path);
            println!("  Checking app dir: {}", app_path.display());
            if app_path.exists() {
                println!("  Found in app dir: {}", app_path.display());
                return app_path;
            }
        }
    }
    
    // Also check relative to the user's directory
    if let Some(home_dir) = dirs::home_dir() {
        let home_path = home_dir.join(path);
        println!("  Checking home dir: {}", home_path.display());
        if home_path.exists() {
            println!("  Found in home dir: {}", home_path.display());
            return home_path;
        }
        
        // Try in Downloads
        let downloads_path = home_dir.join("Downloads").join(path);
        println!("  Checking Downloads dir: {}", downloads_path.display());
        if downloads_path.exists() {
            println!("  Found in Downloads dir: {}", downloads_path.display());
            return downloads_path;
        }
        
        // Try in Documents
        let docs_path = home_dir.join("Documents").join(path);
        println!("  Checking Documents dir: {}", docs_path.display());
        if docs_path.exists() {
            println!("  Found in Documents dir: {}", docs_path.display());
            return docs_path;
        }
    }
    
    // If we didn't find it, return the original path
    println!("  Could not find file, returning original path: {}", path.display());
    path.to_path_buf()
}

// Then update clean_maya_scene to handle file selection more gracefully

#[tauri::command]
fn clean_maya_scene(file_path: String, state: State<AppState>) -> Result<CleaningResult, String> {
    println!("Called clean_maya_scene with path: {}", file_path);
    
    // Resolve the path first
    let resolved_path = resolve_path(&file_path);
    
    // Check if file exists
    if !resolved_path.exists() {
        println!("File does not exist after resolution: {}", resolved_path.display());
        
        // Try checking for a file with this name in common directories
        // Create a "dummy" result for now to allow testing
        return Err(format!("File does not exist: {}. Tried resolving to: {}. \nPlease copy the Maya file to the same folder as this application and try again.", 
                         file_path, resolved_path.display()));
    }
    
    println!("File exists at: {}", resolved_path.display());
    let maya_exe = find_maya_exe(state)?;
    run_cleaner_script("scene", Some(&resolved_path.to_string_lossy()), &maya_exe)
}

// Clean a directory of Maya files
#[tauri::command]
fn clean_maya_directory(dir_path: String, state: State<AppState>) -> Result<CleaningResult, String> {
    // Check if directory exists
    if !Path::new(&dir_path).exists() || !Path::new(&dir_path).is_dir() {
        return Err(format!("Directory does not exist: {}", dir_path));
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
