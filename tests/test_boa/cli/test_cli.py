"""
Tests for BOA CLI.
"""

import pytest
from typer.testing import CliRunner

from boa.cli.main import app


runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""
    
    def test_version(self):
        """Test version command."""
        result = runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "BOA version" in result.stdout
    
    def test_help(self):
        """Test help command."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "BOA CLI" in result.stdout
        assert "serve" in result.stdout
        assert "process" in result.stdout
        assert "campaign" in result.stdout
    
    def test_serve_help(self):
        """Test serve command help."""
        result = runner.invoke(app, ["serve", "--help"])
        
        assert result.exit_code == 0
        assert "--host" in result.stdout
        assert "--port" in result.stdout
        assert "--database" in result.stdout
    
    def test_process_help(self):
        """Test process command help."""
        result = runner.invoke(app, ["process", "--help"])
        
        assert result.exit_code == 0
        assert "create" in result.stdout
        assert "list" in result.stdout
        assert "show" in result.stdout
    
    def test_campaign_help(self):
        """Test campaign command help."""
        result = runner.invoke(app, ["campaign", "--help"])
        
        assert result.exit_code == 0
        assert "create" in result.stdout
        assert "list" in result.stdout
        assert "status" in result.stdout
        assert "pause" in result.stdout
        assert "resume" in result.stdout
        assert "complete" in result.stdout
    
    def test_design_help(self):
        """Test design command help."""
        result = runner.invoke(app, ["design", "--help"])
        
        assert result.exit_code == 0
        assert "campaign_id" in result.stdout.lower()
        assert "--samples" in result.stdout
    
    def test_propose_help(self):
        """Test propose command help."""
        result = runner.invoke(app, ["propose", "--help"])
        
        assert result.exit_code == 0
        assert "campaign_id" in result.stdout.lower()
        assert "--candidates" in result.stdout
    
    def test_observe_help(self):
        """Test observe command help."""
        result = runner.invoke(app, ["observe", "--help"])
        
        assert result.exit_code == 0
        assert "campaign_id" in result.stdout.lower()
    
    def test_export_help(self):
        """Test export command help."""
        result = runner.invoke(app, ["export", "--help"])
        
        assert result.exit_code == 0
        assert "--output" in result.stdout





