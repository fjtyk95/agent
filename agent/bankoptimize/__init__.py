"""Bank optimization package."""

from .cli import main as cli_main

__version__ = "0.2.0"
__all__ = ["run_pipeline", "cli_main"]


def run_pipeline(*args, **kwargs):
    """Run the optimization pipeline.
    
    This function provides programmatic access to the optimization workflow.
    For command-line usage, use the CLI interface via cli_main().
    
    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
        
    Raises:
        RuntimeError: Always raised as this is a stub implementation.
    """
    raise RuntimeError("run_pipeline is not yet implemented")