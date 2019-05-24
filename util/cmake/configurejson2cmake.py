#!/usr/bin/env python3
#############################################################################
##
## Copyright (C) 2018 The Qt Company Ltd.
## Contact: https://www.qt.io/licensing/
##
## This file is part of the plugins of the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:GPL-EXCEPT$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and The Qt Company. For licensing terms
## and conditions see https://www.qt.io/terms-conditions. For further
## information use the contact form at https://www.qt.io/contact-us.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3 as published by the Free Software
## Foundation with exceptions as appearing in the file LICENSE.GPL3-EXCEPT
## included in the packaging of this file. Please review the following
## information to ensure the GNU General Public License requirements will
## be met: https://www.gnu.org/licenses/gpl-3.0.html.
##
## $QT_END_LICENSE$
##
#############################################################################

import json_parser
import os.path
import re
import sys
from typing import Set, Union, List, Dict

from helper import map_qt_library, featureName, map_platform, \
    find_3rd_party_library_mapping, generate_find_package_info

knownTests = set()  # type: Set[str]


class LibraryMapping:
    def __init__(self, package: str, resultVariable: str, appendFoundSuffix: bool = True) -> None:
        self.package = package
        self.resultVariable = resultVariable
        self.appendFoundSuffix = appendFoundSuffix

def map_tests(test: str) -> str:
    testmap = {
        'c++11': '$<COMPILE_FEATURES:cxx_std_11>',
        'c++14': '$<COMPILE_FEATURES:cxx_std_14>',
        'c++1z': '$<COMPILE_FEATURES:cxx_std_17>',
        'c99': '$<COMPILE_FEATURES:c_std_99>',
        'c11': '$<COMPILE_FEATURES:c_std_11>',

        'x86SimdAlways': 'ON',  # FIXME: Make this actually do a compile test.

        'aesni': 'TEST_subarch_aes',
        'avx': 'TEST_subarch_avx',
        'avx2': 'TEST_subarch_avx2',
        'avx512f': 'TEST_subarch_avx512f',
        'avx512cd': 'TEST_subarch_avx512cd',
        'avx512dq': 'TEST_subarch_avx512dq',
        'avx512bw': 'TEST_subarch_avx512bw',
        'avx512er': 'TEST_subarch_avx512er',
        'avx512pf': 'TEST_subarch_avx512pf',
        'avx512vl': 'TEST_subarch_avx512vl',
        'avx512ifma': 'TEST_subarch_avx512ifma',
        'avx512vbmi': 'TEST_subarch_avx512vbmi',
        'avx512vbmi2': 'TEST_subarch_avx512vbmi2',
        'avx512vpopcntdq': 'TEST_subarch_avx512vpopcntdq',
        'avx5124fmaps': 'TEST_subarch_avx5124fmaps',
        'avx5124vnniw': 'TEST_subarch_avx5124vnniw',
        'bmi': 'TEST_subarch_bmi',
        'bmi2': 'TEST_subarch_bmi2',
        'cx16': 'TEST_subarch_cx16',
        'f16c': 'TEST_subarch_f16c',
        'fma': 'TEST_subarch_fma',
        'fma4': 'TEST_subarch_fma4',
        'fsgsbase': 'TEST_subarch_fsgsbase',
        'gfni': 'TEST_subarch_gfni',
        'ibt': 'TEST_subarch_ibt',
        'lwp': 'TEST_subarch_lwp',
        'lzcnt': 'TEST_subarch_lzcnt',
        'mmx': 'TEST_subarch_mmx',
        'movbe': 'TEST_subarch_movbe',
        'mpx': 'TEST_subarch_mpx',
        'no-sahf': 'TEST_subarch_no_shaf',
        'pclmul': 'TEST_subarch_pclmul',
        'popcnt': 'TEST_subarch_popcnt',
        'prefetchwt1': 'TEST_subarch_prefetchwt1',
        'prfchw': 'TEST_subarch_prfchw',
        'pdpid': 'TEST_subarch_rdpid',
        'rdpid': 'TEST_subarch_rdpid',
        'rdseed': 'TEST_subarch_rdseed',
        'rdrnd': 'TEST_subarch_rdseed',  # FIXME: Is this the right thing?
        'rtm': 'TEST_subarch_rtm',
        'shani': 'TEST_subarch_sha',
        'shstk': 'TEST_subarch_shstk',
        'sse2': 'TEST_subarch_sse2',
        'sse3': 'TEST_subarch_sse3',
        'ssse3': 'TEST_subarch_ssse3',
        'sse4a': 'TEST_subarch_sse4a',
        'sse4_1': 'TEST_subarch_sse4_1',
        'sse4_2': 'TEST_subarch_sse4_2',
        'tbm': 'TEST_subarch_tbm',
        'xop': 'TEST_subarch_xop',

        'neon': 'TEST_subarch_neon',
        'iwmmxt': 'TEST_subarch_iwmmxt',
        'crc32': 'TEST_subarch_crc32',

        'vis': 'TEST_subarch_vis',
        'vis2': 'TEST_subarch_vis2',
        'vis3': 'TEST_subarch_vis3',

        'dsp': 'TEST_subarch_dsp',
        'dspr2': 'TEST_subarch_dspr2',

        'altivec': 'TEST_subarch_altivec',
        'spe': 'TEST_subarch_spe',
        'vsx': 'TEST_subarch_vsx',

        'posix-iconv': 'TEST_posix_iconv',
        'sun-iconv': 'TEST_sun_iconv',

        'openssl11': '(OPENSSL_VERSION VERSION_GREATER_EQUAL "1.1.0")',

        'reduce_exports': 'CMAKE_CXX_COMPILE_OPTIONS_VISIBILITY',

        'libinput_axis_api': 'ON',
        "xlib": "X11_FOUND",
    }
    if test in testmap:
        return testmap.get(test, None)
    if test in knownTests:
        return 'TEST_{}'.format(featureName(test))
    return None


