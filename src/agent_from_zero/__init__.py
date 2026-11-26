def main(argv=None) -> int:
    from .capstone import main as capstone_main

    return capstone_main(argv)


def run(question, *, trace_dir=None):
    from .capstone import run as capstone_run

    return capstone_run(question, trace_dir=trace_dir)


__all__ = ["main", "run"]
