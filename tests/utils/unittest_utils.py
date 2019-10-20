# -*- coding: utf-8 -*-
# Copyright (c) 2013-2014 Google, Inc.
# Copyright (c) 2013-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014 Arun Persaud <arun@nubati.net>
# Copyright (c) 2015-2018 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015 Aru Sahni <arusahni@gmail.com>
# Copyright (c) 2015 Ionel Cristian Maries <contact@ionelmc.ro>
# Copyright (c) 2016 Derek Gustafson <degustaf@gmail.com>
# Copyright (c) 2016 Glenn Matthews <glenn@e-dad.net>
# Copyright (c) 2017-2018 Anthony Sottile <asottile@umich.edu>
# Copyright (c) 2017 Pierre Sassoulas <pierre.sassoulas@cea.fr>
# Copyright (c) 2017 ttenhoeve-aa <ttenhoeve@appannie.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2018 Pierre Sassoulas <pierre.sassoulas@wisebim.fr>

# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/master/COPYING

import io
import pathlib
import re

import pytest
from pylint.lint import fix_import_path
from pylint.utils import utils

_DATA_DIR = pathlib.Path(__file__).parent


def test__basename_in_blacklist_re_match():
    patterns = [re.compile(".*enchilada.*"), re.compile("unittest_.*")]
    assert utils._basename_in_blacklist_re("unittest_utils.py", patterns)
    assert utils._basename_in_blacklist_re("cheese_enchiladas.xml", patterns)


def test__basename_in_blacklist_re_nomatch():
    patterns = [re.compile(".*enchilada.*"), re.compile("unittest_.*")]
    assert not utils._basename_in_blacklist_re("test_utils.py", patterns)
    assert not utils._basename_in_blacklist_re("enchilad.py", patterns)


def test_decoding_stream_unknown_encoding():
    """decoding_stream should fall back to *some* decoding when given an
    unknown encoding.
    """
    binary_io = io.BytesIO(b"foo\nbar")
    stream = utils.decoding_stream(binary_io, "garbage-encoding")
    # should still act like a StreamReader
    ret = stream.readlines()
    assert ret == ["foo\n", "bar"]


def test_decoding_stream_known_encoding():
    binary_io = io.BytesIO("€".encode("cp1252"))
    stream = utils.decoding_stream(binary_io, "cp1252")
    assert stream.read() == "€"


@pytest.mark.parametrize(
    "files_or_modules,expected",
    [
        (
            [str(_DATA_DIR / "expand_modules_data/case1/module1.py")],
            [
                {
                    "path": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "name": "module1",
                    "isarg": True,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "basename": "module1",
                }
            ],
        ),
        (
            [str(_DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1")],
            [
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "pkg1.subpkg1",
                    "isarg": True,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
            ],
        ),
        (
            [str(_DATA_DIR / "expand_modules_data/case1/pkg1")],
            [
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "name": "pkg1",
                    "isarg": True,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule1.py"
                    ),
                    "name": "pkg1.submodule1",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule2.py"
                    ),
                    "name": "pkg1.submodule2",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "pkg1.subpkg1.__init__",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
            ],
        ),
    ],
)
def test_simple_expand_modules(files_or_modules, expected):
    with fix_import_path(files_or_modules):
        found = utils.expand_modules(files_or_modules, (), ())
    sorted_found = (
        sorted(found[0], key=(lambda item: item["path"])),
        sorted(found[1], key=(lambda item: item["ex"])),
    )
    assert sorted_found == (expected, [])


@pytest.mark.parametrize(
    "extra_path,files_or_modules,expected",
    [
        (
            [str(_DATA_DIR / "expand_modules_data/case1")],
            ["module1"],
            [
                {
                    "path": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "name": "module1",
                    "isarg": True,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "basename": "module1",
                }
            ],
        ),
        (
            [str(_DATA_DIR / "expand_modules_data/case1")],
            ["pkg1.subpkg1"],
            [
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "pkg1.subpkg1",
                    "isarg": True,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "basename": "pkg1.subpkg1",
                },
            ],
        ),
        (
            [str(_DATA_DIR / "expand_modules_data/case1")],
            ["pkg1"],
            [
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "name": "pkg1",
                    "isarg": True,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule1.py"
                    ),
                    "name": "pkg1.submodule1",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule2.py"
                    ),
                    "name": "pkg1.submodule2",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "pkg1.subpkg1.__init__",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "basename": "pkg1",
                },
            ],
        ),
    ],
)
def test_modules_expand_modules(extra_path, files_or_modules, expected):
    with fix_import_path(extra_path):
        found = utils.expand_modules(files_or_modules, (), ())
    sorted_found = (
        sorted(found[0], key=(lambda item: item["path"])),
        sorted(found[1], key=(lambda item: item["ex"])),
    )
    assert sorted_found == (expected, [])


