import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def raiz() -> Path:
    return RAIZ


@pytest.fixture
def python() -> str:
    return sys.executable
