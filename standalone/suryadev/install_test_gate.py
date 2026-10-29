"""Windows SURYADEV installer test gate with complete local failure report.

Does not copy/modify the active SURYADEV installation or its learning data.
Tests run once, without suppressing or retrying failures. A nonzero exit
code prevents the installer from copying any files.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import unittest


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def run(*, source=None, log_path=None):
    root = Path(source or Path(__file__).resolve().parent).resolve()
    report = Path(log_path or Path(tempfile.gettempdir()) / "suryadev-install-tests.log")
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        log = report.open("w", encoding="utf-8")
    except OSError as exc:
        print("Unable to create local test report: " + str(exc), file=sys.stderr)
        return 2
    with log:
        out = Tee(sys.stderr, log)
        print("SURYADEV installer regression test gate", file=out)
        print("Python: " + sys.version.split()[0] +
              " | Platform: " + platform.system() + " " + platform.release(), file=out)
        print("Source: " + str(root), file=out)
        print("Report: " + str(report), file=out)
        print("No active library database is opened by this test gate.", file=out)
        try:
            # Use the same standard-library test discoverer as
            # 'python -m unittest discover -s tests -v'.
            sys.path.insert(0, str(root))
            suite = unittest.TestLoader().discover(
                start_dir=str(root / "tests"),
                pattern="test_*.py",
                # Equivalent to 'python -m unittest discover -s tests':
                # tests/ intentionally has no __init__.py, so root cannot
                # be the explicit unittest top-level import package.
            )
            result = unittest.TextTestRunner(stream=out, verbosity=2).run(suite)
        except Exception:
            import traceback
            print("\nERROR: Installer test suite could not be loaded:", file=out)
            traceback.print_exc(file=out)
            out.flush()
            return 2

        if not result.wasSuccessful():
            print("\n" + "=" * 72, file=out)
            print("FAILED TESTS: full tracebacks are printed below", file=out)
            for label, collection in (("ERROR", result.errors),
                                      ("FAIL", result.failures),
                                      ("UNEXPECTED SUCCESS", result.unexpectedSuccesses)):
                for entry in collection:
                    if label == "UNEXPECTED SUCCESS":
                        print("\n" + label + ": " + str(entry), file=out)
                    else:
                        test, tb = entry
                        print("\n" + label + ": " + str(test), file=out)
                        print(tb, file=out)
            print("\nAll installed files and existing research data remain unchanged.", file=out)
            print("Test report: " + str(report), file=out)
            out.flush()
            return 1
        print("\nPASS: " + str(result.testsRun) + " tests completed successfully.", file=out)
        out.flush()
        return 0


def main():
    parser = argparse.ArgumentParser(description="SURYADEV installation test diagnostics")
    parser.add_argument("--source", default=None)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()
    raise SystemExit(run(source=args.source, log_path=args.log))


if __name__ == "__main__":
    main()
