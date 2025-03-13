import { useState, useEffect, useRef } from 'react';
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

interface CleaningResult {
  status: string;
  message: string;
  details: string[];
  cleaned_count: number;
  processed_count: number;
}

function App() {
  const [mayaPath, setMayaPath] = useState<string | null>(null);
  const [isReady, setIsReady] = useState<boolean>(false);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<CleaningResult | null>(null);
  const [logMessages, setLogMessages] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const dropAreaRef = useRef<HTMLDivElement>(null);

  // Check for Maya installation on startup
  useEffect(() => {
    checkMayaInstallation();
  }, []);

  // Auto-scroll the log to bottom when new messages are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logMessages]);

  const checkMayaInstallation = async () => {
    try {
      addLog("Initializing Maya File Cleaner...");
      const path = await invoke<string>('find_maya_exe');
      setMayaPath(path);
      addLog(`Found Maya Python at: ${path}`);
      setIsReady(true);
    } catch (error) {
      addLog(`Error: Maya installation not found. Please install Maya to use this tool.`);
      setIsReady(false);
    }
  };

  const addLog = (message: string) => {
    console.log("LOG:", message);
    setLogMessages(prev => [...prev, message]);
  };

  // Drag and drop handlers with enhanced logging
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropAreaRef.current) {
      dropAreaRef.current.classList.add('drag-active');
    }
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (dropAreaRef.current) {
      dropAreaRef.current.classList.remove('drag-active');
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();

    if (dropAreaRef.current) {
      dropAreaRef.current.classList.remove('drag-active');
    }

    console.log("Files dropped:", e.dataTransfer.files);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const fileList = Array.from(e.dataTransfer.files);
      console.log("Files array:", fileList);

      // For Tauri v2, we need a different approach for file paths
      const filePaths: string[] = [];
      
      for (const file of fileList) {
        // @ts-ignore - path property added by Tauri v2
        if (file.path) {
          // @ts-ignore
          const path = file.path;
          if (path.toLowerCase().endsWith('.ma') || path.toLowerCase().endsWith('.mb')) {
            filePaths.push(path);
          }
        } else {
          // Fallback for browsers not supporting path property
          addLog(`Warning: Could not get path for ${file.name}. Try using the Browse button instead.`);
        }
      }

      if (filePaths.length > 0) {
        setSelectedFiles(filePaths);

        if (filePaths.length === 1) {
          addLog(`Selected file: ${filePaths[0]}`);
        } else {
          addLog(`Selected ${filePaths.length} files`);
          filePaths.forEach(path => addLog(`  - ${path}`));
        }
      } else {
        addLog("No Maya files (.ma or .mb) were found in the dropped items or paths couldn't be accessed.");
      }
    }
  };

  const selectFiles = async () => {
    try {
      // Use Tauri v2 dialog API
      const selected = await open({
        multiple: true,
        filters: [{
          name: 'Maya Files',
          extensions: ['ma', 'mb']
        }]
      });
      
      if (selected) {
        // Convert to array if it's a single string
        const files = Array.isArray(selected) ? selected : [selected];
        
        setSelectedFiles(files);
        
        if (files.length === 1) {
          addLog(`Selected file: ${files[0]}`);
        } else {
          addLog(`Selected ${files.length} files`);
          files.forEach(path => addLog(`  - ${path}`));
        }
      }
    } catch (error) {
      console.error("File selection error:", error);
      addLog(`Error selecting files: ${error}`);
    }
  };

  const cleanSelectedFiles = async () => {
    if (selectedFiles.length === 0) {
      addLog('Please select at least one Maya file first');
      return;
    }

    setLoading(true);
    let successCount = 0;
    let totalIssuesFixed = 0;

    try {
      for (const filePath of selectedFiles) {
        addLog(`Cleaning file: ${filePath}`);
        try {
          // Try to clean the file
          const result = await invoke<CleaningResult>('clean_maya_scene', { filePath });

          // Only log details that indicate actual issues
          const relevantDetails = result.details.filter(detail =>
            !detail.includes("No issues found") &&
            !detail.includes("Processing Maya file")
          );

          if (relevantDetails.length > 0) {
            relevantDetails.forEach(detail =>
              addLog(detail.replace('infections', 'issues').replace('infected', 'affected'))
            );
          } else {
            addLog(`No issues found in ${filePath}`);
          }

          successCount++;
          totalIssuesFixed += result.cleaned_count;
        } catch (error) {
          console.error("Error cleaning file:", error);
          addLog(`Error processing ${filePath}: ${error}`);
        }
      }

      // Create a summary result
      setResults({
        status: "success",
        message: `Processed ${successCount} of ${selectedFiles.length} files, fixed ${totalIssuesFixed} issues`,
        details: [],
        cleaned_count: totalIssuesFixed,
        processed_count: successCount
      });

      addLog(`Cleaning complete: Processed ${successCount} of ${selectedFiles.length} files, fixed ${totalIssuesFixed} issues`);
    } catch (error) {
      console.error("Error in cleaning process:", error);
      addLog(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const cleanMayaUserDirs = async () => {
    setLoading(true);
    try {
      addLog('Cleaning Maya user directories...');
      const result = await invoke<CleaningResult>('clean_maya_user_dirs');
      setResults(result);
      addLog(`Cleaning complete: ${result.message.replace('infections', 'issues')}`);
      result.details.forEach(detail =>
        addLog(detail.replace('infections', 'issues').replace('infected', 'affected'))
      );
    } catch (error) {
      console.error("Error cleaning user dirs:", error);
      addLog(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const clearSelection = () => {
    setSelectedFiles([]);
    addLog('File selection cleared');
  };

  return (
    <div className="container">
      <h1>Maya File Cleaner</h1>

      <div className="instructions-card">
        <h3>How to Clean Maya Files</h3>
        <ol className="instruction-list">
          <li>Select Maya files using the Browse button or drag and drop them</li>
          <li>Click the "Clean Selected Files" button</li>
          <li>Review the log for results</li>
        </ol>
        <p className="note">Note: You can select Maya files from anywhere on your computer.</p>
      </div>

      {isReady ? (
        <div className="content-area">
          <div className="card-container">
            {/* Main Actions Card */}
            <div className="card">
              <h2>Clean Maya Files</h2>

              <div
                ref={dropAreaRef}
                className="drop-area"
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <div className="drop-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                </div>
                <p>Drag & drop Maya files here or <button onClick={selectFiles} className="browse-button">Browse...</button></p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="selected-files">
                  <div className="selected-header">
                    <strong>{selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected</strong>
                    <button onClick={clearSelection} className="clear-button">Clear</button>
                  </div>
                  <div className="file-list">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="file-item" title={file}>
                        {file}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="action-buttons">
                <button
                  onClick={cleanSelectedFiles}
                  disabled={selectedFiles.length === 0 || loading}
                  className="primary-button"
                >
                  {loading ? 'Cleaning...' : `Clean Selected File${selectedFiles.length !== 1 ? 's' : ''}`}
                </button>

                <div className="divider">OR</div>

                <button
                  onClick={cleanMayaUserDirs}
                  disabled={loading}
                  className="secondary-button"
                >
                  {loading ? 'Cleaning...' : 'Clean Maya User Settings'}
                </button>
              </div>
            </div>

            {/* Results Card (shown when there are results) */}
            {results && (
              <div className="card results-card">
                <h2>Cleaning Results</h2>
                <p className={results.status === 'success' ? 'success' : 'error'}>
                  {results.message.replace('infections', 'issues')}
                </p>
                <div className="stats">
                  <div>
                    <span>Files Processed:</span>
                    <span>{results.processed_count}</span>
                  </div>
                  <div>
                    <span>Issues Fixed:</span>
                    <span>{results.cleaned_count}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Log Card - Fixed at bottom */}
          <div className="log-card">
            <h3>Operation Log</h3>
            <div className="log-container" ref={logContainerRef}>
              {logMessages.map((message, index) => (
                <div key={index} className="log-line">
                  {message}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>Checking for Maya installation...</p>
          <div className="log-card small-log">
            <h3>Initialization Log</h3>
            <div className="log-container" ref={logContainerRef}>
              {logMessages.map((message, index) => (
                <div key={index} className="log-line">
                  {message}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;