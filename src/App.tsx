import { useState, useEffect, useRef } from 'react';
import { invoke } from "@tauri-apps/api/core";
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
  const fileInputRef = useRef<HTMLInputElement>(null);
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

      // Get filenames only for now
      const filenames = fileList.map(file => file.name);
      console.log("Filenames:", filenames);

      // Filter Maya files
      const mayaFiles = filenames.filter(name =>
        name.toLowerCase().endsWith('.ma') ||
        name.toLowerCase().endsWith('.mb')
      );

      if (mayaFiles.length > 0) {
        setSelectedFiles(mayaFiles);

        if (mayaFiles.length === 1) {
          addLog(`Selected file: ${mayaFiles[0]}`);
        } else {
          addLog(`Selected ${mayaFiles.length} files`);
          mayaFiles.forEach(path => addLog(`  - ${path}`));
        }
      } else {
        addLog("No Maya files (.ma or .mb) were found in the dropped items.");
      }
    }
  };

  const selectFiles = () => {
    // Use the hidden file input
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Updated file handling to get full paths in App.tsx

  // Replace handleFileInputChange with this version:
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    console.log("Files selected:", files);

    if (files && files.length > 0) {
      // Try to get full paths if possible
      // In Tauri v2, we need to try different approaches for file paths

      const selectedPaths: string[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        console.log(`File ${i} details:`, file);

        // Try all possible ways to get the path
        // @ts-ignore - path might exist on File in Tauri
        const path = file.path || (file as any).webkitRelativePath || file.name;

        // Log what we found
        console.log(`Found path for ${file.name}:`, path);
        selectedPaths.push(path);

        // Also try to log all properties on the file object
        console.log("All properties:", Object.getOwnPropertyNames(file));
      }

      if (selectedPaths.length > 0) {
        setSelectedFiles(selectedPaths);

        if (selectedPaths.length === 1) {
          addLog(`Selected file: ${selectedPaths[0]}`);
        } else {
          addLog(`Selected ${selectedPaths.length} files`);
          selectedPaths.forEach(path => addLog(`  - ${path}`));
        }
      }
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
    // Also reset the file input if needed
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    addLog('File selection cleared');
  };


  return (
    <div className="container">
      <h1>Maya File Cleaner</h1>

      <div className="instructions-card">
        <h3>How to Clean Maya Files</h3>
        <ol className="instruction-list">
          <li>Copy your Maya files to the same folder as this application</li>
          <li>Click Browse and select the files you want to clean</li>
          <li>Click the "Clean Selected Files" button</li>
        </ol>
        <p className="note">Note: Place Maya files in the same directory as this app for best results.</p>
      </div>

      {/* Hidden file input element */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        multiple
        accept=".ma,.mb"
        onChange={handleFileInputChange}
      />

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