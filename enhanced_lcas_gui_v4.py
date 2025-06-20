self.update_status("Processing stopped by user")
    
def _run_preservation(self):
        feat/ai-integration-fix
    """Run file preservation in background thread"""
    try: # Ensuring this line is exactly 4 spaces followed by try:

        feat/ai-integration-fix
    """Run file preservation in background thread"""
    try: # Ensuring this line is exactly 4 spaces followed by try:

        feat/ai-integration-fix
    """Run file preservation in background thread"""
    try: # Ensuring this line is exactly 4 spaces followed by try:

        feat/ai-integration-fix
    """Run file preservation in background thread"""
    try: # Ensuring this line is exactly 4 spaces followed by try:

      feat/ai-integration-fix
    """Run file preservation in background thread"""
    try:
        main
        main
        main
        main
        source_path = Path(self.source_var.get())
        target_path = Path(self.target_var.get())

        self.root.after(0, self.log_status, "🚀 Starting file preservation...")

        # Create target structure
        self.root.after(0, self.log_status, "📁 Creating folder structure...")
        self.create_folder_structure(target_path)

        # Discover files
        files = list(source_path.rglob("*"))
        files = [f for f in files if f.is_file()]

        self.root.after(0, self.log_status, f"📋 Found {len(files)} files to preserve...")

        # Preserve files
        preserved_count = 0
        for i, file_path in enumerate(files):
            if not self.is_processing:
                break
        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix


        """Run file preservation in background thread"""
        try:
            source_path = Path(self.source_var.get())
            target_path = Path(self.target_var.get())
            
            self.root.after(0, self.log_status, "🚀 Starting file preservation...")
            
            # Create target structure
            self.root.after(0, self.log_status, "📁 Creating folder structure...")
            self.create_folder_structure(target_path)
            
            # Discover files
            files = list(source_path.rglob("*"))
            files = [f for f in files if f.is_file()]
            
            self.root.after(0, self.log_status, f"📋 Found {len(files)} files to preserve...")
      main
        main
        main
        main
        main
            
            try:
                # Calculate relative path
                rel_path = file_path.relative_to(source_path)
                target_file = target_path / "00_PRESERVED_ORIGINALS" / rel_path
                
                # Create target directory
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(file_path, target_file)

                # Verify with hash
                source_hash = self.calculate_hash(file_path)
                target_hash = self.calculate_hash(target_file)

                if source_hash == target_hash:
                    preserved_count += 1
                    status = "✅"
                else:
                    status = "❌ Hash mismatch"

                # Update progress
                progress = (i + 1) / len(files)
                self.root.after(0, self.update_progress, progress, f"Preserving {i+1}/{len(files)}")
                self.root.after(0, self.log_status, f"{status} {rel_path}")

            except Exception as e:
                self.root.after(0, self.log_status, f"❌ Failed: {file_path.name} - {e}")

        # Complete
        self.root.after(0, self.preservation_complete, preserved_count, len(files))

    except Exception as e:
        self.root.after(0, self.preservation_error, str(e))
    
