# from __future__ import annotations

import enum
import unittest
from dataclasses import dataclass
from datetime import datetime
from typing import (Any, AnyStr, Dict, Generic, List, Literal, Optional, Set,
                    Tuple, TypeVar, Union, get_origin, get_type_hints)

from petit_ts.handlers import TupleHandler
from petit_ts.named_types import get_extended_name
from petit_ts.inline_type import Type

from .. import ClassHandler, Named, TypeStore, patch_get_origin_for_Union
from ..exceptions import InvalidTypeArgument, MissingHandler

# this makes us able, to use NamedUnion as Union for pydantic, without it we can't use
# Named(Union[...])
# patch_get_origin_for_Union()


# B = Named(Optional[Literal[1, 2, 'test_string']])

# C = Named(Tuple[int, str])


# F = Named(Union[str, int])
# G = Named(Optional[Union[str, int, float]])


# class L(BaseModel):
#     p: str
#     j: Optional[Union[str, int, None]]
#     l: B
#     # op: D
#     # m: F
#     # e: Union[F, G]


# @dataclass
# class Deb:
#     a: int
#     l: L
#     dezo: Optional[Deb]
#     pp: D
#     m: F
#     e: Union[F, G]


# D = Named(Optional[Tuple[C, Tuple[str, str]]])
# A = Named(Optional[Union[int, str, Deb, B, C]])


# store = TypeStore(export_all=True)
# store.add_class_handler(BaseModelHandler)
# store.get_repr(A)
# print(store.get_repr(B))
# print(store.get_full_repr(D))
# print(store.get_all_not_inlined())

# d = {
#     'p':1,
#     'j':'',
#     'l':1,
# }

# m = L(**d)
# print(m)