def cm(ctx, *output):
    txt = ctx['output']
    if txt != '' and not txt.endswith('\n'):
        txt += '\n'
    txt += '\n'.join(output)

    ctx['output'] = txt
    return ctx


def readJsonFromDir(dir):
    path = os.path.join(dir, 'configure.json')

    print('Reading {}...'.format(path))
    assert os.path.exists(path)

    parser = json_parser.QMakeSpecificJSONParser()
    return parser.parse(path)


def processFiles(ctx, data):
    print('  files:')
    if 'files' in data:
        for (k, v) in data['files'].items():
            ctx[k] = v
    return ctx

def parseLib(ctx, lib, data, cm_fh, cmake_find_packages_set):
    newlib = find_3rd_party_library_mapping(lib)
    if not newlib:
        print('    XXXX Unknown library "{}".'.format(lib))
        return

    if newlib.packageName is None:
        print('    **** Skipping library "{}" -- was masked.'.format(lib))
        return

    print('    mapped library {} to {}.'.format(lib, newlib.targetName))

    # Avoid duplicate find_package calls.
    if newlib.targetName in cmake_find_packages_set:
        return

    # If certain libraries are used within a feature, but the feature
    # is only emitted conditionally with a simple condition (like
    # 'on Windows' or 'on Linux'), we should enclose the find_package
    # call for the library into the same condition.
    emit_if = newlib.emit_if

    # Only look through features if a custom emit_if wasn't provided.
    if not emit_if:
        for feature in data['features']:
            feature_data = data['features'][feature]
            if 'condition' in feature_data and \
                    'libs.{}'.format(lib) in feature_data['condition'] and \
                    'emitIf' in feature_data and \
                    'config.' in feature_data['emitIf']:
                emit_if = feature_data['emitIf']
                break

    if emit_if:
        emit_if = map_condition(emit_if)

    cmake_find_packages_set.add(newlib.targetName)

    cm_fh.write(generate_find_package_info(newlib, emit_if=emit_if))


def lineify(label, value, quote=True):
    if value:
        if quote:
            return '    {} "{}"\n'.format(label, value.replace('"', '\\"'))
        return '    {} {}\n'.format(label, value)
    return ''

