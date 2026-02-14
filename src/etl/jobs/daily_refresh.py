"""Budget-mode daily refresh entrypoint."""

from datetime import datetime


def run() -> None:
    """Execute a lightweight daily refresh workflow."""

    # TODO: wire to NBAApiClient endpoints and SQL upserts.
    print(f"[{datetime.utcnow().isoformat()}] Daily refresh placeholder executed.")


if __name__ == "__main__":
    run()

