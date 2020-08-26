#!/usr/bin/env bash
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2020 Cecil Curry.
# See "LICENSE" for further details.
#
# --------------------( SYNOPSIS                          )--------------------
# Bash shell script profiling this project against comparable competitors under
# a battery of simple (albeit instructive and hopefully unbiased) tests.

# ....................{ TODO                              }....................
#FIXME: Add support for profiling "enforce", which provides a
#@runtime_validation decorator and supports Python 3.5 through Python 3.8:
#    https://pypi.org/project/enforce
#FIXME: Add support for profiling "pytypes" *AFTER* "pytypes" finally supports
#Python 3.7 through Python 3.8, which it currently does *NOT*:
#    https://github.com/Stewori/pytypes/issues/40

# ....................{ PREAMBLE                          }....................
# Enable strictness for sanity.
set -e

# Human-readable version of this profiling suite.
VERSION='0.0.1'

# Print a greeting preamble.
echo "beartype profiler [version]: ${VERSION}"

# ....................{ FUNCTIONS ~ profilers             }....................
# profile_func(
#     label: str,
#     code_setup: str,
#     code_func: str,
#     code_call: str,
# ) -> None
#
# Profile the passed snippet of Python code defining a function to be
# iteratively decorated by each runtime type checker recognized by this script
# (i.e., "beartype", "pytypes", "typeguard") and then repeatedly called by
# the passed snippet of arbitrary Python code after first running the passed
# snippet of arbitrary Python code exactly once.
function profile_callable() {
    # Validate and localize all passed arguments.
    (( $# == 4 )) || {
        echo 'Expected four arguments.' 1>&2
        return 1
    }
    local \
        label="${1}" \
        code_setup="${2}" \
        code_func="${3}" \
        code_call="${4}"

    # Print the passed label as a banner.
    print_banner "${label}"

    # Python code snippet repeatedly performing the passed function call.
    local code_call_repeat="
for _ in range(100):
    ${code_call}"

    # Print the function to be called.
    echo -e "function to be decorated with type-checking:\n${code_func}\n"

    # Print the function calls to be performed.
    echo -e "function calls to be type-checked:${code_call_repeat}\n"

    # Python code snippet importing the "beartype" decorator.
    local CODE_SETUP_BEARTYPE='from beartype import beartype
'

    # Python code snippet importing the "typeguard" decorator.
    local CODE_SETUP_TYPEGUARD='from typeguard import typechecked
'

    # Python code snippet decorating the passed function with "beartype".
    local CODE_DECOR_BEARTYPE='@beartype
'

    # Python code snippet decorating the passed function with "typeguard".
    local CODE_DECOR_TYPEGUARD='@typechecked
'

    # Profile this undecorated definition of this function as a baseline.
    profile_snippet 'decoration         [none     ]: ' \
        "${code_setup}" "${code_func}"

    # Profile the "beartype"-decorated definition of this function.
    profile_snippet 'decoration         [beartype ]: ' \
        "${CODE_SETUP_BEARTYPE}${code_setup}" \
        "${CODE_DECOR_BEARTYPE}${code_func}"

    # Profile the "typeguard"-decorated definition of this function.
    profile_snippet 'decoration         [typeguard]: ' \
        "${CODE_SETUP_TYPEGUARD}${code_setup}" \
        "${CODE_DECOR_TYPEGUARD}${code_func}"

    # Profile this undecorated definition and repeated calling of this function
    # as a baseline.
    profile_snippet 'decoration + calls [none     ]: ' \
        "${code_setup}" "${code_func}${code_call_repeat}"

    # Profile the "beartype"-decorated definition and repeated calling of this
    # function.
    profile_snippet 'decoration + calls [beartype ]: ' \
        "${CODE_SETUP_BEARTYPE}${code_setup}" \
        "${CODE_DECOR_BEARTYPE}${code_func}${code_call_repeat}"

    # Profile the "beartype"-decorated definition and repeated calling of this
    # function.
    profile_snippet 'decoration + calls [typeguard]: ' \
        "${CODE_SETUP_TYPEGUARD}${code_setup}" \
        "${CODE_DECOR_TYPEGUARD}${code_func}${code_call_repeat}"
}


# profile_snippet(label: str, code_setup: str, code_profile: str) -> None
#
# Profile the passed snippet of arbitrary Python code to be timed after first
# running the passed snippet of arbitrary Python code exactly once.
function profile_snippet() {
    # Validate and localize all passed arguments.
    (( $# == 3 )) || {
        echo 'Expected three arguments.' 1>&2
        return 1
    }
    local label="${1}" code_setup="${2}" code_profile="${3}"

    # Print the passed label *BEFORE* profiling, which (thankfully) implicitly
    # prints succinct timings after completion.
    echo -n "${label}"

    # Profile these snippets.
    command python3 -m timeit -n 100 -r 3 -s "${code_setup}" "${code_profile}"
}

# ....................{ FUNCTIONS ~ printers              }....................
# print_banner(label: str) -> None
#
# Print the passed terse human-readable string containing *NO* newlines as a
# banner message, both centered to the current terminal width and padded
# (i.e., preceded and followed) by "=" characters.
#
# See also this StackExchange answer strongly inspiring this implementation:
#     https://unix.stackexchange.com/a/267730/117478
function print_banner() {
    # Validate and localize all passed arguments.
    (( $# == 1 )) || {
        echo 'Expected one argument.' 1>&2
        return 1
    }
    local label="${1}"

    # If either:
    #
    # * Stdout (i.e., standard output) is *NOT* attached to an interactive
    #   terminal *OR*...
    # * The "tput" command is *NOT* in the current ${PATH}...
    #
    # Then print this label as is and immediately return.
    { [[ -t 1 ]] && is_command 'tput'; } || {
        echo "${label}"
        return 0
    }
    # Else, stdout is attached to an interactive terminal *AND* the "tput"
    # command is in the current ${PATH}.

    # Number of characters in this label.
    local label_len="${#label}"

    # Number of characters comprising each line of this terminal.
    local terminal_len="$(tput cols)"

    # Number of characters comprising both the prefixing and suffixing padding.
    local padding_len="$(((terminal_len - label_len - 2)/2))"

    # "=" character repeated 500 times, to be truncated below.
    local padding="$(printf '%0.1s' ={1..500})"

    # Magically print this label as a banner.
    printf '\n%*.*s %s %*.*s\n'\
        0 \
        "${padding_len}" \
        "${padding}" \
        "${label}" \
        0 \
        "${padding_len}" \
        "${padding}"
}

# ....................{ FUNCTIONS ~ testers               }....................
# is_command(command_basename: str) -> bool
#
# Report success only if a command with the passed basename is available in the
# current "${PATH}".
#
# See also this StackExchange answer strongly inspiring this implementation:
#     https://stackoverflow.com/a/46013739/2809027
function is_command() {
    # Validate and localize all passed arguments.
    (( $# == 1 )) || {
        echo 'Expected one argument.' 1>&2
        return 1
    }
    local command_basename="${1}"
    command -v "${command_basename}" >/dev/null
}

# ....................{ VERSIONS                          }....................
# Print project versions *BEFORE* profiling for disambiguity. Note that:
# * The "typeguard" package fails to explicitly publish its version, so we
#   fallback to the setuptools-based Hard Way.
echo
command python3 -c '
import beartype
print("beartype  [version]: " + beartype.__version__)'
command python3 -c '
import pkg_resources
print("typeguard [version]: " + pkg_resources.require("typeguard")[0].version)'

# ....................{ PROFILE ~ union                   }....................
profile_callable 'UNION' \
    'from typing import Union' \
    'def panther_canter(quick_foot: Union[int, str]) -> Union[int, str]:
    return quick_foot' \
    'panther_canter("We dare not wait for thee. Follow, Baloo. We must go on the quick-foot -- Kaa and I.")'
