#!/usr/bin/env python3
"""
LCAS Main Entry Point
Command-line interface for the Legal Case Analysis System
"""

import asyncio
import argparse
import sys
from pathlib import Path

from .core import LCASCore, LCASConfig
from .gui import LCASMainGUI


def main():
    """Main entry point for LCAS"""
    parser = argparse.ArgumentParser(
        description="LCAS - Legal Case Analysis System")
    parser.add_argument(
        "--config",
        default="config/lcas_config.json", # Relative to project root LCAS_2/
        help="Configuration file path")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch GUI interface")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode")
    parser.add_argument(
        "--plugins-dir",
        default="lcas2/plugins", # Relative to project root LCAS_2/
        help="Plugins directory")
    parser.add_argument("--source", help="Source directory path")
    parser.add_argument("--target", help="Target directory path")

    args = parser.parse_args()

    if args.gui:
        # Launch GUI
        try:
            app = LCASMainGUI()
            app.run()
        except Exception as e:
            print(f"Failed to start GUI: {e}")
            sys.exit(1)
    else:
        # Run CLI version
        asyncio.run(run_cli(args))


async def run_cli(args):
    """Run CLI version of LCAS"""
    # Load configuration
    core = LCASCore.load_config(args.config)

    if args.debug:
        core.config.debug_mode = True
        core.config.log_level = "DEBUG"

    if args.plugins_dir:
        core.config.plugins_directory = args.plugins_dir

    if args.source:
        core.config.source_directory = args.source

    if args.target:
        core.config.target_directory = args.target

    # Initialize and run
    if await core.initialize():
        print("LCAS Core Application started successfully")
        print(f"Loaded plugins: {list(core.plugin_manager.loaded_plugins.keys())}")

        # Run analysis if directories are configured
        if core.config.source_directory and core.config.target_directory:
            print("Running analysis...")
            await run_analysis(core)
        else:
            print(
                "No source/target directories configured. Use --source and --target options.")

        await core.shutdown()
    else:
        print("Failed to start LCAS Core Application")
        sys.exit(1)


async def run_analysis(core: LCASCore):
    """Run analysis using loaded plugins"""
    try:
        analysis_plugins = core.get_analysis_plugins()

        if not analysis_plugins:
            print("No analysis plugins loaded")
            return

        print(f"Running {len(analysis_plugins)} analysis plugins...")

        for plugin in analysis_plugins:
            print(f"Running {plugin.name}...")
            try:
                result = await plugin.analyze({
                    "source_directory": core.config.source_directory,
                    "target_directory": core.config.target_directory,
                    "case_name": core.config.case_name
                })

                core.set_analysis_result(plugin.name, result)
                print(f"✓ {plugin.name} completed")

            except Exception as e:
                print(f"✗ {plugin.name} failed: {e}")

        print("Analysis complete!")

    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