def map_condition(condition):
    # Handle NOT:
    if isinstance(condition, list):
        condition = '(' + ') AND ('.join(condition) + ')'
    if isinstance(condition, bool):
        if condition:
            return 'ON'
        else:
            return 'OFF'
    assert isinstance(condition, str)

    mapped_features = {
        'gbm': 'gbm_FOUND',
        "system-xcb": "ON",
        "system-freetype": "ON",
        'system-pcre2': 'ON',
    }

    # Turn foo != "bar" into (NOT foo STREQUAL 'bar')
    condition = re.sub(r"(.+)\s*!=\s*('.+')", '(! \\1 == \\2)', condition)

    condition = condition.replace('!', 'NOT ')
    condition = condition.replace('&&', ' AND ')
    condition = condition.replace('||', ' OR ')
    condition = condition.replace('==', ' STREQUAL ')

    # explicitly handle input.sdk == '':
    condition = re.sub(r"input\.sdk\s*==\s*''", 'NOT INPUT_SDK', condition)

    last_pos = 0
    mapped_condition = ''
    has_failed = False
    for match in re.finditer(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_+-]+)', condition):
        substitution = None
        appendFoundSuffix = True
        if match.group(1) == 'libs':
            libmapping = find_3rd_party_library_mapping(match.group(2))

            if libmapping and libmapping.packageName:
                substitution = libmapping.packageName
                if libmapping.resultVariable:
                    substitution = libmapping.resultVariable
                if libmapping.appendFoundSuffix:
                    substitution += '_FOUND'

        elif match.group(1) == 'features':
            feature = match.group(2)
            if feature in mapped_features:
                substitution = mapped_features.get(feature)
            else:
                substitution = 'QT_FEATURE_{}'.format(featureName(match.group(2)))

        elif match.group(1) == 'subarch':
            substitution = 'TEST_arch_{}_subarch_{}'.format("${TEST_architecture_arch}",
                                                            match.group(2))

        elif match.group(1) == 'call':
            if match.group(2) == 'crossCompile':
                substitution = 'CMAKE_CROSSCOMPILING'

        elif match.group(1) == 'tests':
            substitution = map_tests(match.group(2))

        elif match.group(1) == 'input':
            substitution = 'INPUT_{}'.format(featureName(match.group(2)))

        elif match.group(1) == 'config':
            substitution = map_platform(match.group(2))

        elif match.group(1) == 'arch':
            if match.group(2) == 'i386':
                # FIXME: Does this make sense?
                substitution = '(TEST_architecture_arch STREQUAL i386)'
            elif match.group(2) == 'x86_64':
                substitution = '(TEST_architecture_arch STREQUAL x86_64)'
            elif match.group(2) == 'arm':
                # FIXME: Does this make sense?
                substitution = '(TEST_architecture_arch STREQUAL arm)'
            elif match.group(2) == 'arm64':
                # FIXME: Does this make sense?
                substitution = '(TEST_architecture_arch STREQUAL arm64)'
            elif match.group(2) == 'mips':
                # FIXME: Does this make sense?
                substitution = '(TEST_architecture_arch STREQUAL mips)'

        if substitution is None:
            print('    XXXX Unknown condition "{}".'.format(match.group(0)))
            has_failed = True
        else:
            mapped_condition += condition[last_pos:match.start(1)] + substitution
            last_pos = match.end(2)

    mapped_condition += condition[last_pos:]

    # Space out '(' and ')':
    mapped_condition = mapped_condition.replace('(', ' ( ')
    mapped_condition = mapped_condition.replace(')', ' ) ')

    # Prettify:
    condition = re.sub('\\s+', ' ', mapped_condition)
    condition = condition.strip()

    if has_failed:
        condition += ' OR FIXME'

    return condition


