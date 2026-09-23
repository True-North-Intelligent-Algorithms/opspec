"""A blocking dialog. This is an example; being obvious is the point."""

__all__ = ["shout"]


def shout(message: str) -> None:
    from qtpy.QtWidgets import QMessageBox

    QMessageBox.information(None, "example_runner!!!!!", message)
