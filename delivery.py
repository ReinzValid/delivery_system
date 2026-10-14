try:
    from .main_cli import main
except ImportError:
    from main_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
