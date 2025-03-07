#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Maya Virus Cleaner - mayapy version
Designed to be run with mayapy.exe
"""
import os
import sys
import json
import stat
import shutil
import argparse
from pathlib import Path

# Initialize standalone Maya
import maya.standalone
maya.standalone.initialize(name='python')

# Now we can import Maya commands
import maya.cmds as cmds


class MayaVirusCleaner:
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
        """Clean a userSetup.py file by removing virus sections"""
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}")
            return False
            
        # Make file writable
        self.make_writable(file_path)
        
        # Create a backup
        backup_path = f"{file_path}.backup"
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
                
            # Check for virus signatures
            virus_detected = False
            for virus_sig in ['import fuckVirus', 'import vaccine', 'leukocyte', 'phage']:
                if virus_sig in content:
                    virus_detected = True
                    break
                    
            if not virus_detected:
                self.log(f"No virus detected in {file_path}")
                return False
                
            # Determine how many lines are virus related
            lines = content.splitlines()
            virus_lines = []
            clean_lines = []
            
            for line in lines:
                is_virus_line = False
                for sig in ['fuckVirus', 'vaccine', 'leukocyte', 'phage', 'cmds.evalDeferred(']:
                    if sig in line:
                        is_virus_line = True
                        virus_lines.append(line)
                        break
                        
                if not is_virus_line:
                    clean_lines.append(line)
            
            # If most lines are virus related, replace the file
            if len(virus_lines) > len(clean_lines):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# This file was cleaned of virus code\n# Original backup saved as .backup\n")
                self.log(f"Replaced heavily infected userSetup.py: {file_path}")
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
        
        # Create backup
        backup_path = f"{file_path}.backup"
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
            
        # Check for virus script nodes
        infections_found = 0
        virus_node_names = ["vaccine_gene", "breed_gene", "fuckVirus_gene"]
        
        # Find all script nodes
        all_script_nodes = cmds.ls(type='script') or []
        
        for node in all_script_nodes:
            try:
                if cmds.objExists(node) and cmds.attributeQuery('before', node=node, exists=True):
                    node_code = cmds.getAttr(node + '.before') or ""
                    
                    # Check node name
                    if any(virus_name in node for virus_name in virus_node_names):
                        self.log(f"Found virus node by name: {node}")
                        cmds.delete(node)
                        infections_found += 1
                        continue
                        
                    # Check code content for virus signatures
                    for virus_sig in ['userSetup.py', 'leukocyte', 'phage', 'cmds.scriptJob(event=["SceneSaved"', 'fuckVirus', 'vaccine']:
                        if virus_sig in node_code:
                            self.log(f"Found virus code in node: {node}")
                            cmds.delete(node)
                            infections_found += 1
                            break
            except Exception as e:
                self.log(f"Error checking script node {node}: {e}")
        
        # Check for virus script jobs
        try:
            all_jobs = cmds.scriptJob(listJobs=True)
            
            for job in all_jobs:
                if any(sig in job for sig in ['leukocyte.antivirus()', 'phage', 'vaccine', 'fuckVirus']):
                    # Extract job number
                    job_num = int(job.split(':', 1)[0])
                    self.log(f"Removing infected script job: {job}")
                    cmds.scriptJob(kill=job_num, force=True)
                    infections_found += 1
        except Exception as e:
            self.log(f"Error checking script jobs: {e}")
        
        # Save file if infections were found
        if infections_found > 0:
            try:
                cmds.file(save=True, force=True)
                self.log(f"Saved cleaned file: {file_path}")
                self.cleanup_count += infections_found
            except Exception as e:
                self.log(f"Error saving file: {e}")
                return False
                
        self.files_processed += 1
        
        if infections_found > 0:
            self.log(f"Cleaned {infections_found} infections from {file_path}")
            return True
        else:
            self.log(f"No infections found in {file_path}")
            return False
    
    def clean_maya_directories(self):
        """Clean Maya user directories of virus files"""
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
            
            # Remove known virus files
            virus_files = [
                os.path.join(scripts_dir, 'userSetup.mel'),
                os.path.join(scripts_dir, 'vaccine.py'),
                os.path.join(scripts_dir, 'fuckVirus.py')
            ]
            
            for file_path in virus_files:
                if os.path.exists(file_path):
                    try:
                        # Make writable
                        self.make_writable(file_path)
                        
                        # Create backup
                        backup_path = f"{file_path}.backup"
                        shutil.copy2(file_path, backup_path)
                        
                        # Remove file
                        os.remove(file_path)
                        
                        self.log(f"Removed virus file: {file_path}")
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
        self.results["message"] = f"Processed {self.files_processed} files, cleaned {self.cleanup_count} infections"
        return self.results


def main():
    parser = argparse.ArgumentParser(description='Maya Virus Cleaner')
    parser.add_argument('--mode', choices=['scene', 'directory', 'user'], required=True,
                       help='Cleaning mode: single scene, directory, or user directories')
    parser.add_argument('--path', help='Path to Maya file or directory')
    parser.add_argument('--log', help='Path to write log file')
    parser.add_argument('--json', help='Path to write JSON results')
    
    args = parser.parse_args()
    
    # Initialize cleaner
    cleaner = MayaVirusCleaner(log_file=args.log)
    
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
        cleaner.log(f"Infections cleaned: {cleaner.cleanup_count}")
        
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