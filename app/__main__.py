import sys

from app.web import create_app


def main(argv: list[str]) -> int:
    # Commands (serve, replay, ...) are added by features; with no command, building the app
    # proves the wiring imports and constructs.
    create_app()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
