import pytest


@pytest.mark.parametrize("input,expected", [(2, 4), (3, 6), (4, 8)])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
