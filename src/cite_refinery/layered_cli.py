from __future__ import annotations

from . import cli as core_cli
from .app import CiteRefinery


def main(argv: list[str] | None = None) -> int:
    # Reuse the stable CLI parser/dispatch while swapping only the application
    # constructor. This keeps command behavior compatible with 0.4.x.
    core_cli.CiteRefinery = CiteRefinery
    return core_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
