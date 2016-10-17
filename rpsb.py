#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ren'Py Script Builder takes an input script file and generates
a Ren'Py v6.99.11 compatible .rpy file(s).

Usage: "python rpsb.py input-file [-o output-dir]"
Use "--help" for more info.
"""
from __future__ import print_function, unicode_literals
from builtins import str, range, object

import os
import sys
import getopt
import re
import time
import types
import traceback
import codecs
from os import path
from functools import reduce

__version__ = "0.6.2"
__author__ = "Nathan Sullivan"
__email__ = "contact@torrentails.com"
__license__ = "MIT"

##-----------------------------------------------------------------------------
## Globals
##-----------------------------------------------------------------------------

state = {
    "master_in_file": None,
    "cur_in_file": None,
    "cur_out_file": None,
    "next_out_file": None,
    "control_file": None,
    "open_files": set(),
    "known_line_rep": {},
    "known_character_rep": {},
    "file_chain": [],
    "parent_labels": set(),
    "is_nvl_mode": False,
}

config = {
    "create_parent_files": False,
    "create_flow_control_file": True,
    "flow_control_ignore": None,
    "copy_comments": False,
    "copy_special_comments": "#",
    "nvl_character": "NVL",
    "nvl_prefix": "",
    "nvl_suffix": "_NVL",
    "output_path": ".",
    "auto_return": True,
    "abort_on_error": True,
}

stats = {
    "in_files": 0,
    "out_files": 0,
    "in_lines": 0,
    "out_lines": 0,
    "commands_processed": 0,
    "line_replacements": 0,
    "character_replacements": 0,
    "narration_lines": 0,
    "dialogue_lines": 0,
    "start_time": time.time()
}

rep_dict1 = {
    r'\{': '\xc0',
    r'\}': '\xc1',
    r'\*': '\xc2',
    r'\+': '\xc3',
    r'\?': '\xc4',
    r'\\': '\xc5',
    '.': r'\.',
    '(': r'\(',
    ')': r'\)',
    '[': r'\[',
    ']': r'\]'
}

rep_dict2 = {
    '{': '(',
    '}': ')',
    '*': '.*?',
    '+': '.+?',
    '?': '.?',
    '^': r'\^',
    '$': r'\$',
    '|': r'\|',
    '\xc0': r'\{',
    '\xc1': r'\}',
    '\xc2': r'\*',
    '\xc3': r'\+',
    '\xc4': r'\?',
    '\xc5': r'\\'
}

rep_dict3 = {r'\{': '\xc0', r'\}': '\xc1', '\xc0': '{', '\xc1': '}'}

command_list = [
    re.compile("^:(line)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(line:)$"),
    re.compile("^:(character)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(character:)$"),
    re.compile("^:(:)\s*(\.?.*?):?$"),
    re.compile("^:(sc)\s+(.*)$"),
    re.compile("^:(s)\s+(.*)$"),
    re.compile("^:(w)\s+(.*)$"),
    re.compile("^:(p)\s+(.*?)\s+(.*)$"),
    re.compile("^:(pm)\s+(.*)$"),
    re.compile("^:(ps)\s+(.*)$"),
    re.compile("^:(pa)\s+(.*)$"),
    re.compile("^:(v)\s+(.*)$"),
    re.compile("^:(q)\s+(.*?)\s+(.*)$"),
    re.compile("^:(stop)\s*(.*)?$"),
    re.compile("^:(c)\s+(.*)$"),
    re.compile("^:(j)\s+(.*)$"),
    re.compile("^:(r)$"),
    re.compile("^:(r)\s+(.*)$"),
    re.compile("^:(choice):$"),
    re.compile("^:(if)\s+(.*?):$"),
    re.compile("^:(elif)\s+(.*?):$"),
    re.compile("^:(else):$"),
    re.compile("^:(nvl):$"),
    re.compile('^:(clear)$'),
    re.compile("^:(import)\s+(.*)$"),
    re.compile("^:(file)\s+(.*)$"),
    re.compile("^:(log)\s+(0|1|2|3|4|" \
               "VERBOSE|DEBUG|INFO|WARN|WARNING|ERROR)\s+(.*)$"),
    re.compile("^:(config)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(config:)$"),
    re.compile("^:(break)$")
]

parent_label_re = re.compile("^(\w*)\.?.*$")
empty_line_re = re.compile("^\s*$")
comment_re = re.compile("^(\s*)#(.*)$")
python_re = re.compile("^(\$.*)$")
command_re = re.compile("^:(.*)$")

##-----------------------------------------------------------------------------
## Helper Classes
##-----------------------------------------------------------------------------

try:
    import colorama
    colorama.init()
    Fore = colorama.Fore
    Back = colorama.Back
    Style = colorama.Style
except ImportError:
    class __fake_col__(object):
        def __getattr__(*a, **kw):
            return ''
    Fore = __fake_col__()
    Back = Fore
    Style = Fore


class Colorama_Helper(object):
    r = Style.RESET_ALL+Fore.WHITE
    l = (
        Fore.LIGHTBLACK_EX,
        Fore.LIGHTBLACK_EX,
        Fore.WHITE,
        Fore.YELLOW,
        Fore.RED
    )

    def __getitem__(self, i):
        return self.l[i]
_c = Colorama_Helper()


class Current_Line_Str(object):
    def __str__(self):
        if len(state["file_chain"]):
            _f = state["file_chain"][-1]
            return "{}|{} ".format(_f["file_name"], _f["cur_line"])
        return '<init> '

    def __add__(self, other):
        if issubclass(type(other), (str, unicode)):
            return str(self)+other
        raise TypeError("unsupported operand type(s) for +:"
            " 'str' and '{}'".format(type(other).__name__))

    def __radd__(self, other):
        if issubclass(type(other), (str, unicode)):
            return other+str(self)
        raise TypeError("unsupported operand type(s) for +:"
            " '{}' and 'str'".format(type(other).__name__))
_ln = Current_Line_Str()


class Indent_Level_Str(object):
    def __str__(self):
        if state["is_nvl_mode"] is False:
            return '    '*state["file_chain"][-1]["cur_indent"]
        return '    '*(state["file_chain"][-1]["cur_indent"]-1)

    def __add__(self, other):
        if issubclass(type(other), (str, unicode)):
            return str(self)+other
        raise TypeError("unsupported operand type(s) for +:"
            " 'str' and '{}'".format(type(other).__name__))

    def __radd__(self, other):
        if issubclass(type(other), (str, unicode)):
            return other+str(self)
        raise TypeError("unsupported operand type(s) for +:"
            " '{}' and 'str'".format(type(other).__name__))
_il = Indent_Level_Str()


class LOGLEVEL(object):
    ERROR = 4
    WARN = 3
    WARNING = 3
    INFO = 2
    DEBUG = 1
    VERB = 0
    VERBOSE = 0

    def __getitem__(self, i):
        return ('VERB', 'DEBUG', 'INFO', 'WARN', 'ERROR')[i]
LOGLEVEL = LOGLEVEL()

##-----------------------------------------------------------------------------
## Logger
##-----------------------------------------------------------------------------

_tmp_log = []

class _Logger(object):

    def __init__(self, tmp_log, flush_number=10):
        if _debug == 2:
            self.log_save_level = LOGLEVEL.VERB
            self.log_display_level = LOGLEVEL.DEBUG
        elif _debug == 1:
            self.log_save_level = LOGLEVEL.DEBUG
            self.log_display_level = LOGLEVEL.DEBUG
        else:
            self.log_save_level = LOGLEVEL.INFO
            self.log_display_level = LOGLEVEL.INFO

        self.__errors = 0
        self.__warnings = 0

        self.__log = []
        self.__log_flush_number = flush_number
        self.__log_count = 0
        _file, _ = path.splitext(path.basename(__file__))
        self.__log_file = _file+'.log'

        _log = []
        for val in tmp_log:
            if val['level'] >= self.log_save_level:
                log_string = ("<{0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}>"
                    " [{1:<6} {2}\n".format(time.localtime(val['time']),
                    LOGLEVEL[val['level']]+']', val['message']))
                _log.append(log_string)

            if LOGLEVEL.ERROR > val['level'] >= self.log_display_level:
                print(_c[val['level']]+"[{:<6} {}".format(
                    LOGLEVEL[val['level']]+']', val['message'])+_c.r)

            if val['level'] == LOGLEVEL.WARN:
                self.__warnings += 1
            elif val['level'] >= LOGLEVEL.ERROR:
                self.__errors += 1

        if _log:
            try:
                with open(self.__log_file, 'w') as f:
                    f.writelines(_log)
            except IOError:
                raise
                # log("Unable to open log file for writing.", LOGLEVEL.ERROR)

    def __call__(self, msg, level=LOGLEVEL.INFO, exit=1):
        if level >= self.log_save_level:
            self.__log_count += 1
        else:
            return

        cur_time = time.time()
        msg = _ln+str(msg)
        self.__log.append({'time': cur_time, 'level': level, 'message': msg})

        if level == LOGLEVEL.WARN:
            self.__warnings += 1
        elif level >= LOGLEVEL.ERROR:
            self.__errors += 1

        if LOGLEVEL.ERROR > level >= self.log_display_level:
            print(_c[level]+"[{:<6} {}".format(LOGLEVEL[level]+']', msg)+_c.r)

        elif level >= LOGLEVEL.ERROR:
            print(_c[level]+"[{:<6} {}".format(LOGLEVEL[level]+']', msg)+_c.r)
            if exit and config["abort_on_error"]:
                sys.exit(exit)

        if self.__log_count >= self.__log_flush_number:
            self.flush()

    def flush(self):
        _log = []
        for l in self.__log:
            if l['level'] >= self.log_save_level:
                log_string = ("<{0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}>"
                    " [{1:<6} {2}\n".format(time.localtime(l['time']),
                    LOGLEVEL[l['level']]+']', l['message']))
                _log.append(log_string)

        if _log:
            try:
                with open(self.__log_file, 'a') as f:
                    f.writelines(_log)
                self.__log = []
            except IOError:
                raise
                # log("Unable to open log file for writing.", LOGLEVEL.ERROR)

    def log_traceback(self, exit_code=1):
        _tb = '\n>>> '.join(traceback.format_exc().split('\n')[:-1])
        log("Traceback:\n>>> {}".format(_tb),
            LOGLEVEL.ERROR, exit = False)
        sys.exit(exit_code)

    def stats(self, cur_time=None):
        log("Logging statistics", LOGLEVEL.VERB)
        _log = ["Statistics:"]

        def _s(t):
            _t = reduce(lambda ll, b: divmod(ll[0], b) + \
                ll[1:], [(t*1000,), 1000, 60, 60])
            return "{}:{:0>2}:{:0>2}.{:0>3}".format(*[int(v) for v in _t])

        def _pretty_log(key):
            _log.append("    {:>19} : {}".format(key, stats[key]))

        _stats_list = (
            "in_files",
            "out_files",
            "in_lines",
            "out_lines",
            "commands_processed",
            "line_replacements",
            "character_replacements",
            "narration_lines",
            "dialogue_lines"
        )
        for k in _stats_list:
            _pretty_log(k)

        _log.append("    {1:>19} : {0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}".format(
            time.localtime(stats["start_time"]), "start_time"))

        cur_time = cur_time or time.time()
        _run_time = cur_time - stats["start_time"]
        _log.append("    {:>19} : {}".format("total_run_time", _s(_run_time)))

        log('\n'.join(_log))

    def close(self):
        log("Closing logger", LOGLEVEL.DEBUG)

        if self.__errors:
            log("Build failed with {} WARNINGS and {} ERRORS".format(
                self.__warnings, self.__errors), LOGLEVEL.WARN)
        else:
            log("Build completed sucessfully with {} WARNINGS "
                "and {} ERRORS".format(self.__warnings, self.__errors),
                LOGLEVEL.INFO)

        self.stats(time.time())
        self.flush()


def log(msg, level=LOGLEVEL.INFO, exit=True):
    msg = _ln+msg
    _tmp_log.append({'time': time.time(), 'level': level, 'message': msg})
    if level >= LOGLEVEL.ERROR:
        if exit and config["abort_on_error"]:
            sys.exit(_c[level]+"[{:<6} {}".format(LOGLEVEL[level]+']', msg))
        else:
            print(_c[level]+"[{:<6} {}".format(LOGLEVEL[level]+']', msg)+_c.r)


def _log_close(*args, **kwargs):
    pass
log.close = _log_close


def _log_traceback(exit_code=1):
    _tb = "\n        ".join(traceback.format_exc().split('\n'))
    log("Traceback:\n        {}".format(_tb),
        LOGLEVEL.ERROR, exit = exit_code)
log.log_traceback = _log_traceback

##-----------------------------------------------------------------------------
## Misc Functions
##-----------------------------------------------------------------------------

def setup_globals(output_path=None, flush_number=10):
    global log, _tmp_log
    log("Initializing Globals", LOGLEVEL.DEBUG)

    output_path = output_path or '.'
    _old_output_path = output_path
    output_path = path.expandvars(path.expanduser(output_path))
    if not path.isdir(output_path):
        usage("Invalid output path: {}".format(_old_output_path))
    config["output_path"] = output_path

    log("initializing logger", LOGLEVEL.DEBUG)
    log = _Logger(_tmp_log, flush_number)
    del _tmp_log

    config["flow_control_ignore"] = [
        re.compile('^'+regex_prep("*_choice*")+'$'),
        re.compile('^'+regex_prep("*_ignore*")+'$')
    ]


def total(itter):
    _sum = 0
    for i in itter:
        _sum += len(i)
    return _sum


def fix_brace(matchobj):
    _m = matchobj.group(0)
    if _m in rep_dict3:
        return rep_dict3[_m]
    else:
        log("Failed to match {}".format(_m), LOGLEVEL.WARN)
        return _m


def usage(error=None, exit_code=None):
    log("Printing usage", LOGLEVEL.VERB)
    if error:
        exit_code = exit_code or 2
        log(str(error), LOGLEVEL.ERROR, exit=False)
        print('')
    print('::'+("-"*77))
    print("::   Ren'Py Script Builder")
    print('::'+("-"*77))
    print('\n  Usage:')
    print('    {} -h|source [-o:dir] [--flush=value]' \
          ' [--debug|--verbose]\n\n'.format(path.basename(__file__)))
    print("   {:>16} :: Print this help message\n".format('[-h|--help]'))
    print("   {:>16} :: Set the output directory".format('[-o:<dir>]'))
    print("   {:>16} :: NOTE: Output directory may be overwritten by config" \
        .format('[--output=<dir>]'))
    print((" "*20)+"::  options set in the source file.\n")
    print("   {:>16} :: Print this help message\n".format('[-h|--help]'))
    print("   {:>16} :: Set logging level to debug".format('[--debug]'))
    print("   {:>16} :: Set logging level to verbose.".format('[--verbose]'))
    print((" "*20)+":: "
        "WARNING: Verbose logging will print a lot of garbage to")
    print((" "*20)+":: "
        " the console and create a very large log file. Only use")
    print((" "*20)+":: "
        " this option if asked to to do so by the developer.")
    sys.exit(exit_code)

##-----------------------------------------------------------------------------
## Regex manager
##-----------------------------------------------------------------------------

def regex_prep(string):
    log("Preping string for regex: {}".format(string), LOGLEVEL.VERB)

    def _re1(matchobj):
        _m = matchobj.group(0)
        if _m in rep_dict1:
            return rep_dict1[_m]
        else:
            log("Failed to match {}".format(_m), LOGLEVEL.WARN)
            return _m

    def _re2(matchobj):
        _m = matchobj.group(0)
        if _m in rep_dict2:
            return rep_dict2[_m]
        else:
            log("Failed to match {}".format(_m), LOGLEVEL.WARN)
            return _m

    string = string.strip()
    _s = re.sub('\\\\{|\\\\}|\\\\\*|\\\\\+|'
                '\\\\\?|\.|\(|\)|\[|\]', _re1, string)
    return re.sub('\{|\}|\*|\+|\?|\^|\$|\||'
                  '\xc0|\xc1|\xc2|\xc3|\xc4|\xc5', _re2, _s)


def line_regex(match, replace):
    log("Building line replacement regex: {} = {}".format(match,
        replace), LOGLEVEL.DEBUG)
    _rep = regex_prep(match)
    log("Regex result: {}".format(_rep), LOGLEVEL.DEBUG)
    _m = re.compile('^'+_rep+'$')
    state["known_line_rep"][_m] = replace


def character_regex(match, replace):
    log("Building character replacement regex: {} = {}".format(match,
        replace), LOGLEVEL.DEBUG)
    _rep = regex_prep(match)
    log("Regex result: {}".format(_rep), LOGLEVEL.DEBUG)
    _m = re.compile('^'+_rep+'\s(.*)')
    state["known_character_rep"][_m] = (replace, ' "{}"')

##-----------------------------------------------------------------------------
## File manager
##-----------------------------------------------------------------------------

def loop_file(in_file):
    file = open_file(in_file, "r")
    log("Parsing file {}".format(in_file), LOGLEVEL.DEBUG)
    state['cur_in_file'] = file
    if stats["in_files"] == 1:
        state["master_in_file"] = file

    for _lineno, line in enumerate(file, start=1):
        state["file_chain"][-1]["cur_line"] = _lineno
        parse_line(line)

    state["file_chain"].pop()


def open_file(file_path, mode='w'):
    if mode == 'w':
        if not path.isabs(file_path):
            _, tail = path.split(file_path)
            if tail == file_path:
                file_path = path.join(config["output_path"], file_path)

        head, tail = path.split(file_path)
        try:
            os.makedirs(head)
            log("Creating directory {}".format(head), LOGLEVEL.DEBUG)
        except OSError:
            pass

    _path = path.abspath(path.expanduser(path.expandvars(file_path)))
    for f in state["open_files"]:
        if _path == f.name:
            return f

    _path_for_log = _path.replace(os.getcwd(), '.')
    _mode = {'r': 'READ', 'w': 'WRITE', 'a': 'APPEND'}
    log("Opening new file {} in {} mode".format(_path_for_log, _mode[mode]),
        LOGLEVEL.INFO)
    try:
        file = codecs.open(_path, mode, "utf-8")
    except IOError:
        log("Unable to open the file at {}".format(_path_for_log),
            LOGLEVEL.ERROR)

    state["open_files"].add(file)

    if mode == 'r':
        stats["in_files"] += 1
        dir_name, file_name = path.split(_path)
        if state["next_out_file"] is None:
            root, _ = path.splitext(file_name)
            next_out_file(root+'.rpy')
        state["file_chain"].append({
                "file": file,
                "file_path": _path,
                "file_dir": dir_name,
                "file_name": file_name,
                "cur_line": 0,
                "cur_indent": 0,
                "prev_indent": 0,
                "new_indent": False,
                "prev_whitespace": [],
                # "temp_dedent": [],
                "command_block": False,
                "command": (None, None),
                "blank_line": True,
                "label_chain": [],
                "next_label_call": None
            })
    else:
        stats["out_files"] += 1

    return file


def get_out_file():
    if not state["cur_out_file"]:
        state["cur_out_file"] = open_file(state["next_out_file"])

    return state["cur_out_file"]


def next_out_file(file):
    log("Seting next output file to {}".format(file), LOGLEVEL.DEBUG)
    state["next_out_file"] = file
    state["cur_out_file"] = None


def write_line(line=None, indent=True, file=None):
    _f = state["file_chain"][-1]
    if line is None:
        if not _f["blank_line"]:
            line = ''
            _f["blank_line"] = True
        else:
            return
    else:
        _f["blank_line"] = False

    log("Writing line to output", LOGLEVEL.VERB)
    file = file or get_out_file()

    if line != '' and line[-1] != '"':
        line = line.replace('\\n', '\n')

    if indent:
        _i = str(_il)
        file.write('\n'.join([_i+l.strip() for l in line.split('\n')])+'\n')
    else:
        file.write(line+'\n')

    if config["create_flow_control_file"]:
        _label = _f["next_label_call"]
        if _label:
            log("Adding label call to control file", LOGLEVEL.DEBUG)
            _f["next_label_call"] = None
            if not state["control_file"]:
                state["control_file"] = open_file("control.rpy", 'w')
                write_line("label _control:", False, state["control_file"])
            if _label[0] == '.':
                write_line("    call "+_f["label_chain"][-1]+_label,
                           False, state["control_file"])
            else:
                write_line("    call "+_label, False, state["control_file"])
        _f["next_label_call"] = None

    stats["out_lines"] += len(line.split('\n'))

##-----------------------------------------------------------------------------
## Commands
##-----------------------------------------------------------------------------

def parse_command_block(line):
    log("Parsing next line in command block", LOGLEVEL.VERB)
    _f = state['file_chain'][-1]
    _c = _f["command"]

    _m = _c[1].match(':'+_c[0]+' '+line)

    parse_command(_m.group(1), _m.groups()[0:], _c[1])


def parse_command(command, matches, _re):
    matches = [m.strip() for m in matches[1:]]
    log("Parsing command '{}' {}".format(command, matches), LOGLEVEL.DEBUG)
    stats["commands_processed"] += 1
    _f = state['file_chain'][-1]

    def _write_play(channel, sound):
        write_line("play "+channel+' '+sound)

    # ^:(line)\s*(.*?)=\s?(.*)$
    if command == "line":
        log("command: New line replacement", LOGLEVEL.DEBUG)
        line_regex(matches[0], matches[1])

    # ^:(line:)$
    elif command == "line:":
        log("command: Line replacement block", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        _f["command_block"] = True
        _f["command"] = ('line', _re)

    # ^:(character)\s*(.*?)=\s?(.*)$
    if command == "character":
        log("command: New character replacement", LOGLEVEL.DEBUG)
        character_regex(matches[0], matches[1])

    # ^:(character:)$
    elif command == "character:":
        log("command: Character replacement block", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        _f["command_block"] = True
        _f["command"] = ('character', _re)

    # ^:(:)\s+(\.?[\w\.]*)$
    # TODO: Move all of this to another function and fix it up
    # TODO: Integrate auto_return for labels with content.
    elif command == ":":
        log("command: Label", LOGLEVEL.DEBUG)
        _m = parent_label_re.match(matches[0])
        if _m and _m.groups()[0]:
            log("Parent label: {}".format(_m.group(1)), LOGLEVEL.DEBUG)
            # TODO: fix this so we write to the correct parent file if it is
            #       already open
            if config["create_parent_files"]:
                if _m.group(1) not in state["parent_labels"]:
                    log("New parent file: {}".format(_m.group(1)))
                    next_out_file(_m.group(1)+'.rpy')
                    state["parent_labels"].add(_m.group(1))

        _f["next_label_call"] = None

        write_line('label '+matches[0]+':')

        if config["create_flow_control_file"]:
            ignore = False
            for _re in config["flow_control_ignore"]:
                if _re.match(matches[0]):
                    ignore = True
                    break
            if not ignore:
                _f["next_label_call"] = matches[0]

        # Build label chain links
        # TODO: Fix this mess up
        if matches[0][0] != '.':
            _parent = matches[0].split('.')[0]
            if _parent not in _f["label_chain"]:
                _f["label_chain"].append(_parent)
                # log(_f["label_chain"])

    # ^:(sc)\s*(\w*)$
    elif command == "sc":
        log("command: Scene", LOGLEVEL.DEBUG)
        write_line('scene '+matches[0])

    # ^:(s)\s*(\w*)$
    elif command == "s":
        log("command: Show", LOGLEVEL.DEBUG)
        write_line('show '+matches[0])

    # ^:(w)\s*(\w*)$
    elif command == "w":
        log("command: With", LOGLEVEL.DEBUG)
        write_line('with '+matches[0])

    # ^:(p)\s+(.*?)\s+(.*)$
    elif command == "p":
        log("command: Play", LOGLEVEL.DEBUG)
        _write_play(matches[0], matches[1])

    # ^:(pm)\s+(.*)$
    elif command == "pm":
        log("command: Play music", LOGLEVEL.DEBUG)
        _write_play("music", matches[0])

    # ^:(ps)\s+(.*)$
    elif command == "ps":
        log("command: Play sound", LOGLEVEL.DEBUG)
        _write_play("sound", matches[0])

    # ^:(pa)\s+(.*)$
    elif command == "pa":
        log("command: Play audio", LOGLEVEL.DEBUG)
        _write_play("audio", matches[0])

    # ^:(v)\s+(.*)$
    elif command == "v":
        log("command: Voice", LOGLEVEL.DEBUG)
        write_line("voice "+matches[0])

    # ^:(q)\s+(.*?)\s+(.*)$
    elif command == "q":
        log("command: Queue", LOGLEVEL.DEBUG)
        write_line("queue "+matches[0]+' '+matches[1])

    # ^:(stop)\s*(.*)?$
    elif command == "stop":
        log("command: Stop", LOGLEVEL.DEBUG)
        write_line("stop "+matches[0])

    # ^:(c)\s*(\w*)$
    elif command == "c":
        log("command: Call", LOGLEVEL.DEBUG)
        write_line('call '+matches[0])

    # ^:(j)\s*(\w*)$
    elif command == "j":
        log("command: Jump", LOGLEVEL.DEBUG)
        # TODO: Work propper label chain into this
        write_line('jump '+matches[0])

    # ^:(r)$
    # ^:(r)\s+(.*)$
    elif command == "r":
        log("command: Return", LOGLEVEL.DEBUG)
        if len(matches) >= 1:
            write_line("return {}".format(matches[0]))
        else:
            write_line('return')

    # ^:(choice):$
    elif command == "choice":
        log("command: New menu block", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        write_line('menu:')

    # ^:(if)\s*(.*?):$
    elif command == "if":
        log("command: if statement", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        write_line('if '+matches[0]+':')

    # ^:(elif)\s*(.*?):$
    elif command == "elif":
        log("command: elif statement", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        write_line('elif '+matches[0]+':')

    # ^:(else):$
    elif command == "else":
        log("command: else statement", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        write_line('else:')

    # ^:(nvl):$
    elif command == "nvl":
        log("command: New NVL block", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        state["is_nvl_mode"] = True

    # ^:(clear)$
    elif command == "clear":
        log("command: NVL clear", LOGLEVEL.DEBUG)
        if state["is_nvl_mode"]:
            write_line("nvl clear")
        else:
            write_line()

    # ^:(import)\s*(.*)$
    elif command == "import":
        log("command: Import new file for reading", LOGLEVEL.DEBUG)
        _f = path.abspath(path.expanduser(path.expandvars(matches[0])))
        if path.isfile(_f) is False:
            log("{} is not an accessible file".format(
                matches[0]), LOGLEVEL.ERROR)
        log("Importing file {}".format(matches[0]), LOGLEVEL.INFO)
        loop_file(_f)

    # ^:(file)\s*(.*)$
    elif command == "file":
        log("command: New output file", LOGLEVEL.DEBUG)
        next_out_file(matches[0])

    # ^:(log)\s*(0|1|2|3|4|VERBOSE|DEBUG|INFO|WARN|WARNING|ERROR)\s*(.*)$
    elif command == "log":
        log("command: write to log", LOGLEVEL.VERB)
        try:
            log(matches[1], int(matches[0]))
        except ValueError:
            log(matches[1], eval("LOGLEVEL."+matches[0]))

    # ^:(config)\s*(.*?)=\s?(.*)$
    elif command == "config":
        log("command: Congiguration setting", LOGLEVEL.DEBUG)
        if matches[0] not in config:
            log("Unknown config option {}".format(matches[0]), LOGLEVEL.ERROR)

        if matches[0] == "flow_control_ignore":
            _l = []
            for v in eval(matches[1].replace(r'\"', '"')):
                _l.append(re.compile('^'+regex_prep(v)+'$'))
            config["flow_control_ignore"] = _l

        else:
            try:
                config[matches[0]] = eval(matches[1])
            except (SyntaxError, NameError):
                config[matches[0]] = matches[1]

    # ^:(config:)$
    elif command == "config:":
        log("command: Config block", LOGLEVEL.DEBUG)
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
        _f["command_block"] = True
        _f["command"] = ('config', _re)

    # ^:(break)$
    elif command == "break":
        log("Break command encountered", LOGLEVEL.INFO)
        sys.exit()

##-----------------------------------------------------------------------------
## Per line functions
##-----------------------------------------------------------------------------

def indentinator(leading_whitespace):
    log("Performing indentation management", LOGLEVEL.VERB)
    _f = state['file_chain'][-1]
    prev_ws = _f["prev_whitespace"]

    if leading_whitespace < sum(prev_ws):
        _f["command_block"] = False
        _reduce = 0
        for i in range(len(prev_ws), 0, -1):
            if leading_whitespace < sum(prev_ws[:i]):
                _reduce += 1
            else:
                break

        _f["cur_indent"] -= _reduce
        while _reduce >= 1:
            prev_ws.pop()
            if state["is_nvl_mode"]:
                state["is_nvl_mode"] -= 1
                if state["is_nvl_mode"] == 0:
                    state["is_nvl_mode"] = False
            _reduce -= 1

        if leading_whitespace != sum(prev_ws):
            log("Inconsistent indentation detected", LOGLEVEL.ERROR)

    elif leading_whitespace > sum(prev_ws):
        _f["cur_indent"] += 1
        prev_ws.append(leading_whitespace - sum(prev_ws))
        if state["is_nvl_mode"]:
            if state["is_nvl_mode"] is True:
                state["is_nvl_mode"] = 1
            else:
                state["is_nvl_mode"] += 1


def parse_line(line):
    stats["in_lines"] += 1
    _f = state["file_chain"][-1]
    log('Parsing Line: "{}"'.format(line.strip()), LOGLEVEL.VERB)

    if empty_line_re.match(line):
        write_line()
        return

    # Comments
    _m = comment_re.match(line)
    if _m:
        line = _m.group(2).rstrip()
        if line[0] == config["copy_special_comments"]:
            write_line(_m.group(1)+'#'+line, indent=False)
        else:
            log("Non-copy comment detected; skipping.", LOGLEVEL.VERB)
        return

    indentinator(len(line) - len(line.lstrip()))
    line = line.strip()

    log("Checking for indentation errors", LOGLEVEL.VERB)
    if _f["new_indent"]:
        if _f["cur_indent"] <= _f["prev_indent"]:
            log("Expecting new indent", LOGLEVEL.ERROR)
    elif _f["cur_indent"] > _f["prev_indent"]:
        log("Line is indented, but not expecting a new indent",
            LOGLEVEL.ERROR)

    _f["prev_indent"] = _f["cur_indent"]
    _f["new_indent"] = 0

    # Inside command block
    if _f["command_block"]:
        parse_command_block(line.replace('"', r'\"'))
        return

    # Commands
    log("Checking for command", LOGLEVEL.VERB)
    for i in range(len(command_list)):
        _m = command_list[i].match(line.replace('"', r'\"'))
        if _m:
            if _m.group(1) == ':' and line[-1] == ':':
                log("New indent is now expected", LOGLEVEL.VERB)
                _f["new_indent"] = 1
            parse_command(_m.group(1), _m.groups()[0:], command_list[i-1])
            return

    log("Checking for new indent", LOGLEVEL.VERB)
    if line[-1] == ':':
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1

    # $ starting python lines
    _m = python_re.match(line)
    if _m:
        log("Python line command detected", LOGLEVEL.DEBUG)
        write_line(_m.group(1))
        return

    line = line.replace('"', r'\"')

    # Line replacement
    log("Checking for line replacement", LOGLEVEL.VERB)
    for k, v in state["known_line_rep"].items():
        _m = k.match(line)
        if _m:
            log("Line replacement match", LOGLEVEL.VERB)
            stats["line_replacements"] += 1
            _s = re.sub('\\\\{|\\\\}', fix_brace, v)
            _s = _s.format(*_m.groups())
            try:
                write_line(re.sub('\xc0|\xc1', fix_brace, _s))
            except Exception as e:
                raise
                # log("Unable to replace line:\n  {}\n  {}".format(
                #     v, _m.groups()), LOGLEVEL.ERROR)
            return

    # Character Replacement
    log("Checking for character replacement", LOGLEVEL.VERB)
    for k, v in state["known_character_rep"].items():
        _m = k.match(line)
        if _m:
            log("Character replacement match", LOGLEVEL.VERB)
            _s = re.sub('\\\\{|\\\\}', fix_brace, v[0])
            if state["is_nvl_mode"]:
                _n = config["nvl_prefix"]+_s+config["nvl_suffix"]
                _line = ''.join((_n, v[1]))
            else:
                _line = ''.join(v)
            stats["character_replacements"] += 1
            stats["dialogue_lines"] += 1
            try:
                _line = _line.format(*_m.groups())
                write_line(re.sub('\xc0|\xc1', fix_brace, _line))
            except Exception as e:
                raise
                # log("Unable to replace prefix:\n  {}\n  {}".format(
                #     v[0], _m.groups()), LOGLEVEL.ERROR)
            return

    # Unknown command
    log("Checking for unknown command", LOGLEVEL.VERB)
    _m = command_re.match(line)
    if _m:
        # TODO: implement unknow command outputs
        log("Unknown command processing not yet implemented, sorry :/",
            LOGLEVEL.WARN)
        # log("Unknown command detected", LOGLEVEL.INFO)
        # # TODO: Use current indent level
        # # TODO: make use of this dict value
        # _f["unknown_block"] = True
        # # TODO: Write this function
        # write_unknown_command_block()
        # return

    # Else, its just a normal narration line
    log("Normal narration line", LOGLEVEL.VERB)
    if state["is_nvl_mode"]:
        _nvl = config["nvl_character"]+' '
    else:
        _nvl = ''

    stats["narration_lines"] += 1
    if line[-1] == ':':
        write_line(_nvl+'"{}":'.format(line[:-1]))
    else:
        write_line(_nvl+'"{}"'.format(line))

##-----------------------------------------------------------------------------
## Main execution
##-----------------------------------------------------------------------------

def main(argv):
    global _debug, log

    if not argv:
        usage("No input script file defined.")
    if '-h' in argv or '--help' in argv:
        usage()

    if len(argv) > 1:
        try:
            opts, args = getopt.getopt(argv[1:], 'ho:',
                ['help', 'output=', 'debug', 'verbose'])
        except getopt.GetoptError as e:
            usage(str(e))
    else:
        opts, args = {}, {}

    output_path = None
    _debug = 0

    if opts:
        log("Command line arguments: {}".format(opts), LOGLEVEL.VERB)
    else:
        log("No additional command line arguments detected", LOGLEVEL.VERB)

    for opt, arg in opts:
        if opt in ('-o', '--output'):
            output_path = arg
        elif opt == '--debug':
            if _debug:
                log("Can not set --debug and --verbose options simultaniously",
                    LOGLEVEL.WARN)
            else:
                _debug = 1
                log("Debug logging enabled")
        elif opt == '--verbose':
            if _debug:
                log("Can not set --debug and --verbose options simultaniously",
                    LOGLEVEL.WARN)
            else:
                _debug = 2
                log("Verbose mode is set. This can severly impact the speed "
                    "and performance of the script and may result in a huge "
                    "log file.", LOGLEVEL.WARN)

    in_file = path.abspath(path.expanduser(path.expandvars(argv[0])))

    if path.isfile(in_file) is False:
        log("{} is not an accessible file".format(argv[0]),
            LOGLEVEL.ERROR, exit = False)
        try:
            log("initializing logger", LOGLEVEL.DEBUG)
            os.chdir(path.dirname(in_file))
        except:
            log("Failed to set directory for logger", LOGLEVEL.ERROR)
        else:
            log = _Logger(_tmp_log)
            sys.exit(1)

    os.chdir(path.dirname(in_file))

    setup_globals(output_path)

    loop_file(in_file)

    sys.exit()


def cleanup():
    log("Cleaning up", LOGLEVEL.VERB)
    if state["control_file"]:
        write_line("return", False, state["control_file"])
    for f in state['open_files']:
        try:
            f.close()
        except ValueError:
            pass
    log.close()


if __name__ == "__main__":
    print(_c.r)
    log("Starting Build", LOGLEVEL.INFO)
    try:
        main(sys.argv[1:])
    except Exception:
        log.log_traceback()
    finally:
        cleanup()
