"""Enable running Sequel as a module with `python -m sequel`."""

from sequel.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