class Test(unittest.TestCase):
    def test_named_literal(self):
        store = TypeStore(export_all=True)
        B = Named(Literal[1, 2, 'test_string'])
        res = 'export type B = 1 | 2 | "test_string";'
        self.assertEqual(store.get_full_repr(B), res)
        self.assertEqual(store.get_repr(B), 'B')

    def test_named_inline_literal(self):
        store = TypeStore(export_all=True)
        B = Literal[1, 2, 'test_string']
        res = '1 | 2 | "test_string"'
        self.assertEqual(store.get_repr(B), res)

    def test_invalid_literal(self):
        store = TypeStore(export_all=True)
        B = Optional[Literal[1, int]]
        with self.assertRaises(InvalidTypeArgument):
            store.get_repr(B)

    def test_named_Union(self):
        store = TypeStore(export_all=True)
        K = Named(Optional[Union[int, str]])
        res = 'export type K = number /*int*/ | string | undefined;'
        self.assertEqual(store.get_full_repr(K), res)
        self.assertEqual(store.get_repr(K), 'K')

    def test_inline_Union_not_mapping(self):
        store = TypeStore(export_all=True)
        B = Optional[Union[int, str]]
        res = 'number /*int*/ | string | undefined'
        self.assertEqual(store.get_repr(B), res)

    def test_inline_Union_mapping(self):
        store = TypeStore(export_all=True)
        T = TypeVar('T')

        @dataclass
        class jeb(Generic[T]):
            p: T

        @dataclass
        class test(Generic[T]):
            a: Optional[Union[int, str]]
            b: List[jeb[T]]
            c: T
        res = 'export type test<T> = {\n\ta?: number /*int*/ | string;\n\tb: (jeb<T>)[];\n\tc: T;\n};'
        self.assertEqual(store.get_full_repr(test), res)

    def test_valid_enum(self):
        class e(enum.Enum):
            A = 'A'
            B = 1

        store = TypeStore(export_all=True)
        res = 'export enum e {\n\tA = "A",\n\tB = 1,\n};'
        self.assertEqual(store.get_full_repr(e), res)

    def test_invalid_enum(self):
        class e(enum.Enum):
            A = 'A'
            B = {'test': 1}

        store = TypeStore(export_all=True)
        res = 'export enum e {\n\tA = "A",\n};'
        with self.assertRaises(InvalidTypeArgument):
            store.get_full_repr(e)

    def test_custom_and_patch(self):

        from pydantic import BaseModel
        patch_get_origin_for_Union()

        class BaseModelHandler(ClassHandler):
            @staticmethod
            def is_mapping() -> bool:
                return True

            @staticmethod
            def should_handle(cls, store, origin, args) -> bool:
                return issubclass(cls, BaseModel)

            @staticmethod
            def build(cls: BaseModel, store, origin, args, is_mapping_key) -> Tuple[Optional[str], Dict[str, Any]]:
                name = cls.__name__
                fields = get_type_hints(cls)
                return name, fields

        store = TypeStore(export_all=True)
        store.add_class_handler(BaseModelHandler)

        class T(BaseModel):
            a: int
        res = 'export type T = {\n\ta: number /*int*/;\n};'
        self.assertEqual(store.get_repr(T), 'T')
        self.assertEqual(store.get_full_repr(T), res)

    def test_tuple(self):
        G = Tuple[Tuple[str, str]]
        store = TypeStore(export_all=False, raise_on_error=True)
        res = '[[string, string]]'
        self.assertEqual(store.get_repr(G), res)

    def test_named_tuple(self):
        store = TypeStore()
        C = Named(Tuple[int, str])
        D = Named(Optional[Tuple[C, Tuple[str, str]]])
        res = 'type D = [C, [string, string]] | undefined;'
        self.assertEqual(store.get_full_repr(D), res)

    def test_inline_dataclass(self):
        a = Type(a=Optional[str], b=Optional[Union[int, str]], c=int)
        store = TypeStore()
        res = '{ \ta?: string, \tb?: number /*int*/ | string, \tc: number /*int*/ }'
        self.assertEqual(store.get_repr(a), res)

    def test_not_inline_dataclass(self):
        @dataclass
        class a:
            a: Optional[str]
            b: int
        store = TypeStore()
        res = 'type a = {\n\ta?: string;\n\tb: number /*int*/;\n};'
        self.assertEqual(store.get_full_repr(a), res)
        self.assertEqual(store.get_repr(a), 'a')

    def test_basic_array(self):
        a = List[int]
        store = TypeStore()
        res = 'number[]'
        self.assertEqual(store.get_repr(a), res)

    def test_inline_generic_array(self):
        b = List[Union[int, str]]
        store = TypeStore()
        res = '(number /*int*/ | string)[]'
        print('extended name should be None', get_extended_name(b))
        self.assertEqual(store.get_repr(b), res)

    def test_generic_array(self):
        u = Named(Union[int, str])
        a = List[u]
        store = TypeStore()
        res = '(u)[]'
        print('extended name should be u', get_extended_name(u))
        self.assertEqual(store.get_repr(a), res)

    def test_generic_mapping(self):
        K = str
        V = TypeVar('V')
        u = Dict[K, V]
        store = TypeStore()
        res = '{ [key: string]: V }'
        self.assertEqual(store.get_repr(u), res)

    def test_store(self):
        store = TypeStore()
        self.assertEqual(store.get_repr(TypeVar('T')), 'T')
        self.assertEqual(store.get_full_repr(TypeVar('T')), 'T')

    def test_all_not_inlined(self):
        store = TypeStore()
        F = Named(Union[str, int])
        G = Named(Optional[Union[str, int, float]])
        store.add_type(F)
        store.add_type(G)
        res = 'type F = string | number /*int*/;\ntype G = string | number /*int*/ | number /*float*/ | undefined;'
        self.assertEqual(store.get_all_not_inlined(), res)

    def test_basic_cast(self):
        store = TypeStore()
        store.add_basic_cast(datetime, str)

        @dataclass
        class t:
            date: datetime

        res = 'type t = {\n\tdate: string;\n};'
        self.assertEqual(store.get_full_repr(t), res)

    def test_no_handler_class(self):
        store = TypeStore()

        @dataclass
        class t:
            date: datetime

        res = "type t = {\n\tdate: any /* <class 'datetime.datetime'> */;\n};"
        self.assertEqual(store.get_full_repr(t), res)

    def test_no_handler_class_with_raise(self):
        store = TypeStore(raise_on_error=True)

        @dataclass
        class t:
            date: datetime

        with self.assertRaises(MissingHandler):
            store.get_full_repr(t)

    def test_no_handler_not_class(self):
        store = TypeStore(raise_on_error=True)
        store.basic_handlers.remove(TupleHandler)

        with self.assertRaises(MissingHandler):
            print(store.get_repr(tuple()))
        store.add_basic_handler(TupleHandler)

    def test_add_basic(self):
        store = TypeStore(raise_on_error=True)
        # nomminally a handler is never removed
        store.basic_handlers.remove(TupleHandler)
        store.add_basic_handler(TupleHandler)
        self.assertEqual(store.get_repr(Tuple[str, str]), '[string, string]')

    def test_patch(self):
        from typing import get_origin
        self.assertEqual(get_origin(list), None)

    def test_export_one(self):
        store = TypeStore()
        a = Named(Union[int, str])
        self.assertEqual(store.get_full_repr(a, exported=True),
                         'export type a = number /*int*/ | string;')

    def test_named_mapping(self):
        store = TypeStore()
        a = Named(Dict[int, str])
        self.assertEqual(store.get_full_repr(a),
                         'type a = { [key: number /*int*/]: string }')

    def test_named_list(self):
        store = TypeStore()
        a = Named(List[int])
        self.assertEqual(store.get_full_repr(a),
                         'type a = (number /*int*/)[]')