def parseInput(ctx, input, data, cm_fh):
    skip_inputs = {
        "prefix", "hostprefix", "extprefix",

        "archdatadir", "bindir", "datadir", "docdir",
        "examplesdir", "external-hostbindir", "headerdir",
        "hostbindir", "hostdatadir", "hostlibdir",
        "importdir", "libdir", "libexecdir",
        "plugindir", "qmldir", "settingsdir",
        "sysconfdir", "testsdir", "translationdir",

        "android-arch", "android-ndk", "android-ndk-host",
        "android-ndk-platform", "android-sdk",
        "android-toolchain-version", "android-style-assets",

        "appstore-compliant",

        "avx", "avx2", "avx512", "c++std", "ccache", "commercial",
        "compile-examples", "confirm-license",
        "dbus",
        "dbus-runtime",

        "debug", "debug-and-release",

        "developer-build",

        "device", "device-option",

        "f16c",

        "force-asserts", "force-debug-info", "force-pkg-config",
        "framework",

        "gc-binaries",

        "gdb-index",

        "gcc-sysroot",

        "gcov",

        "gnumake",

        "gui",

        "harfbuzz",

        "headersclean",

        "incredibuild-xge",

        "libudev",
        "ltcg",
        "make",
        "make-tool",

        "mips_dsp",
        "mips_dspr2",
        "mp",

        "nomake",

        "opensource",

        "optimize-debug", "optimize-size", "optimized-qmake", "optimized-tools",

        "pch",

        "pkg-config",

        "platform",

        "plugin-manifests",
        "profile",
        "qreal",

        "reduce-exports", "reduce-relocations",

        "release",

        "rpath",

        "sanitize",

        "sdk",

        "separate-debug-info",

        "shared",

        "silent",

        "qdbus",

        "sse2",
        "sse3",
        "sse4.1",
        "sse4.2",
        "ssse3",
        "static",
        "static-runtime",
        "strip",
        "syncqt",
        "sysroot",
        "testcocoon",
        "use-gold-linker",
        "warnings-are-errors",
        "Werror",
        "widgets",
        "xplatform",
        "zlib",

        "doubleconversion",

        "eventfd",
        "glib",
        "icu",
        "inotify",
        "journald",
        "pcre",
        "posix-ipc",
        "pps",
        "slog2",
        "syslog",

        "sqlite",
    }

    if input in skip_inputs:
        print('    **** Skipping input {}: masked.'.format(input))
        return

    type = data
    if isinstance(data, dict):
        type = data["type"]

    if type == "boolean":
        print('    **** Skipping boolean input {}: masked.'.format(input))
        return

    if type == "enum":
        cm_fh.write("# input {}\n".format(input))
        cm_fh.write('set(INPUT_{} "undefined" CACHE STRING "")\n'.format(featureName(input)))
        cm_fh.write('set_property(CACHE INPUT_{} PROPERTY STRINGS undefined {})\n\n'.format(featureName(input), " ".join(data["values"])))
        return

    print('    XXXX UNHANDLED INPUT TYPE {} in input description'.format(type))
    return


