import logging

import typer

from metrics_server.utils import config_logging

app = typer.Typer()


@app.command()
def main():
    """Example log"""
    config_logging(logging.ERROR)
    world = typer.style("world!", fg=typer.colors.GREEN, bold=True)
    typer.echo("Hello " + world)


if __name__ == "__main__":
    app()
