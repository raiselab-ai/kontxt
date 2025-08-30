import argparse
from textwrap import dedent

def app() -> None:
    parser = argparse.ArgumentParser(
        prog="kontxt",
        description="Kontxt — framework-agnostic context management for AI apps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """\
            Examples:
              kontxt version
              python -m kontxt version
            """
        ),
    )

    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("version", help="Show Kontxt version")

    args = parser.parse_args()
    if args.cmd == "version":
        from . import __version__, __status__
        print(f"Kontxt {__version__} ({__status__})")
    else:
        parser.print_help()