#  "tests": {
#        "cxx11_future": {
#            "label": "C++11 <future>",
#            "type": "compile",
#            "test": {
#                "include": "future",
#                "main": [
#                    "std::future<int> f = std::async([]() { return 42; });",
#                    "(void)f.get();"
#                ],
#                "qmake": "unix:LIBS += -lpthread"
#            }
#        },
def parseTest(ctx, test, data, cm_fh):
    skip_tests = {
       'c++11', 'c++14', 'c++1y', 'c++1z',
       'c11', 'c99',
       'gc_binaries',
       'posix-iconv', "sun-iconv",
       'precomile_header',
       'reduce_exports',
       'separate_debug_info',  # FIXME: see if cmake can do this
       'gc_binaries',
       'libinput_axis_api',
       'xlib',
    }

    if test in skip_tests:
        print('    **** Skipping features {}: masked.'.format(test))
        return

    if data["type"] == "compile":
        knownTests.add(test)

        details = data["test"]

        if isinstance(details, str):
            print('    XXXX UNHANDLED TEST SUB-TYPE {} in test description'.format(details))
            return

        head = details.get("head", "")
        if isinstance(head, list):
            head = "\n".join(head)

        sourceCode = head + '\n'

        include = details.get("include", "")
        if isinstance(include, list):
            include = '#include <' + '>\n#include <'.join(include) + '>'
        elif include:
            include = '#include <{}>'.format(include)

        sourceCode += include + '\n'

        tail = details.get("tail", "")
        if isinstance(tail, list):
            tail = "\n".join(tail)

        sourceCode += tail + '\n'

        sourceCode += "int main(int argc, char **argv)\n"
        sourceCode += "{\n"
        sourceCode += "    (void)argc; (void)argv;\n"
        sourceCode += "    /* BEGIN TEST: */\n"

        main = details.get("main", "")
        if isinstance(main, list):
            main = "\n".join(main)

        sourceCode += main + '\n'

        sourceCode += "    /* END TEST: */\n"
        sourceCode += "    return 0;\n"
        sourceCode += "}\n"

        sourceCode = sourceCode.replace('"', '\\"')

        librariesCmakeName = ""
        qmakeFixme = ""

        cm_fh.write("# {}\n".format(test))
        if "qmake" in details: # We don't really have many so we can just enumerate them all
            if details["qmake"] == "unix:LIBS += -lpthread":
                librariesCmakeName = format(featureName(test)) + "_TEST_LIBRARIES"
                cm_fh.write("if (UNIX)\n")
                cm_fh.write("    set(" + librariesCmakeName + " pthread)\n")
                cm_fh.write("endif()\n")
            elif details["qmake"] == "linux: LIBS += -lpthread -lrt":
                librariesCmakeName = format(featureName(test)) + "_TEST_LIBRARIES"
                cm_fh.write("if (LINUX)\n")
                cm_fh.write("    set(" + librariesCmakeName + " pthread rt)\n")
                cm_fh.write("endif()\n")
            elif details["qmake"] == "CONFIG += c++11":
                # do nothing we're always in c++11 mode
                pass
            else:
                qmakeFixme = "# FIXME: qmake: {}\n".format(details["qmake"])

        if "use" in data:
            if data["use"] == "egl xcb_xlib":
                librariesCmakeName = format(featureName(test)) + "_TEST_LIBRARIES"
                cm_fh.write("if (HAVE_EGL AND X11_XCB_FOUND AND X11_FOUND)\n")
                cm_fh.write("    set(" + librariesCmakeName + " EGL::EGL X11::X11 X11::XCB)\n")
                cm_fh.write("endif()\n")
            else:
                qmakeFixme += "# FIXME: use: {}\n".format(data["use"])

        cm_fh.write("qt_config_compile_test({}\n".format(featureName(test)))
        cm_fh.write(lineify("LABEL", data.get("label", "")))
        if librariesCmakeName != "":
            cm_fh.write(lineify("LIBRARIES", "${"+librariesCmakeName+"}"))
            cm_fh.write("    CODE\n")
        cm_fh.write('"' + sourceCode + '"')
        if qmakeFixme != "":
            cm_fh.write(qmakeFixme)
        cm_fh.write(")\n\n")

    elif data["type"] == "x86Simd":
        knownTests.add(test)

        label = data["label"]

        cm_fh.write("# {}\n".format(test))
        cm_fh.write("qt_config_compile_test_x86simd({} \"{}\")\n".format(test, label))
        cm_fh.write("\n")

#    "features": {
#        "android-style-assets": {
#            "label": "Android Style Assets",
#            "condition": "config.android",
#            "output": [ "privateFeature" ],
#            "comment": "This belongs into gui, but the license check needs it here already."
#        },
    else:
        print('    XXXX UNHANDLED TEST TYPE {} in test description'.format(data["type"]))


