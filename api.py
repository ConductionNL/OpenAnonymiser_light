from os import environ

import click
import uvicorn

from scripts.check_deps import check_versions


@click.command()
@click.option(
    "--env",
    type=click.Choice(["development", "staging", "production"]),
    default="development",
)
@click.option(
    "--host",
    type=str,
    default="0.0.0.0",
)
@click.option(
    "--port",
    type=int,
    default=8080,
)
@click.option(
    "--workers",
    type=int,
    default=1,
)
def main(env: str, host: str, port: int, workers: int) -> None:
    print("Dependency versions:")
    check_versions()
    print(f"Serving on {host}:{port} with {workers} workers in {env} mode.")
    # set environment variable with SERVER_MODE
    environ["UVICORN_SERVER_MODE"] = env

    uvicorn.run(
        app="src.api.main:app",
        host=host,
        port=port,
        reload=True if env != "production" else False,
        workers=workers,
        log_level="warning" if env == "production" else "info",
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
