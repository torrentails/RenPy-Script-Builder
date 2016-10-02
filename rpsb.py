#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ren'Py Script Builder takes an input script file and generates
a Ren'Py v6.99.11 compatible .rpy file(s).

Usage: "python rpsb.py input-file [-o output-dir]"
Use "--help" for more info.
"""

__version__ = "0.4.6"
__author__ = "Nathan Sullivan"
__email__ = "contact@torrentails.com"
__license__ = "MIT"

import os, sys, getopt, re, time, types, atexit

try:
    import colorama
    colorama.init()
    Fore = colorama.Fore
    Back = colorama.Back
    Style = colorama.Style
except ImportError:
    class __fake_col__():
        def __getattr__(*a,**kw):
            return ''
    Fore = __fake_col__()
    Back = Fore
    Style = Fore

class Colorama_Helper:
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

state = {
    "master_in_file":None,
    "cur_in_file":None,
    "cur_out_file":None,
    "next_out_file":None,
    "control_file":None,
    "open_files":set(),
    "known_line_rep":{},
    "known_prefix_rep":{},
    "file_chain":[],
    "parent_labels":set(),
    "is_nvl_mode":False,
    # "next_indent_is_ignored":False
}

config = {
    "create_parent_files":False,
    "create_flow_control_file":True,
    "flow_control_ignore":None,
    "copy_comments":False,
    "copy_special_comments":"#",
    "nvl_character":"NVL",
    "nvl_prefix":"",
    "nvl_suffix":"_NVL",
    "output_path":".",
    "auto_return":True
}

stats = {
    "in_files":0,
    "out_files":0,
    "in_lines":0,
    "out_lines":0,
    "commands_processed":0,
    "line_replacements":0,
    "prefix_replacements":0,
    "narration_lines":0,
    "dialogue_lines":0,
    "start_time":time.time()
}

rep_dict1 = {
    r'\{':'À',
    r'\}':'Á',
    r'\*':'Â',
    r'\+':'Ã',
    r'\?':'Ä',
    r'\\':'Å',
    '.':r'\.',
    '(':r'\(',
    ')':r'\)',
    '[':r'\[',
    ']':r'\]'
}
rep_dict2 = {
    '{':'(',
    '}':')',
    '*':'.*?',
    '+':'.+?',
    '?':'.?',
    '^':r'\^',
    '$':r'\$',
    '|':r'\|',
    'À':r'\{',
    'Á':r'\}',
    'Â':r'\*',
    'Ã':r'\+',
    'Ä':r'\?',
    'Å':r'\\'
}

rep_dict3 = {r'\{':'\xc0', r'\}':'\xc1', '\xc0':'{', '\xc1':'}',}
    # r'\\':'\xc2', '\xc2':'\\'}

command_list = [
    re.compile("^:(l)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(l:)$"),
    re.compile("^:(p)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(p:)$"),
    re.compile("^:(:)\s*(\.?.*?):?$"),
    re.compile("^:(sc)\s+(.*)$"),
    re.compile("^:(s)\s+(.*)$"),
    re.compile("^:(w)\s+(.*)$"),
    re.compile("^:(c)\s+(.*)$"),
    re.compile("^:(j)\s+(.*)$"),
    re.compile("^:(r)$"),
    re.compile("^:(m):$"),
    re.compile("^:(if)\s+(.*?):$"),
    re.compile("^:(elif)\s+(.*?):$"),
    re.compile("^:(else):$"),
    re.compile("^:(nvl):$"),
    re.compile('^:(clear)$'),
    # re.compile('^:(close)$'),
    re.compile("^:(import)\s+(.*)$"),
    re.compile("^:(file)\s+(.*)$"),
    re.compile("^:(log)\s+(0|1|2|3|4|VERBOSE|DEBUG|INFO|WARN|WARNING|ERROR)\s+(.*)$"),
    re.compile("^:(config)\s+(.*?)\s*=\s*(.*)$"),
    re.compile("^:(config:)$"),
    re.compile("^:(break)$")
]

class Current_Line_Str(object):
    def __str__(self):
        if len(state["file_chain"]):
            _f = state["file_chain"][-1]
            return "{}|{} ".format(_f["file_name"], _f["cur_line"])
        return '<init> '
    def __add__(self, other):
        if issubclass(type(other), str):
            return str(self)+other
    def __radd__(self, other):
        if issubclass(type(other), str):
            return other+str(self)
_ln = Current_Line_Str()

class LOGLEVEL:
    ERROR = 4
    WARN = 3
    WARNING = 3
    INFO = 2
    DEBUG = 1
    VERB = 0
    VERBOSE = 0

    def __getitem__(self, i):
        return ('VERBOSE', 'DEBUG', 'INFO', 'WARNING', 'ERROR')[i]

LOGLEVEL = LOGLEVEL()

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

        # self.log_display_level = self.log_save_level + 1

        self.__log = [] # copy.deepcopy(tmp_log)
        self.__log_flush_number = flush_number
        self.__log_count = 0
        _file, _ = os.path.splitext(os.path.basename(__file__))
        self.__log_file = _file+'.log'

        _log = []
        for val in tmp_log:
            if val['level'] >= self.log_save_level:
                log_string = ("<{0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}>"
                    " [{1:<8} {2}\n".format(time.localtime(val['time']),
                    LOGLEVEL[val['level']]+']', val['message']))
                _log.append(log_string)

            if LOGLEVEL.ERROR > val['level'] >= self.log_display_level:
                print _c[val['level']]+"[{:<8} {}".format(
                    LOGLEVEL[val['level']]+']',val['message'])+_c.r

        if _log:
            try:
                with open(self.__log_file, 'w') as f:
                    f.writelines(_log)
            except IOError:
                raise
                # log("Unable to open log file for writing.", LOGLEVEL.ERROR)

    def __call__(self, msg, level=LOGLEVEL.INFO, exit=True):
        if level >= self.log_save_level:
            self.__log_count += 1
        else:
            return

        cur_time = time.time()
        msg = _ln+str(msg)
        self.__log.append({'time':cur_time, 'level':level, 'message':msg})


        if LOGLEVEL.ERROR > level >= self.log_display_level:
            print _c[level]+"[{:<8} {}".format(LOGLEVEL[level]+']', msg)+_c.r

        elif level >= LOGLEVEL.ERROR:
            print _c[level]+"[{:<8} {}".format(LOGLEVEL[level]+']', msg)+_c.r
            if exit:
                sys.exit(1)

        if self.__log_count >= self.__log_flush_number:
            self.flush()

    def flush(self):
        _log = []
        for l in self.__log:
            if l['level'] >= self.log_save_level:
                log_string = ("<{0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}>"
                    " [{1:<8} {2}\n".format(time.localtime(l['time']),
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

    def stats(self, cur_time=None):
        log("Logging statistics", LOGLEVEL.VERB)
        _log = ["Statistics:"]

        def _sts(t):
            _t = reduce(lambda ll,b : divmod(ll[0],b) + \
                ll[1:], [(t*1000,),1000,60,60])
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
            "prefix_replacements",
            "narration_lines",
            "dialogue_lines"
        )
        for k in _stats_list:
            _pretty_log(k)

        _log.append("    {1:>19} : {0[3]:0>2n}:{0[4]:0>2n}:{0[5]:0>2n}".format(
            time.localtime(stats["start_time"]), "start_time"))

        cur_time = cur_time or time.time()
        _run_time = cur_time - stats["start_time"]
        _log.append("    {:>19} : {}".format("total_run_time", _sts(_run_time)))

        log('\n'.join(_log))

    def close(self):
        log("Closing logger", LOGLEVEL.DEBUG)
        self.stats(time.time())
        self.flush()

_tmp_log = []
def log(msg, level=LOGLEVEL.INFO, exit=True):
    msg = _ln+msg
    _tmp_log.append({'time':time.time(), 'level':level, 'message':msg})
    if level >= LOGLEVEL.ERROR:
        if exit:
            sys.exit(_c[level]+"[{:<8} {}".format(LOGLEVEL[level]+']', msg))
        else:
            print _c[level]+"[{:<8} {}".format(LOGLEVEL[level]+']', msg)+_c.r
def _close():
    pass
log.close = _close

def setup_globals(output_path=None, flush_number=10):
    global log, _tmp_log
    log("Initializing Globals", LOGLEVEL.DEBUG)

    output_path = output_path or '.'
    _old_output_path = output_path
    output_path = os.path.expandvars(os.path.expanduser(output_path))
    if not os.path.isdir(output_path):
        usage("Invalid output path: {}".format(_old_output_path))
    config["output_path"] = output_path

    log("initializing logger", LOGLEVEL.DEBUG)
    log = _Logger(_tmp_log, flush_number)
    del _tmp_log

    config["flow_control_ignore"] = [
        re.compile('^'+regex_prep("*_choice*")+'$'),
        re.compile('^'+regex_prep("*_ignore*")+'$')
    ]

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
    _s = re.sub('\\\\{|\\\\}|\\\\\*|\\\\\+|\\\\\?|\.|\(|\)|\[|\]', _re1, string)
    return re.sub('\{|\}|\*|\+|\?|\^|\$|\||\xc0|\xc1|\xc2|\xc3|\xc4|\xc5', _re2, _s)

def line_regex(match, replace):
    log("Building line replacement regex: {} = {}".format(match,
        replace), LOGLEVEL.DEBUG)
    _rep = regex_prep(match)
    log("Regex result: {}".format(_rep), LOGLEVEL.DEBUG)
    _m = re.compile('^'+_rep+'$')
    state["known_line_rep"][_m] = replace

def prefix_regex(match, replace):
    log("Building prefix replacement regex: {} = {}".format(match,
        replace), LOGLEVEL.DEBUG)
    _rep = regex_prep(match)
    log("Regex result: {}".format(_rep), LOGLEVEL.DEBUG)
    _m = re.compile('^'+_rep+'\s(.*)')
    state["known_prefix_rep"][_m] = (replace, ' "{}"')

def total(itter):
    _sum = 0
    for i in itter:
        _sum += len(i)
    return _sum

def usage(error=None, exit_code=None):
    log("Printing usage", LOGLEVEL.VERB)
    if error:
        exit_code = exit_code or 2
        log(error, LOGLEVEL.ERROR, exit=False)
        print ''
    print '::'+("-"*77)
    print "::   Ren'Py Script Builder"
    print '::'+("-"*77)
    print '\n  Usage:'
    print '    {} -h|source [-o:dir] [--flush=value]' \
    ' [--debug|--verbose]\n\n'.format(os.path.basename(__file__))
    print "   {:>16} :: Print this help message\n".format('[-h|--help]')
    print "   {:>16} :: Set the output directory to <dir>".format('[-o:<dir>]')
    print "   {:>16} :: NOTE: Output directory may be overwritten by config" \
        .format('[--output=<dir>]')
    print (" "*20)+"::  options set in the source file.\n"
    print "   {:>16} :: Print this help message\n".format('[-h|--help]')
    print "   {:>16} :: Set the logging level to debug".format('[--debug]')
    print "   {:>16} :: Set the logging level to verbose.".format('[--verbose]')
    print (" "*20)+":: WARNING: Verbose logging will print a lot of garbage to"
    print (" "*20)+"::  the console and create a very large log file. Only use"
    print (" "*20)+"::  this option if asked to to do so by the developer."
    sys.exit(exit_code)

def main(argv):
    global _debug

    if not argv:
        usage("No input script file defined.")
    if argv[0] in ('-h', '--help'):
        usage()

    if len(argv) > 1:
        try:
            opts, args = getopt.getopt(argv[1:], 'ho:f:',
                ['help', 'output=', 'flush=', 'debug', 'verbose'])
        except getopt.GetoptError:
            usage("Unknown option")
    else:
        opts, args = {}, {}

    output_path = None
    _flush = 10
    _debug = 0

    if opts:
        log("Parsing command line arguments", LOGLEVEL.VERB)
        log("Arguments: {}".format(opts), LOGLEVEL.VERB)
    else:
        log("No additional command line arguments detected", LOGLEVEL.VERB)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt in ('-o', '--output'):
            output_path = arg
        elif opt in ('-f', '--flush'):
            _flush = int(arg)
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
                log("Verbose mode is set. This can severly impact the speed " \
                    "and performance of the script and may result in a huge " \
                    "log file.", LOGLEVEL.WARN)

    in_file = os.path.abspath(os.path.expanduser(os.path.expandvars(argv[0])))

    if os.path.isfile(in_file) is False:
        log("{} is not an accessible file".format(argv[0]), LOGLEVEL.ERROR)

    os.chdir(os.path.dirname(in_file))

    setup_globals(output_path, _flush)

    loop_file(in_file)

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
        if not os.path.isabs(file_path):
            _, tail = os.path.split(file_path)
            if tail == file_path:
                file_path = os.path.join(config["output_path"], file_path)

        head, tail = os.path.split(file_path)
        try:
            os.makedirs(head)
            log("Creating directory {}".format(head), LOGLEVEL.DEBUG)
        except OSError:
            pass

    path = os.path.abspath(os.path.expanduser(os.path.expandvars(file_path)))
    for f in state["open_files"]:
        if path == f.name:
            return f

    _mode = {'r':'READ', 'w':'WRITE', 'a':'APPEND'}
    log("Opening new file {} in {} mode".format(file_path, _mode[mode]))
    try:
        file = open(path, mode)
    except IOError:
        log("Unable to open the file at {}".format(file_path), LOGLEVEL.ERROR)

    state["open_files"].add(file)

    if mode == 'r':
        stats["in_files"] += 1
        dir_name, file_name = os.path.split(path)
        if state["next_out_file"] is None:
            root, _ = os.path.splitext(file_name)
            next_out_file(root+'.rpy')
        state["file_chain"].append({
                "file":file,
                "file_path":path,
                "file_dir":dir_name,
                "file_name":file_name,
                "cur_line":0,
                "cur_indent":0,
                "prev_indent":0,
                "new_indent":False,
                "prev_whitespace":[],
                # "temp_dedent":[],
                "command_block":False,
                "command":(None, None),
                "blank_line":True,
                "label_chain":[]
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

    stats["out_lines"] += len(line.split('\n'))

def parse_command_block(line):
    log("Parsing next line in command block", LOGLEVEL.VERB)
    _f = state['file_chain'][-1]
    _c = _f["command"]

    _m = _c[1].match(':'+_c[0]+' '+line)

    parse_command(_m.group(1), _m.groups()[0:], _c[1])

parent_label_re = re.compile("^(\w*)\.?.*$")
def parse_command(command, matches, _re):
    matches = [m.strip() for m in matches[1:]]
    log("Parsing command '{}' {}".format(command, matches), LOGLEVEL.DEBUG)
    stats["commands_processed"] += 1
    _f = state['file_chain'][-1]

    # ^:(l)\s*(.*?)=\s?(.*)$
    if command == "l":
        log("command: New line replacement", LOGLEVEL.DEBUG)
        line_regex(matches[0], matches[1])

    # ^:(l:)$
    elif command == "l:":
        log("command: Line replacement block", LOGLEVEL.DEBUG)
        _f["command_block"] = True
        _f["command"] = ('l', _re)

    # ^:(p)\s*(.*?)=\s?(.*)$
    if command == "p":
        log("command: New prefix replacement", LOGLEVEL.DEBUG)
        prefix_regex(matches[0], matches[1])

    # ^:(p:)$
    elif command == "p:":
        log("command: Prefix replacement block", LOGLEVEL.DEBUG)
        _f["command_block"] = True
        _f["command"] = ('p', _re)

    # ^:(:)\s+(\.?[\w\.]*)$
    # TODO: Move all of this to another function and fix it up
    # TODO: Delay label writing until actuall content is output so that parent labels aren't called unessisarily in the mater file
    # TODO: Integrate auto_return for labels with content.
    elif command == ":":
        log("command: Label", LOGLEVEL.DEBUG)
        _m = parent_label_re.match(matches[0])
        if _m and _m.groups()[0]:
            log("Parent label: {}".format(_m.group(1)), LOGLEVEL.DEBUG)
            # TODO: fix this so we write to the correct parent file if it is already open
            if config["create_parent_files"]:
                if _m.group(1) not in state["parent_labels"]:
                    log("New parent file: {}".format(_m.group(1)))
                    next_out_file(_m.group(1)+'.rpy')
                    state["parent_labels"].add(_m.group(1))

        write_line('label '+matches[0]+':')

        # Build label chain links
        # TODO: Fix this mess up
        if matches[0][0] != '.':
            if matches[0].split('.')[0] not in _f["label_chain"]:
                _f["label_chain"].append(matches[0].split('.')[0])
                # log(_f["label_chain"])

        if config["create_flow_control_file"]:
            ignore = False
            for _re in config["flow_control_ignore"]:
                if _re.match(matches[0]):
                    ignore = True
                    break
            if not ignore:
                log("Adding label call to control file", LOGLEVEL.DEBUG)
                if not state["control_file"]:
                    state["control_file"] = open_file("control.rpy", 'w')
                    write_line("label _control_:", False, state["control_file"])
                if matches[0][0] == '.':
                    # print state["parent_labels"]
                    write_line("    call "+_f["label_chain"][-1]+matches[0],
                        False, state["control_file"])
                else:
                    write_line("    call "+matches[0], False, state["control_file"])

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
    elif command == "r":
        log("command: Return", LOGLEVEL.DEBUG)
        write_line('return')

    # ^:(m):$
    elif command == "m":
        log("command: New menu block", LOGLEVEL.DEBUG)
        write_line('menu:')

    # ^:(if)\s*(.*?):$
    elif command == "if":
        log("command: if statement", LOGLEVEL.DEBUG)
        write_line('if '+matches[0]+':')

    # ^:(elif)\s*(.*?):$
    elif command == "elif":
        log("command: elif statement", LOGLEVEL.DEBUG)
        write_line('elif '+matches[0]+':')

    # ^:(else):$
    elif command == "else":
        log("command: else statement", LOGLEVEL.DEBUG)
        write_line('else:')

    # ^:(nvl):$
    elif command == "nvl":
        log("command: New NVL block", LOGLEVEL.DEBUG)
        state["is_nvl_mode"] = True
        # state["next_indent_is_ignored"] = True

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
        _f = os.path.abspath(os.path.expanduser(os.path.expandvars(matches[0])))
        if os.path.isfile(_f) is False:
            log("{} is not an accessible file".format(matches[0]), LOGLEVEL.ERROR)
        loop_file(in_file)

    # ^:(file)\s*(.*)$
    elif command == "file":
        log("command: New output file", LOGLEVEL.DEBUG)
        next_out_file(matches[0])

    # ^:(log)\s*(0|1|2|3|4|VERBOSE|DEBUG|INFO|WARN|WARNING|ERROR)\s*(.*)$
    elif command == "log":
        log("command: write to log", LOGLEVEL.VERB)
        try:
            log(matches[1], matches[0])
        except ValueError:
            log(matches[1], eval("LOGLEVEL."+matches[0]))

    # ^:(config)\s*(.*?)=\s?(.*)$
    elif command == "config":
        log("command: Congiguration setting", LOGLEVEL.DEBUG)
        if matches[0] not in config:
            log("Unknown config option {}".format(matches[0]), LOGLEVEL.ERROR)

        if matches[0] == "flow_control_ignore":
            _l = []
            print matches[1]
            for v in eval(matches[1].replace(r'\"', '"')):
                _l.append(re.compile('^'+regex_prep(v)+'$'))
            config["flow_control_ignore"] = _l

        else:
            try:
                config[matches[0]] = eval(matches[1])
            except SyntaxError:
                config[matches[0]] = matches[1]

    # ^:(config:)$
    elif command == "config:":
        log("command: Config block", LOGLEVEL.DEBUG)
        _f["command_block"] = True
        _f["command"] = ('config', _re)

    # ^:(break)$
    elif command == "break":
        log("Break command encountered", LOGLEVEL.WARN)
        sys.exit()

class Indent_Level_Str(object):
    def __str__(self):
        if state["is_nvl_mode"] is False:
            return '    '*state["file_chain"][-1]["cur_indent"]
        return '    '*(state["file_chain"][-1]["cur_indent"]-1)
    def __add__(self, other):
        if issubclass(type(other), str):
            return str(self)+other
    def __radd__(self, other):
        if issubclass(type(other), str):
            return other+str(self)
_il = Indent_Level_Str()

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

def fix_brace(matchobj):
    _m = matchobj.group(0)
    if _m in rep_dict3:
        return rep_dict3[_m]
    else:
        log("Failed to match {}".format(_m), LOGLEVEL.WARN)
        return _m

empty_line_re = re.compile("^\s*$")
comment_re = re.compile("^(\s*)#(.*)$")
python_re = re.compile("^(\$.*)$")
command_re = re.compile("^:(.*)$")
label_or_nvl_re = re.compile("^:(:.*?|nvl):?$")
def parse_line(line):
    stats["in_lines"] += 1
    _f = state["file_chain"][-1]
    log("Parsing Line:\n{:>5}|{}".format(
        _f["cur_line"], line.strip()), LOGLEVEL.VERB)

    if empty_line_re.match(line):
        write_line()
        return

    # Comments
    _m = comment_re.match(line)
    if _m:
        line = _m.group(2).rstrip()
        if line[0] == config["copy_special_comments"]:
            write_line(_m.group(1)+'#'+line, indent=False)
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

    log("Checking for new indent", LOGLEVEL.VERB)
    if line[-1] == ':':
        log("New indent is now expected", LOGLEVEL.VERB)
        _f["new_indent"] = 1
    else:
        _f["new_indent"] = 0

    # Inside command block
    if _f["command_block"]:
        parse_command_block(line.replace('"', r'\"'))
        return

    # $ starting python lines
    _m = python_re.match(line)
    if _m:
        write_line(_m.group(1))

    line = line.replace('"', r'\"')

    # Commands
    log("Checking for command", LOGLEVEL.VERB)
    for i in range(len(command_list)):
        _m = command_list[i].match(line)
        if _m:
            parse_command(_m.group(1), _m.groups()[0:], command_list[i-1])
            return

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
                log("Unable to replace line:\n  {}\n  {}".format(
                    v, _m.groups()), LOGLEVEL.ERROR)
            return

    # Prefix Replacement
    log("Checking for prefix replacement", LOGLEVEL.VERB)
    for k, v in state["known_prefix_rep"].items():
        _m = k.match(line)
        if _m:
            log("Prefix replacement match", LOGLEVEL.VERB)
            _s = re.sub('\\\\{|\\\\}', fix_brace, v[0])
            if state["is_nvl_mode"]:
                _n = config["nvl_prefix"]+_s+config["nvl_suffix"]
                _line = ''.join((_n, v[1]))
            else:
                _line = ''.join(v)
            stats["prefix_replacements"] += 1
            stats["dialogue_lines"] += 1
            try:
                _line = _line.format(*_m.groups())
                write_line(re.sub('\xc0|\xc1', fix_brace, _line))
            except Exception as e:
                log("Unable to replace prefix:\n  {}\n  {}".format(
                    v[0], _m.groups()), LOGLEVEL.ERROR)
            return

    # Unknown command
    log("Checking for unknown command", LOGLEVEL.VERB)
    _m = command_re.match(line)
    if _m:
        # TODO: implement unknow command outputs
        log("Unknown command processing not yet implemented, sorry :/", LOGLEVEL.WARN)
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
    atexit.register(cleanup)
    print _c.r
    log("Starting Build", LOGLEVEL.INFO)
    try:
        main(sys.argv[1:])
    except Exception as e:
        raise
    else:
        log("Done!", LOGLEVEL.INFO)
        sys.exit()
