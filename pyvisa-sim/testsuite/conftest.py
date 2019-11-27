import os

import pytest
import pyvisa

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try back-ported to PY<37 `importlib_resources`
    import importlib_resources as pkg_resources


@pytest.fixture(scope='session')
def resource_manager():
    rm = pyvisa.ResourceManager('@sim')
    yield rm
    rm.close()


@pytest.fixture
def channels():
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'channels.yaml')
    rm = pyvisa.ResourceManager(path + '@sim')
    yield rm
    rm.close()
