#!/usr/bin/env python3
"""
LCAS Runner Script - Easy interface to run the Legal Case Analysis System
"""

import os
import sys
import json
from pathlib import Path

def print_banner():
    """Print the LCAS banner"""
    print("="*70)
    print("  LEGAL CASE-BUILDING AND ANALYSIS SYSTEM (LCAS)")
    print("  Organize, Analyze, and Score Legal Evidence")
    print("="*70)
    print()

def check_requirements():
    """Check if required directories exist and are accessible"""
    print("🔍 Checking system requirements...")
    
    # Default paths
    source_dir = r"F:\POST TRIAL DIVORCE"
    target_dir = r"G:\LCAS_ANALYSIS_RESULTS"
    
    # Check source directory
    if not Path(source_dir).exists():
        print(f"❌ Source directory not found: {source_dir}")
        print("   Please update the source path in the configuration.")
        return False, source_dir, target_dir
    
    # Check if target directory parent exists
    target_parent = Path(target_dir).parent
    if not target_parent.exists():
        print(f"❌ Target parent directory not accessible: {target_parent}")
        print("   Please ensure the G: drive is accessible.")
        return False, source_dir, target_dir
    
    print(f"✅ Source directory found: {source_dir}")
    print(f"✅ Target location accessible: {target_dir}")
    return True, source_dir, target_dir

def check_optional_libraries():
    """Check which optional libraries are available"""
    print("\n📚 Checking optional libraries for enhanced functionality...")
    
    libraries = {
        'PyPDF2': 'PDF extraction',
        'pdfplumber': 'Advanced PDF extraction', 
        'docx': 'Word document extraction',
        'openpyxl': 'Excel file extraction',
        'pandas': 'Data analysis and CSV/Excel processing',
        'spacy': 'Advanced natural language processing',
        'sentence_transformers': 'Text embeddings for similarity analysis',
        'neo4j': 'Knowledge graph database'
    }
    
    available = []
    missing = []
    
    for lib, description in libraries.items():
        try:
            __import__(lib)
            available.append((lib, description))
            print(f"✅ {lib} - {description}")
        except ImportError:
            missing.append((lib, description))
            print(f"❌ {lib} - {description}")
    
    if missing:
        print(f"\n💡 Optional libraries missing: {len(missing)}")
        print("   Install with: pip install [library_name]")
        print("   The system will run with basic functionality.")
    
    return len(available), len(missing)

