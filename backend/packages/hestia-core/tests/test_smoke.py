import hestia_core


def test_package_imports() -> None:
    assert hestia_core.__version__ == "0.1.0"
