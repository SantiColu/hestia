import hestia_project


def test_package_imports() -> None:
    assert hestia_project.__version__ == "0.1.0"
