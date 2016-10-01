Ren'py script builder
=====================

Introduction
------------

The Ren'py script builder was formed out a desire almost entirely to not have to type "" on every damn line!
Most of the ideas pretty much grew from that and having to work around writing scripts without quotation marks while still maintaining the basic level of flexibility that Ren'py offers.

The builder will take more manageable, human readable/writable script file(s) and turn them into something Ren'py can understand. Not that Ren'py scripts aren't human readable, but the goal is simply to cut down on some of the tediousness of writing dialogue and narration in the format that Ren'py requires.

Please keep in mind that this tool is only intended to help speed up the actual _script_ part of your game (the dialogue and narration and stuff). You should still do the more programming intensive stuff, such as init and gui programming in pure rpy.

[TOC]

Usage
-----
To convert a script file into a .rpy file(s), download the rpy_script_builder.py file to the location of your choice then start up a cmd or bash shell in that directory then run `python rpy_script_builder.py file_name` where `file_name` is the path to the file that you wish to convert.

The file(s) will be output in a location relative to the source document (by default, this will be in the same directory as the input file's path). This can be changed by setting `output_path` (see [Configuration](#configuration)).

What it Does
------------

the builder takes the input file and goes over it, reading each line and deciding what to do with it:

+ Empty lines are ignored.
+ Any line starting with a `#` is a [comment](#comments) and is ignored.
+ If the line starts with a `:` it is interpreted as a [command](#commands).
  + If the command is a known command or matches a [line replacement](#replacement) then it is interpreted and output.
  + Otherwise, the command (and any block it opens) is copied verbatim, sans the leading `:`.
+ A line starting with any of the [special characters](#special) are treated accordingly.
+ Finally, if a line doesn't match any of the above requirements, it is first checked for any [prefix replacements](#replacement). Any portion of the line that isn't prefix replaced is wrapped in quotes (first escaping any pre-exiting quotes to preserve them) and output.

Comments
--------

Any line beginning with a `#` is treated as a comment and is skipped over during parsing.
**Note:** Unlike python, the `#` is not treaded as a comment when it appears in the midle of a line. It must be at the beginning of the line to be treated as such.

By default, only lines starting with `##` are copied to the output and all other comments are simply ignored.
See [Configuration](#configuration)

Blocks
------

A `:` at the end of a line, opens a new block.
Blocks are indented in the same way as python and are closed in the same way.

Commands
--------

Any line starting with a `:` is a command.
The command is between the the `:` and the first space or trailing `:`

Any command not recognized by the interpreter is simply transposed as is into the output file, sans the leading `:`. Any block that is opened by this unknown command is also transposed as is.
You can use this output pure code into the output file.

```python
:init python:
    chars = ["Sarah", "George"]
    new_chars = []
    for char in chars:
        new_chars.append(char + "_happy")
```

### Line and Prefix Replacement {#replacement}

```html
:l find = replace
:p find_prefix = replace

:l:
    find = replace
    ...
:p:
    find_prefix = replace
    ...
```

These commands focus on replacing certain elements in each line.

- `:l find = replace` defines a line replacement; if an entire line comprises of `find` it will be replaced by `replace`

    Example:
    `:l tr_fade = with Fade(0.33)` will look for lines that consist only of `tr_fade` and replace that line with `with Fade(0.33)` in the output.
- `:p find = replace` defines a prefix replacement. The interpreter scanst the ginning of the line, looking for `find` followed by a space and replaces it with `replace`.
    Use this for character prefixes on spoken script lines.

    Example:
    `:p m: = Mick` will look at the beginning of each line and replace `m:` with `Mick` before quoting the rest of the string so that `m: Hello, World!` becomes `Mick "Hello, World!"` in the output.

To define multiple replacements in a single go, you can instead place a `:` at the end of the command and list your replacements in a block following it. Example:

```html
:l:
    tr_dis = with dissolve
    tr_fade = with Fade(0.75)
    park = scene bg park

:p:
    d: = David
    a: = Annie
```

You can specify multi-line replacements using `{n}`
```html
:l dorm = scene bg dorm{n}with dissolve
```
becomes
```python
scene bg dorm
with dissolve
```

Substitutions are quite flexible and can even be used to create new commands and/or replace otherwise odd strings.
```html
:l:
    :dance = $ dance_func()
    >> {+} = scene {}{n}with time_skip_short
    >>> {+} = scene {}{n}with time_skip_long
```

#### Wild card Matches and Regex {#wildcards}

Wild cards can be used to match slightly varying strings.

- `?` will match 1 or 0 characters
  `:l some?thing` will match `something` and `some_thing` but not `some other thing`
- `*` will match any number of character, including 0
  `:l some*thing` will match each of `something`, `some_thing` and `some other thing`
- `+` will match any number of character but will always match at least 1.
  `:l some+thing` will match `some_thing` and `some other thing` but not `something`

You can use `{}` to capture a wild card match and substitute it into the output using `{}` where n is the matched group. **Note:** This is different than in python, where `()` are normally used to capture matches, instead here, `{}` are used.
```html
:l dis({+}) = with Dissolve({})
dis(0.75)
```
becomes
```python
with Dissolve(0.75)
```

Substitutions will match in order, so `:l foo{*}bar{*} = $ some_func({},{})` will substitute the first parameter with the match following `foo` and the second parameter will be substituted with the match following `bar`

You can control this behavior by using numbered substitutions in the replacement string `{n}` where `n` is the match group.
Using the above example `:l foo{*}bar{*} = $ some_func({0},{1})` now substitutes the first parameter with the match following bar and the second with the match following foo.
**Note:** Substitutions are zero indexed as in python, so `{0}` is the first match, `{1]` is the second and so on.

If you need to have any of `?*+{}` or `\` in your match string, you must prefix it with a `\`. The same goes for if you wish to have `{}` or `\` in your replacement string.

### Labels

```html
::label_name
::label_name:
    ...
```

The label command can be used to add labels to each section of your script and is used as such:
`::label`

you can also specify sub labels using standard dot notation: `::.sub`
This will group the label under the most recent parent label.

Sub labels can be grouped under a specified parent label however by using `::parent.sub`

```html
::parent1
::.sub1
This sub1 label is grouped under parent1
::parent2.sub1
This sub1 label is instead grouped under parent2
::.sub2
This is part of parent2
::parent1.sub2
This label is listed under parent1 again
```
becomes
```python
label parent1
    label .sub1
        "This sub1 label is grouped under parent1"

label parent2
    label .sub1
        "This sub1 label is instead grouped under parent2"

    label .sub2
        "This is part of parent2 too"

label parent1.sub2
    "This label is listed under parent1 again"
```

**Note:** The label command doesn't need to open a new block with a trailing `:` and it is optional to include it or not if you find the layout better. If you do include the trailing `:` then the following lines must be indented as a block. The output will be the same regardless if you use labels as block openers or not and you can mis and match.

```html
::non-block
The label here doesn't open a block and so this line shouldn't be indented.

::block:
    The label here does open a block and so this line must be indented.
    ::.mix
    You can also mix block/non-block types just fine.
    Just as long as you maintain correct indenting.
```

### Scene, Show and With {#scene-show-with}

```html
:sc scene_name
:s image_name
:w transition
```

To show a new scene, simply use `:sc scene_name` where `scene_name` is the name of the new scene to show.
Likewise, use `:s image_name` to show an image (typically a character) on screen. You can even use `at location` as you would normally like `:s emily annoyed at right`

Transitions can easily be done also using `:w transition` where `transition` is the transition to perform
```html
:sc town night
:w Dissolve(1.25)
```

### Flow control

```html
:c label_name
:j label_name
:r
```

Having labels is all well and good, but a large part of Ren'py is being able to move control from one place to the next.
This is typically done in two ways: the `jump` keyword and the `call` keyword.

In your script, these are replaced by `:j` and `:c` respectfully and otherwise operate the same way.

When calling another label though, it is expected to `return` at the end of the called label. To do this in your script, just use `:r`

### Choices

```html
:m:
```

Choices are an important part of almost any visual novel and in Ren'py this is accomplished through the `menu:` keyword.

The choice dialogue is crafted in the same way as in Ren'py using `:m`
```html
:m:
    d: This is a bit of dialogue accompanying the choice
    This is the first choice:
        :c choice1
    This is the second choice:
        :c choice2
```
becomes
```python
menu:
    DAVID "This is a bit of dialogue accompanying the choice"
    "This is the first choice":
        call choice1
    "This is the second choice":
        call choice2
```

### if, elif and else {#if-else}

```html
:if condition:
:elif condition:
:else:
```

If, elif and else are used in exactly the same way as in Ren'py but must be prefixed with a `:`.

### NVL

```html
:nvl:
:clear
:close
```

`:nvl` begins an nvl block. Each script line has `NVL` as the character and each prefixed script line has `_NVL` appended to the replaced prefix.

```html
:nvl:
    This is an NVL block of text.
    As opposed to the typical ADV style that most script lines are read as.
    a: It sure is!
```
will become:
```python
NVL "This is an NVL block of text."
NVL "As opposed to the typical ADV style that most script lines are read as."
Annie_NVL "It sure is!"
```

To clear the NVL dialogue box, simply use `:clear` inside the NVL block. `:clear` will have no effect when used outside of an NVL block.

You can change the NVL character, NVL suffix and/or prefix using the [`:config` command](#configuration)

### Import

```html
:import file_name
```

For large games, you want to keep your source script separated into different files, perhaps to keep different arcs or paths in your story separate, or this might be useful when you have multiple writers, each working on a different portion of the script.
Whatever the case, the `:import file_name` command (where `file_name` is the relative path to the file to be imported) will pull all these files together.

When called, the `:import` statement will stop parsing the current file at that point, open the new file, parse all of its contents (respecting any further imports) and then return to the importing file, continuing where it left off.
Thus the position and order of your import commands are important.

If you wish to import multiple files in a row, you must specify an `:import` statement for each one.

### File

```html
:file file_name
```

You can specify that a new file be created at any point you like, provided you aren't inside of a block.
To do this use the `:file file_name` command where `file_name` is the file name to use. If the file extension if left off then `.rpy` is appended before creating the file.

When you create a new file, all output from that point onward, until the end of the script, the next `:file` command is encountered or the next parent label is encountered (providing `create_parent_files` is set to `True`).

### Logging

```html
:log level message
:break
```

You can log an output to the log file and/or console window by using the `:log level message` command, where `level` is an integer from the table below and `message` is the message to log.

The `:break` command can be used to cease execution of the script builder at that point.

#### Log Levels {#log-levels-def}
| int | Logging Level |
|:---:|:------------- |
| `0` | VERBOSE       |
| `1` | DEBUG         |
| `2` | INFO          |
| `3` | WARNING       |
| `4` | ERROR         |

Special Characters {#special}
------------------

The interpreter respects a few special characters from Ren'py:

+ `$` placed at the beginning of a line, treats that line a python line just as Ren'py does and simply copies the line directly to the output.
+ `#` begins a comment and is ignored during parsing.
  You can force the interpreter to copy comments to the output by setting `copy_comments` to `True`
  By default, a line starting with `##` _will_ be copied over, regardless of the `copy_comments` setting.

Configuration
-------------

```html
:config option = value
:config:
    option = value
    ...
```

Some things can be configured about the script interpreter itself. This is done through the use of the `:config opt = val` command where `opt` is the configuration option to change and `val` is the new value.
You can also use `:config:` as a block to set multiple configuration options at once.

Although you can change configuration option at any point in the source script, and may be occasionally desirable to do so, it is often wisest to do all configuration at the very beginning of the script to avoid unexpected behavior.

### List of Config Options {#config-list}

The following are the available configuration options and their associated default values.

+ `create_parent_files = False`
  If set to `True` then the interpreter will create new files based on each parent label (labels without at least one leading `.`) and will place all sub labels under a parent label in that parent label's file.
  It will be likely that, unless you are making a kinetic novel, you will need to edit this file after the interpreter has run.
+ `create_flow_control_file = True`
  When set to `True` a master flow control file will be created, which will call each label in the order that they appear, respecting the `flow_control_ignore` list. Set this to `False` if you want to do this manually.
+ `flow_control_ignore = ["*.choice*", "*_ignore*"]`
  A list of label names to ignore when generating the master flow control file. Regex like matches can be used as defined in the section [Wild card Matches](#wildcards).
+ `copy_comments = False`
  When set to `True` comments in the source document will be copied as is to the output.
+ `copy_special_comments = "#"`
  When set to a string, comments beginning with that string will be copied as is to the output, regardless of the `copy_comments` setting.
  By default, any line begging with `##` will be copied to the output, and other comments will simply be ignored.
+ `nvl_character = "NVL"`
  Sets the character used for the NVL narrator.
+ `nvl_prefix = ""`
  Set the prefix applied to character names during NVL blocks.
+ `nvl_suffix = "_NVL"`
  Set the suffix applied to character names during NVL blocks.
+ `output_path = "."`
  Set the relative or absolute output path for the generated script files. The default `"."` will create the files in the same location as your script file.

Syntax Reference {#syntax}
----------------

### Comments

| key | Definition |
|:--- |:---------- |
| `#` | Comment |
| `##` | Comment (copied to output) |

### Commands

| key | Definition |
|:--- |:---------- |
| `:` | Start command |
| `:l find = replace` | Entire line find and replace |
| `:l:` | Entire line find and replace (multiple) |
| `:p find = replace` | Prefix find and replace |
| `:p:` | Prefix find and replace (multiple) |
| `::label_name` | Label |
| `:sc scene` | Show scene |
| `:s image` | Show image |
| `:w transition` | With transition |
| `:c label` | Call label |
| `:j label` | Jump to label |
| `:r` | Return |
| `:m:` | Create menu dialogue |
| `:if condition:` | if statement |
| `:elif condition:` | elif statement |
| `:else:` | else statement |
| `:nvl:` | Opens and NVL block |
| `:clear` | outputs an `nvl clear` statement |
| `:import file_name` | Import and parse another file |
| `:file file_name` | Set a new output file |
| `:log level message` | Log a message at a given level to the console and/or log file |
| `:break` | Stops execution of the script builder at that point |
| `:config option = value` | Change the value of a config option |
| `:config:` | Set multiple config options at once |
| `:UNKNOWN` | Unknown commands (and any blocks they open) are output as is |

### Wildcards

| key | Definition |
|:---:|:---------- |
| `?` | Matches 1 or 0 characters |
| `*` | Matches 0 or more characters |
| `+` | Matches 1 or more characters |
| `{}` | Captures match for replacement in the output string |
| `\` | Escape wildcard characters |

### Config Options

| key | Default | Definition |
|:--- |:------- |:---------- |
|`create_parent_files`|`False`|If `True`, create files based on parent labels|
|`create_flow_control_file`|`True`|If `True`, create a master flow control file|
|`flow_control_ignore`|`["*.choice*", "*_ignore*"]`|A list of label names to ignore when generating the master flow control file.|
|`copy_comments`|`False`|If `True`, copy all comments to the output|
|`copy_special_comments`|`"#"`|Comments starting with this string, will always be copied to the output. Disabled if set to `None`|
|`nvl_character`|`"NVL"`|The character used for the NVL narrator|
|`nvl_prefix`|`""`|The prefix applied to character names during NVL blocks|
|`nvl_suffix`|`"_NVL"`|The suffix applied to character names during NVL blocks|
|`output_path`|`"."`|The output path for generated files|

### Log Levels

| int | Logging Level |
|:---:|:------------- |
| `0` | VERBOSE       |
| `1` | DEBUG         |
| `2` | INFO          |
| `3` | WARNING       |
| `4` | ERROR         |

Example
-------

Input file: ./sample.script
```html
:config:
    output_path = ./scripts
    create_flow_control_file = False

:l >> {+} = scene {}\nwith time_skip_transition

:p:
    a: = ADAM
    b: = BETH
    c: = CHARLES

# This is a comment, and won't be written to the output.
## This comment will though.

::Act_1
::.scene_01:
    :sc tiny_office
    :w Fade(1.25)
    The rain fell heavy on the window as I worked.
    a: I think I need a break.
    I leaned back in my chair, the monitor glowing softly in font of me.
    Suddenly I heard a knock at the door to my tiny office.
    a: Come in. The door's unlocked.
    I turned to face the wooden door as it opened, revealing a familiar face.
    b: Hi Adam, how's the script going?
    a: It's going well, I've made some great progress!
    a: I'm just taking a bit of break at the moment.
    Beth smiled cheekily. Something was up.
    b: Well if you're not busy, perhaps you'd like to meet someone?
    b: You'll like him, I'm sure!
    a: *sigh* Sure, I don't see why not.
    I got up and grabbed my jacket and headed out the door with the waiting Beth.
    :r

::.scene_02:
    >> office_reception
    Standing before me is man in a sharp suit.
    He almost looks out of place amongst the small, casually dressed team we have.
    Upon seeing me, he extends a hand which I take.
    His grasp is firm as he give my had a shake.
    c: The name's Charles!
    c: I work for Big Name Publishings and we're very interested in the work you and your team have done making visual novels.

    :m:
        c: We'd like to offer you a lucrative publishing deal for your upcoming games.
        Accept the offer:
            :j .accept
        Reject him:
            :j .reject

::.accept:
    An opportunity like this only comes around once in a life time!
    a: I'm honoured, of course we'd all be happy to!
    b: See, I told you you'd like him!
    >> success
    We accepted their deal and became a big name in the industry.
    We decided to all take a big holiday in Japan to celebrate.
    THE END
    :r

::.reject:
    This deal would just mean loss of our creative freedom that we've become known for.
    a: Thank you Charles for the offer...
    a: But we pride ourselves on our independence and creative freedom.
    a: So I'm going to have to turn you down, sorry.
    c: I completely understand, thank you for your time.
    b: Aw, I really though this would work.
    >> great_games
    Despite not having a lot of budget for our small studio, by sticking to our values we produced many fine games!
    THE END
    :r

```
Output file: ./scripts/sample.rpy
```python
## This comment will though.

label Act_1:
label .scene_01:
    scene tiny_office
    with Fade(1.25)
    "The rain fell heavy on the window as I worked."
    ADAM "I think I need a break."
    "I leaned back in my chair, the monitor glowing softly in font of me."
    "Suddenly I heard a knock at the door to my tiny office."
    ADAM "Come in. The door's unlocked."
    "I turned to face the wooden door as it opened, revealing a familiar face."
    BETH "Hi Adam, how's the script going?"
    ADAM "It's going well, I've made some great progress!"
    ADAM "I'm just taking a bit of break at the moment."
    "Beth smiled cheekily. Something was up."
    BETH "Well if you're not busy, perhaps you'd like to meet someone?"
    BETH "You'll like him, I'm sure!"
    ADAM "*sigh* Sure, I don't see why not."
    "I got up and grabbed my jacket and headed out the door with the waiting Beth."
    return

label .scene_02:
    scene office_reception
    with time_skip_transition
    "Standing before me is man in a sharp suit."
    "He almost looks out of place amongst the small, casually dressed team we have."
    "Upon seeing me, he extends a hand which I take."
    "His grasp is firm as he give my had a shake."
    CHARLES "The name's Charles!"
    CHARLES "I work for Big Name Publishings and we're very interested in the work you and your team have done making visual novels."

    menu:
        CHARLES "We'd like to offer you a lucrative publishing deal for your upcoming games."
        "Accept the offer":
            jump .accept
        "Reject him":
            jump .reject

label .accept:
    "An opportunity like this only comes around once in a life time!"
    ADAM "I'm honoured, of course we'd all be happy to!"
    BETH "See, I told you you'd like him!"
    scene success
    with time_skip_transition
    "We accepted their deal and became a big name in the industry."
    "We decided to all take a big holiday in Japan to celebrate."
    "THE END"
    return

label .reject:
    "This deal would just mean loss of our creative freedom that we've become known for."
    ADAM "Thank you Charles for the offer..."
    ADAM "But we pride ourselves on our independence and creative freedom."
    ADAM "So I'm going to have to turn you down, sorry."
    CHARLES "I completely understand, thank you for your time."
    BETH "Aw, I really though this would work."
    scene great_games
    with time_skip_transition
    "Despite not having a lot of budget for our small studio, by sticking to our values we produced many fine games!"
    "THE END"
    return
```