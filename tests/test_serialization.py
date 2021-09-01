#!/usr/bin/env python
import os
import json
import sys
import pytest
import datetime
from pickle import UnpicklingError
from decimal import Decimal
from deepdiff import DeepDiff
from deepdiff.helper import pypy3
from deepdiff.serialization import (
    pickle_load, pickle_dump, ForbiddenModule, ModuleNotFoundError,
    MODULE_NOT_FOUND_MSG, FORBIDDEN_MODULE_MSG, pretty_print_diff,
    load_path_content, UnsupportedFormatErr)
from conftest import FIXTURES_DIR
from ordered_set import OrderedSet
from tests import PicklableClass

import logging
logging.disable(logging.CRITICAL)

t1 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": [1, 2, 3]}}
t2 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": "world\n\n\nEnd"}}


class TestSerialization:
    """Tests for Serializations."""

    def test_serialization_text(self):
        ddiff = DeepDiff(t1, t2)
        assert "builtins.list" in ddiff.to_json_pickle()
        jsoned = ddiff.to_json()
        assert "world" in jsoned

    def test_deserialization(self):
        ddiff = DeepDiff(t1, t2)
        jsoned = ddiff.to_json_pickle()
        ddiff2 = DeepDiff.from_json_pickle(jsoned)
        assert ddiff == ddiff2

    def test_serialization_tree(self):
        ddiff = DeepDiff(t1, t2, view='tree')
        pickle_jsoned = ddiff.to_json_pickle()
        assert "world" in pickle_jsoned
        jsoned = ddiff.to_json()
        assert "world" in jsoned

    def test_deserialization_tree(self):
        ddiff = DeepDiff(t1, t2, view='tree')
        jsoned = ddiff.to_json_pickle()
        ddiff2 = DeepDiff.from_json_pickle(jsoned)
        assert 'type_changes' in ddiff2

    def test_serialize_custom_objects_throws_error(self):
        class A:
            pass

        class B:
            pass

        t1 = A()
        t2 = B()
        ddiff = DeepDiff(t1, t2)
        with pytest.raises(TypeError):
            ddiff.to_json()

    def test_serialize_custom_objects_with_default_mapping(self):
        class A:
            pass

        class B:
            pass

        t1 = A()
        t2 = B()
        ddiff = DeepDiff(t1, t2)
        default_mapping = {A: lambda x: 'obj A', B: lambda x: 'obj B'}
        result = ddiff.to_json(default_mapping=default_mapping)
        expected_result = {"type_changes": {"root": {"old_type": "A", "new_type": "B", "old_value": "obj A", "new_value": "obj B"}}}
        assert expected_result == json.loads(result)

    # These lines are long but make it easier to notice the difference:
    @pytest.mark.parametrize('verbose_level, expected', [
        (0, {"type_changes": {"root[0]": {"old_type": str, "new_type": int}}, "dictionary_item_added": ["root[1][5]"], "dictionary_item_removed": ["root[1][3]"], "iterable_item_added": {"root[2]": "d"}}),
        (1, {"type_changes": {"root[0]": {"old_type": str, "new_type": int, "old_value": "a", "new_value": 10}}, "dictionary_item_added": ["root[1][5]"], "dictionary_item_removed": ["root[1][3]"], "values_changed": {"root[1][1]": {"new_value": 2, "old_value": 1}}, "iterable_item_added": {"root[2]": "d"}}),
        (2, {"type_changes": {"root[0]": {"old_type": str, "new_type": int, "old_value": "a", "new_value": 10}}, "dictionary_item_added": {"root[1][5]": 6}, "dictionary_item_removed": {"root[1][3]": 4}, "values_changed": {"root[1][1]": {"new_value": 2, "old_value": 1}}, "iterable_item_added": {"root[2]": "d"}}),
    ])
    def test_to_dict_at_different_verbose_level(self, verbose_level, expected):
        t1 = ['a', {1: 1, 3: 4}, ]
        t2 = [10, {1: 2, 5: 6}, 'd']

        ddiff = DeepDiff(t1, t2, verbose_level=verbose_level)
        assert expected == ddiff.to_dict()


