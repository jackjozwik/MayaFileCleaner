#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Maya File Cleaner - mayapy version
Designed to be run with mayapy.exe
"""
import os
import sys
import json
import stat
import shutil
import argparse
import tempfile
import datetime
from pathlib import Path

# Initialize standalone Maya
import maya.standalone
maya.standalone.initialize(name='python')

# Now we can import Maya commands
import maya.cmds as cmds


class MayaFileCleaner:
    def __init__(self, log_file=None):
        self.cleanup_count = 0
        self.files_processed = 0
        self.log_file = log_file
        self.results = {
            "status": "success",
            "message": "",
            "details": [],
            "cleaned_count": 0,
            "processed_count": 0
        }
        # Create backup directory in temp folder
        self.backup_dir = self.create_backup_directory()
        
    def create_backup_directory(self):
        """Create a backup directory in the temp folder"""
        # Create a "maya_cleaner_backups" directory in the OS temp folder
        temp_dir = os.path.join(tempfile.gettempdir(), "maya_cleaner_backups")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a dated subdirectory for today's backups
        today = datetime.datetime.now().strftime("%Y%m%d")
        today_dir = os.path.join(temp_dir, today)
        os.makedirs(today_dir, exist_ok=True)
        
        self.log(f"Created backup directory: {today_dir}")
        return today_dir
        
    def log(self, message):
        """Log a message to both stdout and log file if provided"""
        print(message)
        self.results["details"].append(message)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
                
    def make_writable(self, file_path):
        """Make file writable if it exists"""
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                return True
            except Exception as e:
                self.log(f"WARNING: Could not change permissions for {file_path}: {e}")
                return False
        return False
    
    def clean_usersetup_file(self, file_path):
        """Clean a userSetup.py file by removing problem sections"""
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}")
            return False
            
        # Make file writable
        self.make_writable(file_path)
        
        # Create a backup in temp directory
        file_name = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"Created backup: {backup_path}")
        except Exception as e:
            self.log(f"Failed to create backup of {file_path}: {e}")
            return False
            
        # Read the file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Check for problem signatures
            problem_detected = False
            for problem_sig in ['import fuckVirus', 'import vaccine', 'leukocyte', 'phage']:
                if problem_sig in content:
                    problem_detected = True
                    break
                    
            if not problem_detected:
                self.log(f"No issues detected in {file_path}")
                return False
                
            # Determine how many lines have issues
            lines = content.splitlines()
            problem_lines = []
            clean_lines = []
            
            for line in lines:
                is_problem_line = False
                for sig in ['fuckVirus', 'vaccine', 'leukocyte', 'phage', 'cmds.evalDeferred(']:
                    if sig in line:
                        is_problem_line = True
                        problem_lines.append(line)
                        break
                        
                if not is_problem_line:
                    clean_lines.append(line)
            
            # If most lines have issues, replace the file
            if len(problem_lines) > len(clean_lines):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# This file was cleaned of problematic code\n# Original backup saved in temp directory\n")
                self.log(f"Replaced problematic userSetup.py: {file_path}")
            else:
                # Write back only the clean lines
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(clean_lines))
                self.log(f"Selectively cleaned userSetup.py: {file_path}")
                
            self.cleanup_count += 1
            return True
                
        except Exception as e:
            self.log(f"Error cleaning {file_path}: {e}")
            return False
    
    def clean_maya_scene(self, file_path=None):
        """Clean a Maya scene file using Maya commands"""
        # If no file provided, use current scene
        if not file_path:
            file_path = cmds.file(q=True, sceneName=True)
            if not file_path:
                self.log("No file specified and no current scene")
                return False
                
        # Check if file exists
        if not os.path.exists(file_path):
            self.log(f"File does not exist: {file_path}")
            return False
            
        self.log(f"Processing Maya file: {file_path}")
        
        # Make file writable
        self.make_writable(file_path)
        
        # Create backup in temp directory
        file_name = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"Created backup: {backup_path}")
        except Exception as e:
            self.log(f"Failed to create backup of {file_path}: {e}")
        
        # Try to open the file in Maya
        try:
            # First save the current scene if there is one
            current_scene = cmds.file(q=True, sceneName=True)
            if current_scene:
                cmds.file(save=True, force=True)
                
            # Create a new scene
            cmds.file(new=True, force=True)
            
            # Open the file to clean
            cmds.file(file_path, open=True, force=True)
        except Exception as e:
            self.log(f"Failed to open file {file_path}: {e}")
            return False
            
        # Check for problematic script nodes
        issues_found = 0
        problem_node_names = ["vaccine_gene", "breed_gene", "fuckVirus_gene"]
        
        # Find all script nodes
        all_script_nodes = cmds.ls(type='script') or []
        
        for node in all_script_nodes:
            try:
                if cmds.objExists(node) and cmds.attributeQuery('before', node=node, exists=True):
                    node_code = cmds.getAttr(node + '.before') or ""
                    
                    # Check node name
                    if any(name in node for name in problem_node_names):
                        self.log(f"Found problematic node by name: {node}")
                        cmds.delete(node)
                        issues_found += 1
                        continue
                        
                    # Check code content for problematic signatures
                    for sig in ['userSetup.py', 'leukocyte', 'phage', 'cmds.scriptJob(event=["SceneSaved"', 'fuckVirus', 'vaccine']:
                        if sig in node_code:
                            self.log(f"Found problematic code in node: {node}")
                            cmds.delete(node)
                            issues_found += 1
                            break
            except Exception as e:
                self.log(f"Error checking script node {node}: {e}")
        
        # Check for problematic script jobs
        try:
            all_jobs = cmds.scriptJob(listJobs=True)
            
            for job in all_jobs:
                if any(sig in job for sig in ['leukocyte.antivirus()', 'phage', 'vaccine', 'fuckVirus']):
                    # Extract job number
                    job_num = int(job.split(':', 1)[0])
                    self.log(f"Removing problematic script job: {job}")
                    cmds.scriptJob(kill=job_num, force=True)
                    issues_found += 1
        except Exception as e:
            self.log(f"Error checking script jobs: {e}")
        
        # Save file if issues were found
        if issues_found > 0:
            try:
                cmds.file(save=True, force=True)
                self.log(f"Saved cleaned file: {file_path}")
                self.cleanup_count += issues_found
            except Exception as e:
                self.log(f"Error saving file: {e}")
                return False
                
        self.files_processed += 1
        
        if issues_found > 0:
            self.log(f"Cleaned {issues_found} issues from {file_path}")
            return True
        else:
            self.log(f"No issues found in {file_path}")
            return False
    
    def clean_maya_directories(self):
        """Clean Maya user directories of problematic files"""
        # Find Maya user directories
        maya_user_dirs = []
        
        # Common locations
        documents = os.path.expanduser("~/Documents")
        app_data = os.path.expanduser("~/AppData/Roaming")
        
        # Look in Documents/maya/VERSION/scripts
        maya_docs = os.path.join(documents, "maya")
        if os.path.exists(maya_docs):
            for version_dir in os.listdir(maya_docs):
                scripts_dir = os.path.join(maya_docs, version_dir, "scripts")
                if os.path.exists(scripts_dir):
                    maya_user_dirs.append(scripts_dir)
        
        # Look in AppData/Roaming/Autodesk/maya/VERSION/scripts
        maya_app = os.path.join(app_data, "Autodesk", "maya")
        if os.path.exists(maya_app):
            for version_dir in os.listdir(maya_app):
                scripts_dir = os.path.join(maya_app, version_dir, "scripts")
                if os.path.exists(scripts_dir):
                    maya_user_dirs.append(scripts_dir)
        
        # Also check Maya's internal variable
        try:
            maya_script_dir = cmds.internalVar(userScriptDir=True)
            if maya_script_dir and os.path.exists(maya_script_dir):
                maya_user_dirs.append(maya_script_dir)
        except:
            pass
        
        # Remove duplicates
        maya_user_dirs = list(set(maya_user_dirs))
        
        self.log(f"Found {len(maya_user_dirs)} Maya user directories")
        
        # Clean each directory
        for scripts_dir in maya_user_dirs:
            self.log(f"Checking directory: {scripts_dir}")
            
            # Check userSetup.py
            usersetup_py = os.path.join(scripts_dir, 'userSetup.py')
            if os.path.exists(usersetup_py):
                self.clean_usersetup_file(usersetup_py)
            
            # Remove known problematic files
            problem_files = [
                os.path.join(scripts_dir, 'userSetup.mel'),
                os.path.join(scripts_dir, 'vaccine.py'),
                os.path.join(scripts_dir, 'fuckVirus.py')
            ]
            
            for file_path in problem_files:
                if os.path.exists(file_path):
                    try:
                        # Make writable
                        self.make_writable(file_path)
                        
                        # Create backup in temp directory
                        file_name = os.path.basename(file_path)
                        timestamp = datetime.datetime.now().strftime("%H%M%S")
                        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
                        shutil.copy2(file_path, backup_path)
                        self.log(f"Created backup: {backup_path}")
                        
                        # Remove file
                        os.remove(file_path)
                        
                        self.log(f"Removed problematic file: {file_path}")
                        self.cleanup_count += 1
                    except Exception as e:
                        self.log(f"Failed to remove {file_path}: {e}")
    
    def batch_clean_directory(self, directory_path):
        """Clean all Maya files in a directory"""
        if not os.path.exists(directory_path):
            self.log(f"Directory does not exist: {directory_path}")
            return False
            
        self.log(f"Scanning directory: {directory_path}")
        
        # Find all Maya files
        maya_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(('.ma', '.mb')):
                    maya_files.append(os.path.join(root, file))
        
        self.log(f"Found {len(maya_files)} Maya files to process")
        
        # Process each file
        for file_path in maya_files:
            try:
                self.clean_maya_scene(file_path)
            except Exception as e:
                self.log(f"Error processing {file_path}: {e}")
                
        return True
    
    def get_results(self):
        """Get the final results as a JSON object"""
        self.results["cleaned_count"] = self.cleanup_count
        self.results["processed_count"] = self.files_processed
        self.results["message"] = f"Processed {self.files_processed} files, cleaned {self.cleanup_count} issues"
        return self.results


def main():
    parser = argparse.ArgumentParser(description='Maya File Cleaner')
    parser.add_argument('--mode', choices=['scene', 'directory', 'user'], required=True,
                       help='Cleaning mode: single scene, directory, or user directories')
    parser.add_argument('--path', help='Path to Maya file or directory')
    parser.add_argument('--log', help='Path to write log file')
    parser.add_argument('--json', help='Path to write JSON results')
    
    args = parser.parse_args()
    
    # Initialize cleaner
    cleaner = MayaFileCleaner(log_file=args.log)
    
    try:
        # Run appropriate cleaning mode
        if args.mode == 'scene':
            if not args.path:
                cleaner.log("Error: --path is required for scene mode")
                sys.exit(1)
            cleaner.clean_maya_scene(args.path)
            
        elif args.mode == 'directory':
            if not args.path:
                cleaner.log("Error: --path is required for directory mode")
                sys.exit(1)
            cleaner.batch_clean_directory(args.path)
            
        elif args.mode == 'user':
            cleaner.clean_maya_directories()
            
        # Write JSON results if requested
        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(cleaner.get_results(), f, indent=2)
                
        # Print final summary
        cleaner.log(f"=== CLEANING COMPLETE ===")
        cleaner.log(f"Files processed: {cleaner.files_processed}")
        cleaner.log(f"Issues fixed: {cleaner.cleanup_count}")
        
    except Exception as e:
        cleaner.log(f"ERROR: {str(e)}")
        cleaner.results["status"] = "error"
        cleaner.results["message"] = str(e)
        
        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(cleaner.get_results(), f, indent=2)
                
        sys.exit(1)
        
    finally:
        # Ensure proper Maya shutdown
        try:
            maya.standalone.uninitialize()
        except:
            pass


if __name__ == "__main__":
    main()