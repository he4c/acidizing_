if __package__:
    from .ui import AcidizingApp
else:
    # Allow PyCharm's "Run main.py" as well as python -m acidizing.main.
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from acidizing.ui import AcidizingApp


def run() -> None:
    app = AcidizingApp()
    app.mainloop()


if __name__ == "__main__":
    run()
