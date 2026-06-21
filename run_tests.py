"""Run the SkillWiki test suite without harmless Streamlit bare-mode warnings."""

import logging
import os
from pathlib import Path
import sys
import unittest


STREAMLIT_TEST_LOGGERS = [
    "streamlit.runtime.caching.cache_data_api",
    "streamlit.runtime.scriptrunner_utils.script_run_context",
    "streamlit.runtime.state.session_state_proxy",
]

IGNORED_STREAMLIT_MESSAGES = [
    "No runtime found, using MemoryCacheStorageManager",
    "missing ScriptRunContext! This warning can be ignored when running in bare mode.",
    "Session state does not function when running a script without `streamlit run`",
]


class StreamlitWarningFilter:
    """Drop only known harmless Streamlit warnings from the test output."""

    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        if any(message in text for message in IGNORED_STREAMLIT_MESSAGES):
            return len(text)
        return self.stream.write(text)

    def flush(self):
        return self.stream.flush()

    def isatty(self):
        return self.stream.isatty()


def main() -> int:
    os.environ["STREAMLIT_LOGGER_LEVEL"] = "error"
    for logger_name in STREAMLIT_TEST_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    sys.stderr = StreamlitWarningFilter(sys.stderr)

    project_root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(project_root / "tests"),
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
