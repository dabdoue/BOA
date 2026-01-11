"""
BOA CLI - Command Line Interface for Bayesian Optimization Assistant.
"""

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from boa import __version__

app = typer.Typer(
    name="boa",
    help="BOA CLI - Bayesian Optimization Assistant",
    no_args_is_help=True,
)

console = Console()

# Subcommand groups
process_app = typer.Typer(help="Manage optimization processes")
campaign_app = typer.Typer(help="Manage optimization campaigns")

app.add_typer(process_app, name="process")
app.add_typer(campaign_app, name="campaign")


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"BOA version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """BOA CLI - Bayesian Optimization Assistant"""
    pass


# =============================================================================
# Server Commands
# =============================================================================

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    database: str = typer.Option(
        "sqlite:///boa.db",
        "--database",
        "-d",
        help="Database URL",
    ),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    """Start the BOA server."""
    import os
    import uvicorn
    
    os.environ["BOA_DATABASE_URL"] = database
    
    console.print(Panel.fit(
        f"[bold green]Starting BOA Server[/bold green]\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Database: {database}",
        title="BOA Server",
    ))
    
    uvicorn.run(
        "boa.server.app:app",
        host=host,
        port=port,
        reload=reload,
    )


# =============================================================================
# Process Commands
# =============================================================================

@process_app.command("create")
def process_create(
    spec_file: Path = typer.Argument(..., help="Path to process spec YAML file"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Create a new process from a spec file."""
    from boa.sdk.client import BOAClient
    
    if not spec_file.exists():
        console.print(f"[red]Error: File not found: {spec_file}[/red]")
        raise typer.Exit(1)
    
    with open(spec_file) as f:
        spec_yaml = f.read()
    
    client = BOAClient(base_url=server)
    
    try:
        process = client.create_process(spec_yaml)
        console.print(f"[green]Created process: {process['id']}[/green]")
        console.print(f"Name: {process['name']}")
        console.print(f"Version: {process['version']}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@process_app.command("list")
def process_list(
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
    active_only: bool = typer.Option(True, "--active/--all", help="Show only active processes"),
):
    """List all processes."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        processes = client.list_processes(is_active=active_only if active_only else None)
        
        if not processes:
            console.print("[yellow]No processes found[/yellow]")
            return
        
        table = Table(title="Processes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Version", style="magenta")
        table.add_column("Active", style="yellow")
        
        for p in processes:
            table.add_row(
                str(p["id"]),
                p["name"],
                str(p["version"]),
                "✓" if p.get("is_active") else "✗",
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@process_app.command("show")
def process_show(
    process_id: str = typer.Argument(..., help="Process ID"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Show details of a process."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        process = client.get_process(UUID(process_id))
        
        console.print(Panel.fit(
            f"[bold]Name:[/bold] {process['name']}\n"
            f"[bold]Version:[/bold] {process['version']}\n"
            f"[bold]Active:[/bold] {process.get('is_active', True)}\n"
            f"[bold]ID:[/bold] {process['id']}",
            title=f"Process: {process['name']}",
        ))
        
        console.print("\n[bold]Spec:[/bold]")
        console.print(process.get("spec_yaml", "N/A"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Campaign Commands
# =============================================================================

@campaign_app.command("create")
def campaign_create(
    process_id: str = typer.Argument(..., help="Process ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Campaign name"),
    metadata: Optional[str] = typer.Option(None, "--metadata", "-m", help="Campaign metadata (JSON)"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Create a new campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        meta = json.loads(metadata) if metadata else {}
        campaign = client.create_campaign(
            process_id=UUID(process_id),
            name=name or f"Campaign-{process_id[:8]}",
            metadata=meta,
        )
        
        console.print(f"[green]Created campaign: {campaign['id']}[/green]")
        console.print(f"Name: {campaign['name']}")
        console.print(f"Status: {campaign['status']}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@campaign_app.command("list")
def campaign_list(
    process_id: Optional[str] = typer.Option(None, "--process", "-p", help="Filter by process ID"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """List all campaigns."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        campaigns = client.list_campaigns(
            process_id=UUID(process_id) if process_id else None,
            status=status,
        )
        
        if not campaigns:
            console.print("[yellow]No campaigns found[/yellow]")
            return
        
        table = Table(title="Campaigns")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="magenta")
        table.add_column("Created", style="yellow")
        
        for c in campaigns:
            table.add_row(
                str(c["id"]),
                c["name"],
                c["status"],
                str(c.get("created_at", "N/A")),
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@campaign_app.command("status")
def campaign_status(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Show status of a campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        campaign = client.get_campaign(UUID(campaign_id))
        
        console.print(Panel.fit(
            f"[bold]Name:[/bold] {campaign['name']}\n"
            f"[bold]Status:[/bold] {campaign['status']}\n"
            f"[bold]Process:[/bold] {campaign['process_id']}\n"
            f"[bold]ID:[/bold] {campaign['id']}",
            title=f"Campaign: {campaign['name']}",
        ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@campaign_app.command("pause")
def campaign_pause(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Pause a campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        campaign = client.update_campaign(UUID(campaign_id), status="paused")
        console.print(f"[green]Campaign {campaign_id} paused[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@campaign_app.command("resume")
def campaign_resume(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Resume a paused campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        campaign = client.update_campaign(UUID(campaign_id), status="active")
        console.print(f"[green]Campaign {campaign_id} resumed[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@campaign_app.command("complete")
def campaign_complete(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Mark a campaign as completed."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        campaign = client.update_campaign(UUID(campaign_id), status="completed")
        console.print(f"[green]Campaign {campaign_id} completed[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Optimization Commands
# =============================================================================

@app.command()
def design(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    samples: int = typer.Option(10, "--samples", "-n", help="Number of initial samples"),
    method: str = typer.Option("lhs", "--method", "-m", help="Sampling method (lhs, sobol, random)"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Generate initial design points for a campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        result = client.generate_initial_design(
            campaign_id=UUID(campaign_id),
            n_samples=samples,
            method=method,
        )
        
        console.print(f"[green]Generated {len(result['samples'])} design points[/green]")
        
        # Display samples
        for i, sample in enumerate(result['samples']):
            console.print(f"  {i+1}: {sample}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def propose(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    candidates: int = typer.Option(1, "--candidates", "-n", help="Number of candidates to propose"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Get next proposal candidates for a campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        result = client.get_next_proposals(
            campaign_id=UUID(campaign_id),
            n_candidates=candidates,
        )
        
        console.print(f"[green]Proposed {len(result.get('proposals', []))} candidates[/green]")
        
        for i, proposal in enumerate(result.get('proposals', [])):
            console.print(f"  {i+1}: {proposal}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def observe(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    inputs: str = typer.Argument(..., help="Input values (JSON)"),
    outputs: str = typer.Argument(..., help="Output values (JSON)"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Record an observation for a campaign."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    try:
        input_data = json.loads(inputs)
        output_data = json.loads(outputs)
        
        obs = client.add_observation(
            campaign_id=UUID(campaign_id),
            inputs=input_data,
            outputs=output_data,
        )
        
        console.print(f"[green]Recorded observation: {obs['id']}[/green]")
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Export/Import Commands
# =============================================================================

@app.command("export")
def export_campaign(
    campaign_id: str = typer.Argument(..., help="Campaign ID to export"),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: campaign-<id>.json)",
    ),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Export a campaign to a JSON bundle file."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    if output is None:
        output = Path(f"campaign-{campaign_id[:8]}.json")
    
    try:
        bundle = client.export_campaign(UUID(campaign_id))
        
        with open(output, "w") as f:
            json.dump(bundle, f, indent=2, default=str)
        
        console.print(f"[green]Exported campaign to: {output}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("import")
def import_campaign(
    bundle_file: Path = typer.Argument(..., help="Path to bundle file"),
    server: str = typer.Option("http://localhost:8000", "--server", "-s", help="BOA server URL"),
):
    """Import a campaign from a JSON bundle file."""
    from boa.sdk.client import BOAClient
    
    client = BOAClient(base_url=server)
    
    if not bundle_file.exists():
        console.print(f"[red]Error: File not found: {bundle_file}[/red]")
        raise typer.Exit(1)
    
    try:
        with open(bundle_file) as f:
            bundle_data = json.load(f)
        
        result = client.import_campaign(bundle_data)
        
        console.print(f"[green]Imported campaign: {result['campaign_id']}[/green]")
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Entry point
# =============================================================================

def run():
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    run()