def create_config_file(source_dir: str, target_dir: str):
    """Create or update configuration file"""
    config_file = "lcas_config.json"
    
    config = {
        "source_directory": source_dir,
        "target_directory": target_dir,
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j", 
        "neo4j_password": "password",
        "min_probative_score": 0.3,
        "min_relevance_score": 0.5,
        "similarity_threshold": 0.85,
        "probative_weight": 0.4,
        "relevance_weight": 0.3,
        "admissibility_weight": 0.3
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📝 Configuration saved to: {config_file}")
    return config_file

def estimate_processing_time(source_dir: str):
    """Estimate processing time based on file count"""
    try:
        file_count = 0
        supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.rtf', '.xlsx', '.xls', '.csv', '.eml', '.msg'}
        
        for file_path in Path(source_dir).rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                file_count += 1
        
        # Rough estimate: 2-5 seconds per file depending on size and type
        estimated_minutes = (file_count * 3) / 60
        
        print(f"\n📊 Analysis Estimate:")
        print(f"   Files to process: {file_count}")
        print(f"   Estimated time: {estimated_minutes:.1f} minutes")
        
        return file_count
    
    except Exception as e:
        print(f"❌ Error estimating processing time: {e}")
        return 0

def run_analysis(config_file: str):
    """Run the LCAS analysis"""
    print(f"\n🚀 Starting LCAS analysis...")
    print("   This may take several minutes depending on file count and size.")
    print("   Progress will be logged to 'lcas.log'")
    print("\n" + "="*50)
    
    try:
        # Import and run LCAS
        from lcas_main import LCASCore, load_config
        
        # Load configuration
        config = load_config(config_file)
        
        # Initialize and run LCAS
        lcas = LCASCore(config)
        
        # Register content extraction plugin if available
        try:
            from content_extraction_plugin import ContentExtractionPlugin
            lcas.register_plugin('content_extraction', ContentExtractionPlugin(config))
        except ImportError:
            print("   Content extraction plugin not found - running with basic extraction")
        
        # Run complete analysis
        lcas.run_complete_analysis()
        lcas.save_analysis_results()
        
        print("\n" + "="*60)
        print("✅ LCAS ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"📁 Results location: {config.target_directory}")
        print("\n📊 Generated Reports:")
        print(f"   • Analysis Summary: 10_VISUALIZATIONS_AND_REPORTS/analysis_summary.md")
        print(f"   • Argument Strength: 10_VISUALIZATIONS_AND_REPORTS/argument_strength_analysis.md")
        print(f"   • Duplicate Files: 10_VISUALIZATIONS_AND_REPORTS/duplicate_files_report.md")
        print(f"   • Detailed Data: analysis_results.json")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Analysis failed with error: {e}")
        print("📋 Check lcas.log for detailed error information")
        return False

def show_menu():
    """Display the main menu"""
    print("\n" + "="*50)
    print("LCAS MAIN MENU")
    print("="*50)
    print("1. Run Full Analysis")
    print("2. Check System Requirements")
    print("3. Install Dependencies Guide")
    print("4. Create/Update Configuration")
    print("5. View Configuration")
    print("6. Exit")
    print("="*50)

def show_installation_guide():
    """Show installation guide for dependencies"""
    print("\n📦 INSTALLATION GUIDE")
    print("="*40)
    print("Core dependencies (recommended for full functionality):")
    print("\n📄 For PDF processing:")
    print("   pip install PyPDF2 pdfplumber")
    print("\n📝 For Word documents:")
    print("   pip install python-docx")
    print("\n📊 For Excel/CSV files:")
    print("   pip install pandas openpyxl")
    print("\n📧 For email files:")
    print("   pip install extract-msg")
    print("\n🧠 For advanced NLP (optional):")
    print("   pip install spacy sentence-transformers")
    print("   python -m spacy download en_core_web_sm")
    print("\n🗃️ For knowledge graphs (optional):")
    print("   pip install neo4j py2neo")
    print("\n📈 For visualizations:")
    print("   pip install matplotlib seaborn plotly")
    print("\n💡 Install all at once:")
    print("   pip install PyPDF2 pdfplumber python-docx pandas openpyxl matplotlib seaborn")

def view_configuration():
    """View current configuration"""
    config_file = "lcas_config.json"
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("\n📋 CURRENT CONFIGURATION")
        print("="*40)
        for key, value in config.items():
            print(f"{key}: {value}")
    else:
        print("\n No configuration file found. Create one using option 4.")

def main():
    """Main application entry point"""
    print_banner()
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            # Run Full Analysis
            requirements_ok, source_dir, target_dir = check_requirements()
            if not requirements_ok:
                print("\n Please fix the directory issues before running analysis.")
                continue
            
            check_optional_libraries()
            
            # Estimate processing time
            file_count = estimate_processing_time(source_dir)
            if file_count == 0:
                print("No supported files found in source directory.")
                continue
            
            # Confirm before proceeding
            confirm = input(f"\nProceed with analysis of {file_count} files? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Analysis cancelled.")
                continue
            
            # Create/update config
        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

      feat/ai-integration-fix
        main
        main
        main
        main
        main
        main
        main
            # Corrected: use source_dir, target_dir from check_requirements()
            config_file = create_config_file(source_dir, target_dir)
            # Run analysis (this was missing from the original choice '1' block after merge)
            success = run_analysis(config_file)
            if success:
                print(f"\n Analysis complete! Check {target_dir} for results.")
            else:
        feat/ai-integration-fix
                print("\n😞 Analysis failed. Check the log file for details.")

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

                print("\n Analysis failed. Check the log file for details.")
        main

        main
        main
        main
        main
        main
        main
        elif choice == '2':
            # Check System Requirements
            requirements_ok, source_dir, target_dir = check_requirements()
            check_optional_libraries()
        
        elif choice == '3':
            # Installation Guide
            show_installation_guide()
        
        elif choice == '4':
            # Create/Update Configuration
            print("\n CONFIGURATION SETUP")
            print("="*30)
            
            # Use different variable names for this input to avoid conflict if source_dir/target_dir are needed later
            cfg_source_dir = input("Enter source directory path (or press Enter for default): ").strip()
            if not cfg_source_dir:
                cfg_source_dir = r"F:\POST TRIAL DIVORCE" # Default
            
            cfg_target_dir = input("Enter target directory path (or press Enter for default): ").strip()
            if not cfg_target_dir:
                cfg_target_dir = r"G:\LCAS_ANALYSIS_RESULTS" # Default
            
            config_file = create_config_file(cfg_source_dir, cfg_target_dir)
        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix
        main
        main
        main
        main
        main
            print(f"✅ Configuration created/updated: {config_file}")

        elif choice == '5': # Ensuring 8-space indent
            # View Configuration
            view_configuration() # Ensuring 12-space indent

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix

        feat/ai-integration-fix


        feat/ai-integration-fix
            print(f"✅ Configuration created/updated: {config_file}")

            print(f" Configuration created/updated: {config_file}")
        main

        elif choice == '5':
            # View Configuration
            view_configuration()

        feat/ai-integration-fix
        main
        main
        main
        main
        main
        main
        elif choice == '6':
            # Exit
            print("\n👋 Thank you for using LCAS!")
            print("Visit us at: https://github.com/your-repo/lcas")
            break

        else:
            print("\n❌ Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
        feat/ai-integration-fix
    main()

        feat/ai-integration-fix
    main()

        feat/ai-integration-fix
    main()

        feat/ai-integration-fix
    main()

        feat/ai-integration-fix
    main()

        feat/ai-integration-fix
    main()
    
    main()


            config_file = create_config_file(source, target)
            print(f" Configuration updated successfully!")
        
        elif choice == '5':
            # View Configuration
            view_configuration()
        
       main
        elif choice == '6':
            # Exit
            print("\n Thank you for using LCAS!")
            print("Visit us at: https://github.com/your-repo/lcas")
            break
       feat/ai-integration-fix
        
       main
        else:
            print("\n Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
       feat/ai-integration-fix
    main()
    
    main()

# The following elif blocks are structurally incorrect as they are outside the main() function's loop.
# However, to address the specific subtask of fixing line 270's "unexpected indent"
# in its current broken context, we would unindent these blocks to be top-level.
# This is a partial fix; the correct fix involves moving these into main().
# For this operation, we will assume these blocks should start at column 0.

elif choice == '2':
    # Check System Requirements
    requirements_ok, source_dir, target_dir = check_requirements()
    check_optional_libraries()

elif choice == '3':
    # Installation Guide
    show_installation_guide()

elif choice == '4':
    # Create/Update Configuration
    print("\n CONFIGURATION SETUP")
    print("="*30)

    source = input("Enter source directory path (or press Enter for default): ").strip()
    if not source:
        source = r"F:\POST TRIAL DIVORCE"

    target = input("Enter target directory path (or press Enter for default): ").strip()
    if not target:
        target = r"G:\LCAS_ANALYSIS_RESULTS"

    config_file = create_config_file(source, target) # Corrected line 270 and added arguments
       main
        main
        main
        main
        main
        main
        main
        main