def _run_analysis(self):
        """Run complete analysis in background thread"""
        try:
            if LCAS_MAIN_AVAILABLE and self.config:
                self.root.after(0, self.log_analysis_status, "🚀 Starting complete LCAS v4.0 analysis...")
                
                # Update config with current GUI values
                self.config.source_directory = self.source_var.get()
                self.config.target_directory = self.target_var.get()
                
                # Create LCAS core and run analysis
                lcas = LCASCore(self.config)
                
                # Run complete analysis
                result = lcas.run_complete_analysis()
                
                self.root.after(0, self.analysis_complete, result)
            else:
                raise Exception("LCAS main system not available")
                
        except Exception as e:
            self.root.after(0, self.analysis_error, str(e))
    
    def _run_quick_analysis(self):
        """Run quick analysis simulation"""
        try:
            self.root.after(0, self.log_analysis_status, "⚡ Starting quick analysis...")
            
            # Simulate analysis of 50 files
            for i in range(1, 51):
                if not self.is_processing:
                    break
                
                time.sleep(0.1)  # Simulate processing time
                
                progress = i / 50
                self.root.after(0, self.update_analysis_progress, progress, f"Analyzing file {i}/50")
                self.root.after(0, self.log_analysis_status, f"✅ Analyzed: test_file_{i}.pdf")
                
                # Update stats
                self.root.after(0, self.update_analysis_stats, i, i // 2, i // 10)
            
            # Complete
            result = {
                "success": True,
                "analysis_count": 50,
                "cluster_count": 5,
                "message": "Quick analysis simulation complete"
            }
            self.root.after(0, self.analysis_complete, result)
            
        except Exception as e:
            self.root.after(0, self.analysis_error, str(e))
    
    # Helper methods
    def calculate_hash(self, file_path):
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except:
            return ""
    
    def create_folder_structure(self, target_path):
        """Create LCAS v4.0 folder structure"""
        folders = [
            "00_AUDIT_TRAIL",
            "00_PRESERVED_ORIGINALS",
            "01_CASE_SUMMARIES_AND_RELATED_DOCS",
            "02_CONSTITUTIONAL_VIOLATIONS",
            "03_ELECTRONIC_ABUSE",
            "04_FRAUD_ON_THE_COURT",
            "05_NON_DISCLOSURE_FC2107_FC2122",
            "06_PD065288_COURT_RECORD_DOCS",
            "07_POST_TRIAL_ABUSE",
            "08_TEXT_MESSAGES",
            "09_FOR_HUMAN_REVIEW",
            "10_VISUALIZATIONS_AND_REPORTS"
        ]
        
        for folder in folders:
            folder_path = target_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
    
    def set_processing_state(self, processing):
        """Update GUI state for processing"""
        self.is_processing = processing
        
        if processing:
            self.preserve_button.configure(state="disabled")
            self.analyze_button.configure(state="disabled")
            self.quick_analyze_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        else:
            self.preserve_button.configure(state="normal")
            self.analyze_button.configure(state="normal")
            self.quick_analyze_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
    
    def update_progress(self, progress, text):
        """Update progress bar and label"""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=text)
    
    def update_analysis_progress(self, progress, text):
        """Update analysis progress"""
        self.analysis_progress_bar.set(progress)
        self.analysis_progress_label.configure(text=text)
    
    def update_analysis_stats(self, files_analyzed, ai_analyzed, clusters):
        """Update analysis statistics"""
        self.files_analyzed_label.configure(text=f"📁 Files Analyzed: {files_analyzed}")
        self.ai_analyzed_label.configure(text=f"🤖 AI Enhanced: {ai_analyzed}")
        self.clusters_label.configure(text=f"🔗 Clusters: {clusters}")
    
    def log_status(self, message):
        """Log message to preservation status feed"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.status_feed.insert("end", log_message)
        self.status_feed.see("end")
    
    def log_analysis_status(self, message):
        """Log message to analysis status feed"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.analysis_status_feed.insert("end", log_message)
        self.analysis_status_feed.see("end")
    
    def preservation_complete(self, preserved_count, total_count):
        """Handle preservation completion"""
        self.set_processing_state(False)
        
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="File preservation completed!")
        
        self.results_label.configure(
            text=f"✅ Successfully preserved {preserved_count}/{total_count} files",
            text_color="green"
        )
        
        messagebox.showinfo(
            "Preservation Complete",
            f"File preservation completed!\n\n"
            f"Files preserved: {preserved_count}/{total_count}\n"
            f"Results saved to: {self.target_var.get()}"
        )
    
    def preservation_error(self, error_message):
        """Handle preservation error"""
        self.set_processing_state(False)
        
        self.progress_label.configure(text="File preservation failed!")
        self.results_label.configure(
            text=f"❌ Preservation failed: {error_message}",
            text_color="red"
        )
        
        messagebox.showerror("Preservation Error", f"Preservation failed:\n\n{error_message}")
    
    def analysis_complete(self, result):
        """Handle analysis completion"""
        self.set_processing_state(False)
        
        self.analysis_progress_bar.set(1.0)
        self.analysis_progress_label.configure(text="Analysis completed successfully!")
        
        if result.get("success"):
            summary_text = f"""LCAS v4.0 Analysis Complete!

📊 Summary:
• Files Analyzed: {result.get('analysis_count', 0)}
• Clusters Created: {result.get('cluster_count', 0)}
• Processing Status: {result.get('message', 'Success')}

🎉 Analysis completed successfully!
Check the Results & Reports tab for detailed findings.
"""
            
            self.results_summary.delete("1.0", "end")
            self.results_summary.insert("1.0", summary_text)
            
            messagebox.showinfo(
                "Analysis Complete",
                f"LCAS v4.0 analysis completed successfully!\n\n"
                f"Files analyzed: {result.get('analysis_count', 0)}\n"
                f"Clusters created: {result.get('cluster_count', 0)}\n\n"
                f"Check the Results & Reports tab for detailed findings."
            )
        else:
            messagebox.showerror("Analysis Error", f"Analysis failed: {result.get('error', 'Unknown error')}")
    
    def analysis_error(self, error_message):
        """Handle analysis error"""
        self.set_processing_state(False)
        
        self.analysis_progress_label.configure(text="Analysis failed!")
        messagebox.showerror("Analysis Error", f"Analysis failed:\n\n{error_message}")
    
    # Results methods
    def view_detailed_results(self):
        """View detailed results"""
        results_file = Path(self.target_var.get()) / "10_VISUALIZATIONS_AND_REPORTS"
        
        if results_file.exists():
            try:
                import subprocess
                import sys
                
                if sys.platform == "win32":
                    subprocess.run(["explorer", str(results_file)])
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(results_file)])
                else:
                    subprocess.run(["xdg-open", str(results_file)])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open results folder: {e}")
        else:
            messagebox.showinfo("No Results", "No analysis results found. Run analysis first.")
    
    def open_reports_folder(self):
        """Open reports folder"""
        self.view_detailed_results()
    
    def export_summary(self):
        """Export analysis summary"""
        try:
            export_file = filedialog.asksaveasfilename(
                title="Export Analysis Summary",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Markdown files", "*.md"),
                    ("All files", "*.*")
                ]
            )
            
            if export_file:
                summary_content = self.results_summary.get("1.0", "end")
                with open(export_file, "w", encoding="utf-8") as f:
                    f.write(summary_content)
                
                messagebox.showinfo("Export Complete", f"Summary exported to:\n{export_file}")
                
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export summary: {e}")
    
    def update_status(self, message):
        """Update status bar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_label.configure(text=f"[{timestamp}] {message}")
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

# Main execution
def main():
    """Main application entry point"""
    try:
        print("🚀 LCAS v4.0 - Enhanced Legal Case Analysis System")
        print("=" * 60)
        
        # Create and run GUI
        app = LCAS_v4_GUI()
        app.run()
        
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
