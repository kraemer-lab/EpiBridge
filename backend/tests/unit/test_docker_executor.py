import pytest

from app.execution.util import parse_exit_code


class TestParseExitCode:
    def test_legacy_int(self):
        assert parse_exit_code(0) == 0
        assert parse_exit_code(1) == 1
        assert parse_exit_code(42) == 42

    def test_dict(self):
        assert parse_exit_code({"StatusCode": 0}) == 0
        assert parse_exit_code({"StatusCode": 1}) == 1
        assert parse_exit_code({"StatusCode": 42}) == 42

    def test_dict_missing_key(self):
        with pytest.raises(RuntimeError, match="without integer StatusCode"):
            parse_exit_code({})

    def test_dict_non_int_value(self):
        with pytest.raises(RuntimeError, match="without integer StatusCode"):
            parse_exit_code({"StatusCode": "oops"})

    def test_none(self):
        with pytest.raises(RuntimeError, match="Unexpected container wait result type"):
            parse_exit_code(None)

    def test_list(self):
        with pytest.raises(RuntimeError, match="Unexpected container wait result type"):
            parse_exit_code([0])