def parseFeature(ctx, feature, data, cm_fh):
    # This is *before* the feature name gets normalized! So keep - and + chars, etc.
    feature_mapping = {
        'alloc_h': None,  # handled by alloc target
        'alloc_malloc_h': None,
        'alloc_stdlib_h': None,
        'build_all': None,
        'c++11': None,   # C and C++ versions
        'c11': None,
        'c++14': None,
        'c++1y': None,
        'c++1z': None,
        'c89': None,
        'c99': None,
        'ccache': None,
        'compiler-flags': None,
        'cross_compile': None,
        'debug_and_release': None,
        'debug': None,
        'dlopen': {
            'condition': 'UNIX',
        },
        'doubleconversion': None,
        'enable_gdb_index': None,
        'enable_new_dtags': None,
        'force_debug_info': None,
        'framework': {
            'condition': 'APPLE AND BUILD_SHARED_LIBS',
        },
        'gc_binaries': None,
        'gcc-sysroot': None,
        'gcov': None,
        'gnu-libiconv': {
            'condition': 'NOT WIN32 AND NOT QNX AND NOT ANDROID AND NOT APPLE AND TEST_posix_iconv AND NOT TEST_iconv_needlib',
            'enable': 'TEST_posix_iconv AND NOT TEST_iconv_needlib',
            'disable': 'NOT TEST_posix_iconv OR TEST_iconv_needlib',
        },
        'GNUmake': None,
        'harfbuzz': {
            'condition': 'HARFBUZZ_FOUND'
        },
        'host-dbus': None,
        'iconv': {
            'condition': 'NOT QT_FEATURE_icu AND QT_FEATURE_textcodec AND ( TEST_posix_iconv OR TEST_sun_iconv )'
        },
        'incredibuild_xge': None,
        'jpeg': {
            'condition': 'QT_FEATURE_imageformatplugin AND JPEG_FOUND'
        },
        'ltcg': None,
        'msvc_mp': None,
        'optimize_debug': None,
        'optimize_size': None,
        # special case to enable implicit feature on WIN32, until ANGLE is ported
        'opengl-desktop': {
            'autoDetect': ''
        },
        # special case to disable implicit feature on WIN32, until ANGLE is ported
        'opengl-dynamic': {
            'autoDetect': 'OFF'
        },
        'opengles2': { # special case to disable implicit feature on WIN32, until ANGLE is ported
            'condition': 'NOT WIN32 AND ( NOT APPLE_WATCHOS AND NOT QT_FEATURE_opengl_desktop AND GLESv2_FOUND )'
        },
        'pkg-config': None,
        'posix_fallocate': None,  # Only needed for sqlite, which we do not want to build
        'posix-libiconv': {
            'condition': 'NOT WIN32 AND NOT QNX AND NOT ANDROID AND NOT APPLE AND TEST_posix_iconv AND TEST_iconv_needlib',
            'enable': 'TEST_posix_iconv AND TEST_iconv_needlib',
            'disable': 'NOT TEST_posix_iconv OR NOT TEST_iconv_needlib',
        },
        'precompile_header': None,
        'profile': None,
        'qmakeargs': None,
        'qpa_default_platform': None, # Not a bool!
        'reduce_relocations': None,
        'release': None,
        'release_tools': None,
        'rpath_dir': None,  # rpath related
        'rpath': None,
        'sanitize_address': None,   # sanitizer
        'sanitize_memory': None,
        'sanitizer': None,
        'sanitize_thread': None,
        'sanitize_undefined': None,
        'separate_debug_info': None,
        'shared': None,
        'silent': None,
        'sql-sqlite' : {
            'condition': 'QT_FEATURE_datestring AND SQLite3_FOUND',
        },
        'stack-protector-strong': None,
        'static': None,
        'static_runtime': None,
        'stl': None,  # Do we really need to test for this in 2018?!
        'strip': None,
        'sun-libiconv': {
            'condition': 'NOT WIN32 AND NOT QNX AND NOT ANDROID AND NOT APPLE AND TEST_sun_iconv',
            'enable': 'TEST_sun_iconv',
            'disable': 'NOT TEST_sun_iconv',
        },
        'system-doubleconversion': None,  # No system libraries anymore!
        'system-freetype': None,
        'system-harfbuzz': None,
        'system-jpeg': None,
        'system-pcre2': None,
        'system-png': None,
        'system-sqlite': None,
        'system-xcb': None,
        'system-zlib': None,
        'use_gold_linker': None,
        'verifyspec': None,   # qmake specific...
        'warnings_are_errors': None,  # FIXME: Do we need these?
        'xkbcommon-system': None, # another system library, just named a bit different from the rest
    }

    mapping = feature_mapping.get(feature, {})

    if mapping is None:
        print('    **** Skipping features {}: masked.'.format(feature))
        return

    handled = { 'autoDetect', 'comment', 'condition', 'description', 'disable', 'emitIf', 'enable', 'label', 'output', 'purpose', 'section' }
    label = mapping.get('label', data.get('label', ''))
    purpose = mapping.get('purpose', data.get('purpose', data.get('description', label)))
    autoDetect = map_condition(mapping.get('autoDetect', data.get('autoDetect', '')))
    condition = map_condition(mapping.get('condition', data.get('condition', '')))
    output = mapping.get('output', data.get('output', []))
    comment = mapping.get('comment', data.get('comment', ''))
    section = mapping.get('section', data.get('section', ''))
    enable = map_condition(mapping.get('enable', data.get('enable', '')))
    disable = map_condition(mapping.get('disable', data.get('disable', '')))
    emitIf = map_condition(mapping.get('emitIf', data.get('emitIf', '')))

    for k in [k for k in data.keys() if k not in handled]:
        print('    XXXX UNHANDLED KEY {} in feature description'.format(k))

    if not output:
        # feature that is only used in the conditions of other features
        output = ["internalFeature"]

    publicFeature = False # #define QT_FEATURE_featurename in public header
    privateFeature = False # #define QT_FEATURE_featurename in private header
    negativeFeature = False # #define QT_NO_featurename in public header
    internalFeature = False # No custom or QT_FEATURE_ defines
    publicDefine = False # #define MY_CUSTOM_DEFINE in public header

    for o in output:
        outputType = o
        outputArgs = {}
        if isinstance(o, dict):
            outputType = o['type']
            outputArgs = o

        if outputType in ['varAssign', 'varAppend', 'varRemove', 'publicQtConfig', 'privateConfig', 'publicConfig']:
            continue
        elif outputType == 'define':
            publicDefine = True
        elif outputType == 'feature':
            negativeFeature = True
        elif outputType == 'publicFeature':
            publicFeature = True
        elif outputType == 'privateFeature':
            privateFeature = True
        elif outputType == 'internalFeature':
            internalFeature = True
        else:
            print('    XXXX UNHANDLED OUTPUT TYPE {} in feature {}.'.format(outputType, feature))
            continue

    if not any([publicFeature, privateFeature, internalFeature, publicDefine, negativeFeature]):
        print('    **** Skipping feature {}: Not relevant for C++.'.format(feature))
        return

    cxxFeature = featureName(feature)

    def writeFeature(name, publicFeature=False, privateFeature=False, labelAppend=''):
        if comment:
            cm_fh.write('# {}\n'.format(comment))

        cm_fh.write('qt_feature("{}"'.format(name))
        if publicFeature:
            cm_fh.write(' PUBLIC')
        if privateFeature:
            cm_fh.write(' PRIVATE')
        cm_fh.write('\n')

        cm_fh.write(lineify('SECTION', section))
        cm_fh.write(lineify('LABEL', label + labelAppend))
        if purpose != label:
            cm_fh.write(lineify('PURPOSE', purpose))
        cm_fh.write(lineify('AUTODETECT', autoDetect, quote=False))
        cm_fh.write(lineify('CONDITION', condition, quote=False))
        cm_fh.write(lineify('ENABLE', enable, quote=False))
        cm_fh.write(lineify('DISABLE', disable, quote=False))
        cm_fh.write(lineify('EMIT_IF', emitIf, quote=False))
        cm_fh.write(')\n')

    # Write qt_feature() calls before any qt_feature_definition() calls

    # Default internal feature case.
    featureCalls = {}
    featureCalls[cxxFeature] = {'name': cxxFeature, 'labelAppend': ''}

    # Go over all outputs to compute the number of features that have to be declared
    for o in output:
        outputType = o
        name = cxxFeature

        # The label append is to provide a unique label for features that have more than one output
        # with different names.
        labelAppend = ''

        if isinstance(o, dict):
            outputType = o['type']
            if 'name' in o:
                name = o['name']
                labelAppend = ': {}'.format(o['name'])

        if outputType not in ['feature', 'publicFeature', 'privateFeature']:
            continue
        if name not in featureCalls:
            featureCalls[name] = {'name': name, 'labelAppend': labelAppend}

        if outputType in ['feature', 'publicFeature']:
            featureCalls[name]['publicFeature'] = True
        elif outputType == 'privateFeature':
            featureCalls[name]['privateFeature'] = True

    # Write the qt_feature() calls from the computed feature map
    for _, args in featureCalls.items():
        writeFeature(**args)

    # Write qt_feature_definition() calls
    for o in output:
        outputType = o
        outputArgs = {}
        if isinstance(o, dict):
            outputType = o['type']
            outputArgs = o

        # Map negative feature to define:
        if outputType == 'feature':
            outputType = 'define'
            outputArgs = {'name': 'QT_NO_{}'.format(cxxFeature.upper()),
                          'negative': True,
                          'value': 1,
                          'type': 'define'}

        if outputType != 'define':
            continue

        if outputArgs.get('name') is None:
            print('    XXXX DEFINE output without name in feature {}.'.format(feature))
            continue

        cm_fh.write('qt_feature_definition("{}" "{}"'.format(cxxFeature, outputArgs.get('name')))
        if outputArgs.get('negative', False):
            cm_fh.write(' NEGATE')
        if outputArgs.get('value') is not None:
            cm_fh.write(' VALUE "{}"'.format(outputArgs.get('value')))
        cm_fh.write(')\n')


