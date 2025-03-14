// src/App.tsx
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
  // Remove the unused mayaPath state variable
  const [isReady, setIsReady] = useState<boolean>(false);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<CleaningResult | null>(null);
  const [logMessages, setLogMessages] = useState<string[]>([]);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [showToast, setShowToast] = useState<boolean>(false);
  const [isHovering, setIsHovering] = useState<boolean>(false);

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

  // Hide toast after a few seconds
  useEffect(() => {
    if (showToast) {
      const timer = setTimeout(() => {
        setShowToast(false);
      }, 10000); // Hide after 10 seconds

      return () => clearTimeout(timer);
    }
  }, [showToast]);

  const checkMayaInstallation = async () => {
    try {
      // Only add this log message once
      addLog("Initializing Maya File Cleaner...");
      
      const path = await invoke<string>('find_maya_exe');
      // Just log the path without storing it in state
      addLog(`Found Maya Python at: ${path}`);
      
      setIsReady(true);
    } catch (error) {
      console.error("Error finding Maya:", error);
      addLog(`Error: Maya installation not found. Please install Maya to use this tool.`);
      setIsReady(false);
    }
  };

  const addLog = (message: string) => {
    console.log("LOG:", message);
    setLogMessages(prev => [...prev, message]);
  };

  // For file selection area
  const handleAreaMouseEnter = () => {
    setIsHovering(true);
  };

  const handleAreaMouseLeave = () => {
    setIsHovering(false);
  };

  // For browsing files
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
      
      // Show toast with results
      setShowToast(true);

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
      setShowToast(true);
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
      <div className="app-header">
        <h1>Maya File Cleaner</h1>
      </div>

      {isReady ? (
        <div className="content-area">
          {/* Main Actions Card */}
          <div className="main-card">
            <div 
              className={`file-select-area ${isHovering ? 'hover-active' : ''}`}
              onMouseEnter={handleAreaMouseEnter}
              onMouseLeave={handleAreaMouseLeave}
              onClick={selectFiles}
            >
              <p>Select Maya file(s)</p>
              <button 
                onClick={(e) => { e.stopPropagation(); selectFiles(); }} 
                className="browse-button"
              >
                Browse...
              </button>
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
                {loading ? (
                  <span className="button-with-spinner">
                    <span className="spinner-small"></span>
                    Cleaning...
                  </span>
                ) : (
                  `Clean Selected File${selectedFiles.length !== 1 ? 's' : ''}`
                )}
              </button>

              {/* <div className="divider">AND</div> */}

              <button
                onClick={cleanMayaUserDirs}
                disabled={loading}
                className="secondary-button"
              >
                {loading ? (
                  <span className="button-with-spinner">
                    <span className="spinner-small"></span>
                    Cleaning...
                  </span>
                ) : (
                  'Clean Maya User Settings'
                )}
              </button>
            </div>
          </div>

          {/* Log Card - Directly attached to the main card */}
          <div className="log-card">
            <h3>Operation Log</h3>
            <div className="log-container" ref={logContainerRef}>
              {logMessages.map((message, index) => (
                <div key={index} className="log-line">
                  {message}
                </div>
              ))}
              {loading && (
                <div className="log-line loading-message">
                  <span className="spinner-small"></span>
                  Processing... please wait
                </div>
              )}
            </div>
          </div>
          
          {/* Toast notification for results */}
          {showToast && results && (
            <div className="toast-notification">
              <div className="toast-content">
                <div className="toast-header">
                  <h3>Cleaning Complete</h3>
                  <button className="close-toast" onClick={() => setShowToast(false)}>×</button>
                </div>
                <p className={results.status === 'success' ? 'success' : 'error'}>
                  {results.message.replace('infections', 'issues')}
                </p>
                <div className="toast-stats">
                  <div className="stat-item">
                    <span>Files Processed:</span>
                    <span>{results.processed_count}</span>
                  </div>
                  <div className="stat-item">
                    <span>Issues Fixed:</span>
                    <span>{results.cleaned_count}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
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