@pytest.mark.skipif(pypy3, reason='clevercsv is not supported in pypy3')
class TestLoadContet:

    @pytest.mark.parametrize('path1, validate', [
        ('t1.json', lambda x: x[0]['key1'] == 'value1'),
        ('t1.yaml', lambda x: x[0][0] == 'name'),
        ('t1.toml', lambda x: x['servers']['alpha']['ip'] == '10.0.0.1'),
        ('t1.csv', lambda x: x[0]['last_name'] == 'Nobody'),
        ('t1.pickle', lambda x: x[1] == 1),
    ])
    def test_load_path_content(self, path1, validate):
        path = os.path.join(FIXTURES_DIR, path1)
        result = load_path_content(path)
        assert validate(result)

    def test_load_path_content_when_unsupported_format(self):
        path = os.path.join(FIXTURES_DIR, 't1.unsupported')
        with pytest.raises(UnsupportedFormatErr):
            load_path_content(path)


class TestPickling:

    def test_serialize(self):
        obj = [1, 2, 3, None, {10: 11E2}, frozenset(['a', 'c']), OrderedSet([2, 1]),
               datetime.datetime.utcnow(), datetime.time(11), Decimal('11.2'), 123.11]
        serialized = pickle_dump(obj)
        loaded = pickle_load(serialized)
        assert obj == loaded

    @pytest.mark.skipif(pypy3, reason='short pickle not supported in pypy3')
    def test_pickle_that_is_string(self):
        serialized_str = 'DeepDiff Delta Payload v0-0-1\nBlah'
        with pytest.raises(UnpicklingError):
            pickle_load(serialized_str)

    def test_custom_object_deserialization_fails_without_explicit_permission(self):
        obj = PicklableClass(10)
        module_dot_name = 'tests.{}'.format(PicklableClass.__name__)

        serialized = pickle_dump(obj)

        expected_msg = FORBIDDEN_MODULE_MSG.format(module_dot_name)
        with pytest.raises(ForbiddenModule) as excinfo:
            pickle_load(serialized)
        assert expected_msg == str(excinfo.value)

        # Explicitly allowing the module to be loaded
        loaded = pickle_load(serialized, safe_to_import={module_dot_name})
        assert obj == loaded

        # Explicitly allowing the module to be loaded. It can take a list instead of a set.
        loaded2 = pickle_load(serialized, safe_to_import=[module_dot_name])
        assert obj == loaded2

    def test_unpickling_object_that_is_not_imported_raises_error(self):

        def get_the_pickle():
            import wave
            obj = wave.Error
            return pickle_dump(obj)

        serialized = get_the_pickle()
        # Making sure that the module is unloaded.
        del sys.modules['wave']
        module_dot_name = 'wave.Error'

        expected_msg = MODULE_NOT_FOUND_MSG.format(module_dot_name)
        with pytest.raises(ModuleNotFoundError) as excinfo:
            pickle_load(serialized, safe_to_import=module_dot_name)
        assert expected_msg == str(excinfo.value)