def processInputs(ctx, data, cm_fh):
    print('  inputs:')
    if 'commandline' not in data:
        return

    commandLine = data['commandline']
    if "options" not in commandLine:
        return

    for input in commandLine['options']:
        parseInput(ctx, input, commandLine['options'][input], cm_fh)


def processTests(ctx, data, cm_fh):
    print('  tests:')
    if 'tests' not in data:
        return

    for test in data['tests']:
        parseTest(ctx, test, data['tests'][test], cm_fh)


def processFeatures(ctx, data, cm_fh):
    print('  features:')
    if 'features' not in data:
        return

    for feature in data['features']:
        parseFeature(ctx, feature, data['features'][feature], cm_fh)


def processLibraries(ctx, data, cm_fh):
    cmake_find_packages_set = set()
    print('  libraries:')
    if 'libraries' not in data:
        return

    for lib in data['libraries']:
        parseLib(ctx, lib, data, cm_fh, cmake_find_packages_set)


def processSubconfigs(dir, ctx, data):
    assert ctx is not None
    if 'subconfigs' in data:
        for subconf in data['subconfigs']:
            subconfDir = os.path.join(dir, subconf)
            subconfData = readJsonFromDir(subconfDir)
            subconfCtx = ctx
            processJson(subconfDir, subconfCtx, subconfData)


