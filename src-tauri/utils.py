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


import maya.standalone
maya.standalone.initialize(name='python')


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

        self.backup_dir = self.create_backup_directory()
        
    def create_backup_directory(self):
        

        temp_dir = os.path.join(tempfile.gettempdir(), "maya_cleaner_backups")
        os.makedirs(temp_dir, exist_ok=True)
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        today_dir = os.path.join(temp_dir, today)
        os.makedirs(today_dir, exist_ok=True)

        return today_dir
        
    def log(self, message):
        
        print(message)
        self.results["details"].append(message)
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
                
    def make_writable(self, file_path):
        
        if os.path.exists(file_path):
            try:
                os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
                return True
            except Exception as e:
                self.log(f"WARNING: Could not change permissions for {file_path}: {e}")
                return False
        return False
    
    def clean_usersetup_file(self, file_path):
        
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}")
            return False
            

        self.make_writable(file_path)
        file_name = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            self.log(f"Failed to create backup of {file_path}: {e}")
            return False
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            problem_detected = False
            for problem_sig in ['import fuckVirus', 'import vaccine', 'leukocyte', 'phage']:
                if problem_sig in content:
                    problem_detected = True
                    break
                    
            if not problem_detected:
                self.log(f"No issues detected in {file_path}")
                return False
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
            if len(problem_lines) > len(clean_lines):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# This file was cleaned of problematic code\n# Original backup saved in temp directory\n")
                self.log(f"Replaced problematic userSetup.py: {file_path}")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(clean_lines))
                self.log(f"Selectively cleaned userSetup.py: {file_path}")
                
            self.cleanup_count += 1
            return True
                
        except Exception as e:
            self.log(f"Error cleaning {file_path}: {e}")
            return False
    
    def clean_maya_scene(self, file_path=None):
        
        if not file_path:
            file_path = cmds.file(q=True, sceneName=True)
            if not file_path:
                self.log("No file specified and no current scene")
                return False
        if not os.path.exists(file_path):
            self.log(f"File does not exist: {file_path}")
            return False
            
        self.log(f"Processing Maya file: {file_path}")
        self.make_writable(file_path)
        file_name = os.path.basename(file_path)
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            self.log(f"Failed to create backup of {file_path}: {e}")
        try:
            current_scene = cmds.file(q=True, sceneName=True)
            if current_scene:
                cmds.file(save=True, force=True)
            cmds.file(new=True, force=True)
            cmds.file(file_path, open=True, force=True)
        except Exception as e:
            self.log(f"Failed to open file {file_path}: {e}")
            return False
        issues_found = 0
        problem_node_names = ["vaccine_gene", "breed_gene", "fuckVirus_gene"]
        all_script_nodes = cmds.ls(type='script') or []
        
        for node in all_script_nodes:
            try:
                if cmds.objExists(node) and cmds.attributeQuery('before', node=node, exists=True):
                    node_code = cmds.getAttr(node + '.before') or ""
                    if any(name in node for name in problem_node_names):
                        self.log(f"Found problematic node by name: {node}")
                        cmds.delete(node)
                        issues_found += 1
                        continue
                    for sig in ['userSetup.py', 'leukocyte', 'phage', 'cmds.scriptJob(event=["SceneSaved"', 'fuckVirus', 'vaccine']:
                        if sig in node_code:
                            self.log(f"Found problematic code in node: {node}")
                            cmds.delete(node)
                            issues_found += 1
                            break
            except Exception as e:
                self.log(f"Error checking script node {node}: {e}")
        try:
            all_jobs = cmds.scriptJob(listJobs=True)
            
            for job in all_jobs:
                if any(sig in job for sig in ['leukocyte.antivirus()', 'phage', 'vaccine', 'fuckVirus']):
                    job_num = int(job.split(':', 1)[0])
                    self.log(f"Removing problematic script job: {job}")
                    cmds.scriptJob(kill=job_num, force=True)
                    issues_found += 1
        except Exception as e:
            self.log(f"Error checking script jobs: {e}")
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
        
        maya_user_dirs = []
        documents = os.path.expanduser("~/Documents")
        app_data = os.path.expanduser("~/AppData/Roaming")
        maya_docs = os.path.join(documents, "maya")
        if os.path.exists(maya_docs):
            for version_dir in os.listdir(maya_docs):
                scripts_dir = os.path.join(maya_docs, version_dir, "scripts")
                if os.path.exists(scripts_dir):
                    maya_user_dirs.append(scripts_dir)
        maya_app = os.path.join(app_data, "Autodesk", "maya")
        if os.path.exists(maya_app):
            for version_dir in os.listdir(maya_app):
                scripts_dir = os.path.join(maya_app, version_dir, "scripts")
                if os.path.exists(scripts_dir):
                    maya_user_dirs.append(scripts_dir)
        try:
            maya_script_dir = cmds.internalVar(userScriptDir=True)
            if maya_script_dir and os.path.exists(maya_script_dir):
                maya_user_dirs.append(maya_script_dir)
        except:
            pass
        maya_user_dirs = list(set(maya_user_dirs))
        
        self.log(f"Found {len(maya_user_dirs)} Maya user directories")
        for scripts_dir in maya_user_dirs:
            self.log(f"Checking directory: {scripts_dir}")
            usersetup_py = os.path.join(scripts_dir, 'userSetup.py')
            if os.path.exists(usersetup_py):
                self.clean_usersetup_file(usersetup_py)
            problem_files = [
                os.path.join(scripts_dir, 'userSetup.mel'),
                os.path.join(scripts_dir, 'vaccine.py'),
                os.path.join(scripts_dir, 'fuckVirus.py')
            ]
            
            for file_path in problem_files:
                if os.path.exists(file_path):
                    try:
                        self.make_writable(file_path)
                        file_name = os.path.basename(file_path)
                        timestamp = datetime.datetime.now().strftime("%H%M%S")
                        backup_path = os.path.join(self.backup_dir, f"{file_name}_{timestamp}.backup")
                        shutil.copy2(file_path, backup_path)
                        os.remove(file_path)
                        
                        self.log(f"Removed problematic file: {file_path}")
                        self.cleanup_count += 1
                    except Exception as e:
                        self.log(f"Failed to remove {file_path}: {e}")
    
    def batch_clean_directory(self, directory_path):
        
        if not os.path.exists(directory_path):
            self.log(f"Directory does not exist: {directory_path}")
            return False
            
        self.log(f"Scanning directory: {directory_path}")
        maya_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(('.ma', '.mb')):
                    maya_files.append(os.path.join(root, file))
        
        self.log(f"Found {len(maya_files)} Maya files to process")
        for file_path in maya_files:
            try:
                self.clean_maya_scene(file_path)
            except Exception as e:
                self.log(f"Error processing {file_path}: {e}")
                
        return True
    
    def get_results(self):
        
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
    cleaner = MayaFileCleaner(log_file=args.log)
    
    try:
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
        if args.json:
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(cleaner.get_results(), f, indent=2)
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
        try:
            maya.standalone.uninitialize()
        except:
            pass


if __name__ == "__main__":
    main()