import os

import pytest

import pyvisa


@pytest.fixture(scope="session")
def resource_manager():
    rm = pyvisa.ResourceManager("@sim")
    yield rm
    rm.close()


@pytest.fixture
def channels():
    path = os.path.join(os.path.dirname(__file__), "fixtures", "channels.yaml")
    rm = pyvisa.ResourceManager(path + "@sim")
    yield rm
    rm.close()


@pytest.fixture
def no_termination_chars_resource_manager():
    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "no_termination_chars.yaml"
    )
    rm = pyvisa.ResourceManager(path + "@sim")
    yield rm
    rm.close()