def processJson(dir, ctx, data):
    ctx['module'] = data.get('module', 'global')

    ctx = processFiles(ctx, data)

    with open(os.path.join(dir, "configure.cmake"), 'w') as cm_fh:
        cm_fh.write("\n\n#### Inputs\n\n")

        processInputs(ctx, data, cm_fh)

        cm_fh.write("\n\n#### Libraries\n\n")

        processLibraries(ctx, data, cm_fh)

        cm_fh.write("\n\n#### Tests\n\n")

        processTests(ctx, data, cm_fh)

        cm_fh.write("\n\n#### Features\n\n")

        processFeatures(ctx, data, cm_fh)

        if ctx.get('module') == 'global':
            cm_fh.write('\nqt_extra_definition("QT_VERSION_STR" "\\\"${PROJECT_VERSION}\\\"" PUBLIC)\n')
            cm_fh.write('qt_extra_definition("QT_VERSION_MAJOR" ${PROJECT_VERSION_MAJOR} PUBLIC)\n')
            cm_fh.write('qt_extra_definition("QT_VERSION_MINOR" ${PROJECT_VERSION_MINOR} PUBLIC)\n')
            cm_fh.write('qt_extra_definition("QT_VERSION_PATCH" ${PROJECT_VERSION_PATCH} PUBLIC)\n')

    # do this late:
    processSubconfigs(dir, ctx, data)


def main():
    if len(sys.argv) != 2:
       print("This scripts needs one directory to process!")
       quit(1)

    dir = sys.argv[1]

    print("Processing: {}.".format(dir))

    data = readJsonFromDir(dir)
    processJson(dir, {}, data)


if __name__ == '__main__':
    main()