class TestDeepDiffPretty:
    """Tests for pretty() method of DeepDiff"""

    class TestingClass:
        one = 1

    testing_class = TestingClass

    @pytest.mark.parametrize('t1, t2, item_path, old_type, new_type, old_val_displayed, new_val_displayed',
                             [
                                 [{2: 2, 4: 4}, {2: 'b', 4: 4}, 'root[2]', 'int', 'str', '2', '"b"'],
                                 [[1, 2, 3], [1, '2', 3], 'root[1]', 'int', 'str', '2', '"2"'],
                                 [[1, 2, 3], {1, 2, 3}, 'root', 'list', 'set', '[1, 2, 3]', '{1, 2, 3}']
                             ])
    def test_pretty_print_diff_type_changes(self, t1, t2, item_path, old_type, new_type, old_val_displayed,
                                            new_val_displayed):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['type_changes'].items[0])
        assert result == 'Type of {} changed from {} to {} and value changed from {} to {}.'.format(item_path, old_type, new_type, old_val_displayed, new_val_displayed)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [{2: 2, 4: 4}, {2: 2, 4: 4, 5: 5}, 'root[5]'],
                             ])
    def test_pretty_print_diff_dictionary_item_added(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['dictionary_item_added'].items[0])
        assert result == 'Item {} added to dictionary.'.format(item_path)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [{2: 2, 4: 4}, {2: 2}, 'root[4]'],
                             ])
    def test_pretty_print_diff_dictionary_item_removed(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['dictionary_item_removed'].items[0])
        assert result == 'Item {} removed from dictionary.'.format(item_path)

    @pytest.mark.parametrize('t1, t2, item_path, old_val_displayed, new_val_displayed',
                             [
                                 [{2: 2, 4: 4}, {2: 3, 4: 4}, 'root[2]', '2', '3'],
                                 [['a', 'b', 'c'], ['a', 'b', 'd'], 'root[2]', '"c"', '"d"']
                             ])
    def test_pretty_print_diff_values_changed(self, t1, t2, item_path, old_val_displayed, new_val_displayed):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['values_changed'].items[0])
        assert result == 'Value of {} changed from {} to {}.'.format(item_path, old_val_displayed, new_val_displayed)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [[1, 2, 3], [1, 2, 3, 4], 'root[3]'],
                             ])
    def test_pretty_print_diff_iterable_item_added(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['iterable_item_added'].items[0])
        assert result == 'Item {} added to iterable.'.format(item_path)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [[1, 2, 3], [1, 2], 'root[2]'],
                             ])
    def test_pretty_print_diff_iterable_item_removed(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['iterable_item_removed'].items[0])
        assert result == 'Item {} removed from iterable.'.format(item_path)

    def test_pretty_print_diff_attribute_added(self):
        t1 = self.testing_class()
        t2 = self.testing_class()
        t2.two = 2

        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['attribute_added'].items[0])
        assert result == 'Attribute root.two added.'

    def test_pretty_print_diff_attribute_removed(self):
        t1 = self.testing_class()
        t1.two = 2
        t2 = self.testing_class()

        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['attribute_removed'].items[0])
        assert result == 'Attribute root.two removed.'

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [{1, 2}, {1, 2, 3}, 'root[3]'],
                             ])
    def test_pretty_print_diff_set_item_added(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['set_item_added'].items[0])
        assert result == 'Item {} added to set.'.format(item_path)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [{1, 2, 3}, {1, 2}, 'root[3]'],
                             ])
    def test_pretty_print_diff_set_item_removed(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree')
        result = pretty_print_diff(ddiff.tree['set_item_removed'].items[0])
        assert result == 'Item {} removed from set.'.format(item_path)

    @pytest.mark.parametrize('t1, t2, item_path',
                             [
                                 [[1, 2, 3, 2], [1, 2, 3], 'root[1]'],
                             ])
    def test_pretty_print_diff_repetition_change(self, t1, t2, item_path):
        ddiff = DeepDiff(t1, t2, view='tree', ignore_order=True, report_repetition=True)
        result = pretty_print_diff(ddiff.tree['repetition_change'].items[0])
        assert result == 'Repetition change for item {}.'.format(item_path)

    def test_pretty_form_method(self):
        t1 = {2: 2, 3: 3, 4: 4}
        t2 = {2: 'b', 4: 5, 5: 5}
        ddiff = DeepDiff(t1, t2, view='tree')
        result = ddiff.pretty()
        expected = (
            'Item root[5] added to dictionary.'
            '\nItem root[3] removed from dictionary.'
            '\nType of root[2] changed from int to str and value changed from 2 to "b".'
            '\nValue of root[4] changed from 4 to 5.'
        )
        assert result == expected
