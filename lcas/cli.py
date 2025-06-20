#!/usr/bin/env python3
"""
LCAS Command Line Interface
Interactive CLI for the Legal Case Analysis System
"""

import asyncio
import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from .core import LCASCore, LCASConfig

console = Console()


@click.group()
@click.version_option(version="4.0.0")
def cli():
    """LCAS - Legal Case Analysis System v4.0"""
    pass


@cli.command()
@click.option('--config', default='lcas_config.json',
              help='Configuration file path')
@click.option('--source', help='Source directory path')
@click.option('--target', help='Target directory path')
@click.option('--case-name', help='Case name')
def analyze(config, source, target, case_name):
    """Run complete analysis on evidence files"""
    console.print("[bold blue]LCAS Analysis Starting...[/bold blue]")

    # Load or create configuration
    if Path(config).exists():
        core = LCASCore.load_config(config)
    else:
        core = LCASCore(LCASConfig())

    # Override with command line options
    if source:
        core.config.source_directory = source
    if target:
        core.config.target_directory = target
    if case_name:
        core.config.case_name = case_name

    # Validate configuration
    if not core.config.source_directory:
        core.config.source_directory = Prompt.ask(
            "Enter source directory path")

    if not core.config.target_directory:
        core.config.target_directory = Prompt.ask(
            "Enter target directory path")

    if not core.config.case_name:
        core.config.case_name = Prompt.ask("Enter case name")

    # Run analysis
    asyncio.run(run_analysis_cli(core))


async def run_analysis_cli(core: LCASCore):
    """Run analysis with CLI progress display"""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Initialize core
            init_task = progress.add_task(
                "Initializing LCAS Core...", total=None)
            if not await core.initialize():
                console.print("[red]Failed to initialize LCAS Core[/red]")
                return
            progress.update(init_task, completed=True)

            # Load plugins
            plugins_task = progress.add_task("Loading plugins...", total=None)
            analysis_plugins = core.get_analysis_plugins()
            progress.update(plugins_task, completed=True)

            if not analysis_plugins:
                console.print("[yellow]No analysis plugins loaded[/yellow]")
                return

            console.print(f"[green]Loaded {len(analysis_plugins)} analysis plugins[/green]")

            # Run analysis plugins
            for plugin in analysis_plugins:
                plugin_task = progress.add_task(
                    f"Running {plugin.name}...", total=None)

                try:
                    result = await plugin.analyze({
                        "source_directory": core.config.source_directory,
                        "target_directory": core.config.target_directory,
                        "case_name": core.config.case_name
                    })

                    core.set_analysis_result(plugin.name, result)
                    progress.update(plugin_task, completed=True)
                    console.print(f"[green]✓ {plugin.name} completed[/green]")

                except Exception as e:
                    progress.update(plugin_task, completed=True)
                    console.print(f"[red]✗ {plugin.name} failed: {e}[/red]")

            # Shutdown
            shutdown_task = progress.add_task("Shutting down...", total=None)
            await core.shutdown()
            progress.update(shutdown_task, completed=True)

        console.print(
            "[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {core.config.target_directory}")

    except Exception as e:
        console.print(f"[red]Analysis failed: {e}[/red]")


@cli.command()
@click.option('--config', default='lcas_config.json',
              help='Configuration file path')
def status(config):
    """Show system status and configuration"""
    console.print("[bold blue]LCAS System Status[/bold blue]")

    # Load configuration
    if Path(config).exists():
        core = LCASCore.load_config(config)
        console.print(f"[green]✓ Configuration loaded from {config}[/green]")
    else:
        console.print(
            f"[yellow]⚠ No configuration file found at {config}[/yellow]")
        core = LCASCore(LCASConfig())

    # Display configuration
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Case Name", core.config.case_name or "Not set")
    table.add_row(
        "Source Directory",
        core.config.source_directory or "Not set")
    table.add_row(
        "Target Directory",
        core.config.target_directory or "Not set")
    table.add_row("Plugins Directory", core.config.plugins_directory)
    table.add_row("Debug Mode", str(core.config.debug_mode))
    table.add_row("Log Level", core.config.log_level)

    console.print(table)

    # Check directories
    console.print("\n[bold blue]Directory Status[/bold blue]")
    if core.config.source_directory:
        if Path(core.config.source_directory).exists():
            console.print(f"[green]✓ Source directory exists[/green]")
        else:
            console.print(f"[red]✗ Source directory not found[/red]")

    if core.config.target_directory:
        target_path = Path(core.config.target_directory)
        if target_path.exists():
            console.print(f"[green]✓ Target directory exists[/green]")
        else:
            console.print(
                f"[yellow]⚠ Target directory will be created[/yellow]")


@cli.command()
@click.option('--config', default='lcas_config.json',
              help='Configuration file path')
def plugins(config):
    """List available and loaded plugins"""
    console.print("[bold blue]LCAS Plugin Status[/bold blue]")

    # Load core to access plugin manager
    core = LCASCore.load_config(config) if Path(
        config).exists() else LCASCore(LCASConfig())

    # Discover plugins
    available_plugins = core.plugin_manager.discover_plugins()

    if not available_plugins:
        console.print("[yellow]No plugins found in plugins directory[/yellow]")
        return

    # Create plugins table
    table = Table(title="Available Plugins")
    table.add_column("Plugin Name", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Enabled", style="green")

    for plugin_name in available_plugins:
        status = "Available"
        enabled = "Yes" if plugin_name in core.config.enabled_plugins else "No"
        table.add_row(plugin_name, status, enabled)

    console.print(table)


@cli.command()
def config():
    """Interactive configuration setup"""
    console.print("[bold blue]LCAS Configuration Setup[/bold blue]")

    # Get configuration values
    case_name = Prompt.ask("Case name")
    source_dir = Prompt.ask("Source directory (where your evidence files are)")
    target_dir = Prompt.ask("Target directory (where results will be saved)")

    # Validate directories
    if not Path(source_dir).exists():
        if not Confirm.ask(
                f"Source directory '{source_dir}' does not exist. Continue anyway?"):
            return

    # Create configuration
    config_data = LCASConfig(
        case_name=case_name,
        source_directory=source_dir,
        target_directory=target_dir
    )

    # Save configuration
    config_file = "lcas_config.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(config_data.__dict__, f, indent=2)
        console.print(f"[green]✓ Configuration saved to {config_file}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to save configuration: {e}[/red]")


@cli.command()
@click.argument('source_dir')
@click.argument('target_dir')
@click.option('--case-name', help='Case name')
def quick(source_dir, target_dir, case_name):
    """Quick analysis with minimal setup"""
    console.print("[bold blue]LCAS Quick Analysis[/bold blue]")

    # Validate directories
    if not Path(source_dir).exists():
        console.print(
            f"[red]✗ Source directory '{source_dir}' does not exist[/red]")
        return

    # Create configuration
    config = LCASConfig(
        case_name=case_name or "Quick Analysis",
        source_directory=source_dir,
        target_directory=target_dir
    )

    core = LCASCore(config)

    # Run analysis
    asyncio.run(run_analysis_cli(core))


def main():
    """Main CLI entry point"""
    cli()


if __name__ == "__main__":
    main()