# These fail because pylint.utils._modpath_from_file._is_package_cb
# checks for __init__.py files all the way up the module path.
# But this is not the case when namespaces are involved.
@pytest.mark.parametrize(
    "extra_path,files_or_modules,expected",
    [
        pytest.param(
            [str(_DATA_DIR / "expand_modules_data")],
            ["case1.pkg1"],
            [
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "name": "case1.pkg1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule1.py"
                    ),
                    "name": "case1.pkg1.submodule1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule2.py"
                    ),
                    "name": "case1.pkg1.submodule2",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "case1.pkg1.subpkg1.__init__",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "case1.pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "case1.pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
            ],
            marks=pytest.mark.xfail(),
        ),
        pytest.param(
            [str(_DATA_DIR / "expand_modules_data")],
            ["case1"],
            [
                {
                    "path": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "name": "case1.module1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "name": "case1.pkg1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule1.py"
                    ),
                    "name": "case1.pkg1.submodule1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule2.py"
                    ),
                    "name": "case1.pkg1.submodule2",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "case1.pkg1.subpkg1.__init__",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "case1.pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "case1.pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
            ],
            marks=pytest.mark.xfail(),
        ),
    ],
)
def test_namespace_expand_modules(extra_path, files_or_modules, expected):
    with fix_import_path(extra_path):
        found = utils.expand_modules(files_or_modules, (), ())
    sorted_found = (
        sorted(found[0], key=(lambda item: item["path"])),
        sorted(found[1], key=(lambda item: item["ex"])),
    )
    assert sorted_found == (expected, [])


@pytest.mark.parametrize(
    "files_or_modules,expected",
    [
        (
            [str(_DATA_DIR / "expand_modules_data/case1")],
            [
                {
                    "path": str(_DATA_DIR / "expand_modules_data/case1/__init__.py"),
                    "name": "case1",
                    "isarg": True,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1/__init__.py"
                    ),
                    "basename": "case1",
                }
            ],
        )
    ],
)
def test_non_recursive_expand_modules(files_or_modules, expected):
    with fix_import_path(files_or_modules):
        found = utils.expand_modules(files_or_modules, (), ())
    sorted_found = (
        sorted(found[0], key=(lambda item: item["path"])),
        sorted(found[1], key=(lambda item: item["ex"])),
    )
    assert sorted_found == (expected, [])


@pytest.mark.parametrize(
    "files_or_modules,expected",
    [
        (
            [str(_DATA_DIR / "expand_modules_data/case1")],
            [
                {
                    "path": str(_DATA_DIR / "expand_modules_data/case1/module1.py"),
                    "name": "module1",
                    "isarg": False,
                    "basepath": str(_DATA_DIR / "expand_modules_data/case1"),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/__init__.py"
                    ),
                    "name": "pkg1.__init__",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule1.py"
                    ),
                    "name": "pkg1.submodule1",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/submodule2.py"
                    ),
                    "name": "pkg1.submodule2",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR / "expand_modules_data/case1/pkg1/subpkg1/__init__.py"
                    ),
                    "name": "pkg1.subpkg1.__init__",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submodulea.py"
                    ),
                    "name": "pkg1.subpkg1.submodulea",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
                {
                    "path": str(
                        _DATA_DIR
                        / "expand_modules_data/case1/pkg1/subpkg1/submoduleb.py"
                    ),
                    "name": "pkg1.subpkg1.submoduleb",
                    "isarg": False,
                    "basepath": str(
                        _DATA_DIR / "expand_modules_data/case1"
                    ),
                    "basename": "case1",
                },
            ],
        )
    ],
)
def test_recursive_expand_modules(files_or_modules, expected):
    with fix_import_path(files_or_modules):
        found = utils.expand_modules(files_or_modules, (), (), recursive=True)
    sorted_found = (
        sorted(found[0], key=(lambda item: item["path"])),
        sorted(found[1], key=(lambda item: item["ex"])),
    )
    assert sorted_found == (expected, [])
