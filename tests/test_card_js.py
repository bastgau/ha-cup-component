"""JavaScript tests of the Lovelace card (tests/js/*.test.mjs), run under Node's own test runner.

CI sets up Node (>= 22) for the integration tests; without Node the tests are skipped locally.
"""

from pathlib import Path
import shutil
import subprocess

import pytest

JS_TESTS = sorted((Path(__file__).parent / "js").glob("*.test.mjs"))


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
@pytest.mark.parametrize("test_file", JS_TESTS, ids=lambda path: path.name)
def test_card_javascript(test_file: Path) -> None:
    """Each JavaScript test file passes under ``node --test``."""
    node: str = shutil.which("node") or "node"
    result = subprocess.run(  # noqa: S603  # a fixed command on a file of the repository
        [node, "--test", str(test_file)],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
