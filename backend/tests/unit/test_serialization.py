"""
Unit tests for app/utils/serialization.py

Tests convert_numpy_types and safe_json_serialize functions.
No database or external service dependencies.
"""
import json
import numpy as np
import pytest

from app.utils.serialization import convert_numpy_types, safe_json_serialize


class TestConvertNumpyInteger:
    def test_int32(self):
        result = convert_numpy_types(np.int32(42))
        assert result == 42
        assert type(result) is int

    def test_int64(self):
        result = convert_numpy_types(np.int64(100))
        assert result == 100
        assert type(result) is int

    def test_int16(self):
        result = convert_numpy_types(np.int16(-5))
        assert result == -5
        assert type(result) is int


class TestConvertNumpyFloat:
    def test_float32(self):
        result = convert_numpy_types(np.float32(3.14))
        assert isinstance(result, float)
        assert abs(result - 3.14) < 0.01

    def test_float64(self):
        result = convert_numpy_types(np.float64(2.718281828))
        assert isinstance(result, float)
        assert abs(result - 2.718281828) < 1e-6


class TestConvertNumpyArray:
    def test_1d_array(self):
        arr = np.array([1, 2, 3])
        result = convert_numpy_types(arr)
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_2d_array(self):
        arr = np.array([[1, 2], [3, 4]])
        result = convert_numpy_types(arr)
        assert result == [[1, 2], [3, 4]]

    def test_empty_array(self):
        arr = np.array([])
        result = convert_numpy_types(arr)
        assert result == []


class TestConvertNumpyBool:
    def test_true(self):
        result = convert_numpy_types(np.bool_(True))
        assert result is True
        assert type(result) is bool

    def test_false(self):
        result = convert_numpy_types(np.bool_(False))
        assert result is False
        assert type(result) is bool


class TestConvertNestedDict:
    def test_nested_dict_with_numpy(self):
        data = {
            'score': np.float64(0.95),
            'count': np.int32(10),
            'values': np.array([1.0, 2.0, 3.0]),
            'nested': {
                'flag': np.bool_(True),
                'id': np.int64(99),
            }
        }
        result = convert_numpy_types(data)

        assert isinstance(result['score'], float)
        assert isinstance(result['count'], int)
        assert isinstance(result['values'], list)
        assert result['nested']['flag'] is True
        assert isinstance(result['nested']['id'], int)

    def test_dict_with_native_types(self):
        data = {'a': 1, 'b': 'hello', 'c': True}
        result = convert_numpy_types(data)
        assert result == data


class TestConvertNestedList:
    def test_list_with_numpy(self):
        data = [np.int32(1), np.float64(2.5), np.bool_(False), 'native']
        result = convert_numpy_types(data)

        assert result[0] == 1 and type(result[0]) is int
        assert isinstance(result[1], float)
        assert result[2] is False
        assert result[3] == 'native'

    def test_nested_list(self):
        data = [[np.int32(1)], [np.float64(2.5)]]
        result = convert_numpy_types(data)
        assert result == [[1], [2.5]]


class TestConvertTuple:
    def test_tuple_with_numpy(self):
        data = (np.int32(1), np.float64(2.0), 'three')
        result = convert_numpy_types(data)
        assert isinstance(result, tuple)
        assert result == (1, 2.0, 'three')
        assert type(result[0]) is int


class TestConvertSet:
    def test_set_with_numpy(self):
        data = {np.int32(1), np.int32(2), np.int32(3)}
        result = convert_numpy_types(data)
        assert isinstance(result, set)
        assert result == {1, 2, 3}


class TestPassthroughNativeTypes:
    def test_native_int(self):
        assert convert_numpy_types(42) == 42
        assert type(convert_numpy_types(42)) is int

    def test_native_float(self):
        assert convert_numpy_types(3.14) == 3.14

    def test_native_str(self):
        assert convert_numpy_types('hello') == 'hello'

    def test_native_bool(self):
        assert convert_numpy_types(True) is True

    def test_none(self):
        assert convert_numpy_types(None) is None


class TestSafeJsonSerialize:
    def test_complex_structure(self):
        data = {
            'metrics': {
                'accuracy': np.float64(0.95),
                'count': np.int32(100),
                'predictions': np.array([0.1, 0.5, 0.9]),
                'flag': np.bool_(True),
            },
            'labels': ['buy', 'sell'],
            'meta': None,
        }
        result = safe_json_serialize(data)

        # Must be JSON-serializable
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

        # Verify values
        assert result['metrics']['accuracy'] == pytest.approx(0.95)
        assert result['metrics']['count'] == 100
        assert result['metrics']['predictions'] == [pytest.approx(0.1), pytest.approx(0.5), pytest.approx(0.9)]
        assert result['metrics']['flag'] is True
        assert result['labels'] == ['buy', 'sell']
        assert result['meta'] is None

    def test_already_native(self):
        data = {'a': 1, 'b': 2.0, 'c': 'text'}
        result = safe_json_serialize(data)
        assert result == data

    def test_empty_structures(self):
        assert safe_json_serialize({}) == {}
        assert safe_json_serialize([]) == []
        assert safe_json_serialize(()) == ()
