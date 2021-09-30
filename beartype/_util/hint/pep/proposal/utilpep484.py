#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
Project-wide :pep:`484`-compliant type hint utilities.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ IMPORTS                           }....................
import typing
from beartype.roar import (
    BeartypeDecorHintForwardRefException,
    BeartypeDecorHintPep484Exception,
)
from beartype._data.hint.pep.sign.datapepsigncls import HintSign
from beartype._data.hint.pep.sign.datapepsigns import (
    HintSignGeneric,
    HintSignNewType,
)
from beartype._data.hint.pep.sign.datapepsignset import HINT_SIGNS_UNION
from beartype._util.py.utilpyversion import (
    IS_PYTHON_AT_LEAST_3_10,
    IS_PYTHON_AT_LEAST_3_7,
)
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.cls.utilclstest import is_type_subclass
from types import FunctionType
from typing import Any, Generic, Optional, Tuple, TypeVar

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ HINTS                             }....................
HINT_PEP484_TUPLE_EMPTY = Tuple[()]
'''
:pep:`484`-compliant empty fixed-length tuple type hint.
'''


# Conditionally define the "typing.ForwardRef" superclass depending on the
# current Python version. This superclass was thankfully publicized under
# Python >= 3.7 after its initial privatization under Python <= 3.6.
HINT_PEP484_FORWARDREF_TYPE: Any = (
    typing.ForwardRef if IS_PYTHON_AT_LEAST_3_7 else
    typing._ForwardRef  # type: ignore [attr-defined]
)
'''
:pep:`484`-compliant **forward reference type** (i.e., class of all forward
reference objects implicitly created by all :mod:`typing` type hint factories
when subscripted by a string).
'''

# ....................{ TESTERS ~ ignorable               }....................
def is_hint_pep484_ignorable_or_none(
    hint: object, hint_sign: HintSign) -> Optional[bool]:
    '''
    ``True`` only if the passed object is a :pep:`484`-compliant **ignorable
    type hint,** ``False`` only if this object is a :pep:`484`-compliant
    unignorable type hint, and ``None`` if this object is *not* `PEP
    484`_-compliant.

    Specifically, this tester function returns ``True`` only if this object is
    a deeply ignorable :pep:`484`-compliant type hint, including:

    * A parametrization of the :class:`typing.Generic` abstract base class
      (ABC) by one or more type variables. As the name implies, this ABC is
      generic and thus fails to impose any meaningful constraints. Since a type
      variable in and of itself also fails to impose any meaningful
      constraints, these parametrizations are safely ignorable in all possible
      contexts: e.g.,

      .. code-block:: python

         from typing import Generic, TypeVar
         T = TypeVar('T')
         def noop(param_hint_ignorable: Generic[T]) -> T: pass

    * The :func:`NewType` closure factory function passed an ignorable child
      type hint. Unlike most :mod:`typing` constructs, that function does *not*
      cache the objects it returns: e.g.,

      .. code-block:: python

         >>> from typing import NewType
         >>> NewType('TotallyNotAStr', str) is NewType('TotallyNotAStr', str)
         False

      Since this implies every call to ``NewType({same_name}, object)`` returns
      a new closure, the *only* means of ignoring ignorable new type aliases is
      dynamically within this function.
    * The :data:`Optional` or :data:`Union` singleton subscripted by one or
      more ignorable type hints (e.g., ``typing.Union[typing.Any, bool]``).
      Why? Because unions are by definition only as narrow as their widest
      child hint. However, shallowly ignorable type hints are ignorable
      precisely because they are the widest possible hints (e.g.,
      :class:`object`, :attr:`typing.Any`), which are so wide as to constrain
      nothing and convey no meaningful semantics. A union of one or more
      shallowly ignorable child hints is thus the widest possible union,
      which is so wide as to constrain nothing and convey no meaningful
      semantics. Since there exist a countably infinite number of possible
      :data:`Union` subscriptions by one or more ignorable type hints, these
      subscriptions *cannot* be explicitly listed in the
      :data:`HINTS_REPR_IGNORABLE_SHALLOW` frozenset. Instead, these
      subscriptions are dynamically detected by this tester at runtime and thus
      referred to as **deeply ignorable type hints.**

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as this tester is only safely callable
    by the memoized parent
    :func:`beartype._util.hint.utilhinttest.is_hint_ignorable` tester.

    Parameters
    ----------
    hint : object
        Type hint to be inspected.
    hint_sign : HintSign
        **Sign** (i.e., arbitrary object uniquely identifying this hint).

    Returns
    ----------
    Optional[bool]
        Either:

        * If this object is :pep:`484`-compliant:

          * If this object is a ignorable, ``True``.
          * Else, ``False``.

        * If this object is *not* :pep:`484`-compliant, ``None``.
    '''

    # Avoid circular import dependencies.
    from beartype._util.hint.utilhinttest import is_hint_ignorable
    from beartype._util.hint.pep.utilpepget import (
        get_hint_pep_args,
        get_hint_pep_origin_or_none,
    )
    # print(f'Testing PEP 484 hint {repr(hint)} [{repr(hint_sign)}] deep ignorability...')

    # If this hint is a PEP 484-compliant generic...
    if hint_sign is HintSignGeneric:
        # print(f'Testing generic hint {repr(hint)} deep ignorability...')
        # If this generic is the "typing.Generic" superclass directly
        # parametrized by one or more type variables (e.g.,
        # "typing.Generic[T]"), return true.
        #
        # Note that we intentionally avoid calling the
        # get_hint_pep_type_isinstanceable_or_none() function here, which has been
        # intentionally designed to exclude PEP-compliant type hints
        # originating from "typing" type origins for stability reasons.
        if get_hint_pep_origin_or_none(hint) is Generic:
            # print(f'Testing generic hint {repr(hint)} deep ignorability... True')
            return True
        # Else, this generic is *NOT* the "typing.Generic" superclass directly
        # parametrized by one or more type variables and thus *NOT* an
        # ignorable non-protocol.
        #
        # Note that this condition being false is *NOT* sufficient to declare
        # this hint to be unignorable. Notably, the type origin originating
        # both ignorable and unignorable protocols is "Protocol" rather than
        # "Generic". Ergo, this generic could still be an ignorable protocol.
        # print(f'Testing generic hint {repr(hint)} deep ignorability... False')
    # Else, this hint is *NOT* a generic.
    #
    # If this hint is a new type, return true only if this new type aliases an
    # ignorable child type hint.
    elif hint_sign is HintSignNewType:
        return is_hint_ignorable(get_hint_pep484_newtype_class(hint))
    # Else, this hint is *NOT* a new type.
    #
    # If this hint is a union, return true only if one or more child hints of
    # this union are recursively ignorable. See the function docstring.
    elif hint_sign in HINT_SIGNS_UNION:
        return any(
            is_hint_ignorable(hint_child)
            for hint_child in get_hint_pep_args(hint)
        )
    # Else, this hint is *NOT* a union.

    # Return "None", as this hint is unignorable only under PEP 484.
    return None

# ....................{ TESTERS ~ kind                    }....................
def is_hint_pep484_forwardref(hint: object) -> bool:
    '''
    ``True`` only if the passed object is a :pep:`484`-compliant **forward
    reference type hint** (i.e., instance of the :class:`typing.ForwardRef`
    class implicitly replacing all string arguments subscripting :mod:`typing`
    objects).

    The :mod:`typing` module implicitly replaces all strings subscripting
    :mod:`typing` objects (e.g., the ``MuhType`` in ``List['MuhType']``) with
    :class:`typing.ForwardRef` instances containing those strings as instance
    variables, for nebulous reasons that make little justifiable sense.

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    bool
        ``True`` only if this object is a :pep:`484`-compliant forward
        reference type hint.
    '''

    # Return true only if this hint is an instance of the PEP 484-compliant
    # forward reference superclass.
    return isinstance(hint, HINT_PEP484_FORWARDREF_TYPE)


def is_hint_pep484_typevar(hint: object) -> bool:
    '''
    ``True`` only if the passed object either is a PEP-compliant **type
    variable** (i.e., instance of the :class:`TypeVar` class).

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Motivation
    ----------
    Since type variables are not themselves types but rather placeholders
    dynamically replaced with types by type checkers according to various
    arcane heuristics, both type variables and types parametrized by type
    variables warrant special-purpose handling.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    bool
        ``True`` only if this object is a type variable.
    '''

    # Return true only if the type of this hint is that of all type variables.
    #
    # Note that the "typing.TypeVar" class prohibits subclassing: e.g.,
    #     >>> import typing as t
    #     >>> class MutTypeVar(t.TypeVar): pass
    #     TypeError: Cannot subclass special typing classes
    #
    # Ergo, the object identity test performed here both suffices and is more
    # efficient than the equivalent general-purpose test, which requires an
    # implicit breadth- or depth-first search over the method resolution order
    # (MRO) of all superclasses of this object: e.g.,
    #     # This is potentially *MUCH* slower. It's the little things in life.
    #     return isinstance(hint, TypeVar)
    return hint.__class__ is TypeVar

# ....................{ TESTERS ~ kind : generic          }....................
# If the active Python interpreter targets at least Python >= 3.7.0, implement
# this function in the standard way.
#
# Sadly, Python 3.7.0 broke backward compatibility with the public API of the
# "typing" module by removing the "typing.GenericMeta" metaclass previously
# referenced by this function under Python 3.6.
if IS_PYTHON_AT_LEAST_3_7:
    def is_hint_pep484_generic(hint: object) -> bool:

        # Avoid circular import dependencies.
        from beartype._util.hint.pep.proposal.pep484585.utilpepgeneric import (
            get_hint_pep484585_generic_type_or_none)

        # If this hint is *NOT* a class, this hint is *NOT* an unsubscripted
        # generic but could still be a subscripted generic (i.e., generic
        # subscripted by one or more PEP-compliant child type hints). To
        # decide, reduce this hint to the object originating this hint if any,
        # enabling the subsequent test to test whether this origin object is an
        # unsubscripted generic, which would then imply this hint to be a
        # subscripted generic. If this strikes you as insane, you're not alone.
        hint = get_hint_pep484585_generic_type_or_none(hint)

        # Return true only if this hint is a subclass of the "typing.Generic"
        # abstract base class (ABC), in which case this hint is a user-defined
        # generic.
        #
        # Note that this test is robust against edge case, as the "typing"
        # module guarantees all user-defined classes subclassing one or more
        # "typing" pseudo-superclasses to subclass the "typing.Generic"
        # abstract base class (ABC) regardless of whether those classes
        # originally did so explicitly. How? By type erasure, of course, the
        # malicious gift that keeps on giving:
        #     >>> import typing as t
        #     >>> class MuhList(t.List): pass
        #     >>> MuhList.__orig_bases__
        #     (typing.List)
        #     >>> MuhList.__mro__
        #     (__main__.MuhList, list, typing.Generic, object)
        #
        # Note that this issubclass() call implicitly performs a surprisingly
        # inefficient search over the method resolution order (MRO) of all
        # superclasses of this hint. In theory, the cost of this search might
        # be circumventable by observing that this ABC is expected to reside at
        # the second-to-last index of the tuple exposing this MRO far all
        # generics by virtue of fragile implementation details violating
        # privacy encapsulation. In practice, this codebase is fragile enough.
        #
        # Note lastly that the following logic superficially appears to
        # implement the same test *WITHOUT* the onerous cost of a search:
        #     return len(get_hint_pep484_generic_bases_unerased_or_none(hint)) > 0
        #
        # Why didn't we opt for that, then? Because this tester is routinely
        # passed objects that *CANNOT* be guaranteed to be PEP-compliant.
        # Indeed, the high-level is_hint_pep() tester establishing the
        # PEP-compliance of arbitrary objects internally calls this lower-level
        # tester to do so. Since the
        # get_hint_pep484_generic_bases_unerased_or_none() getter internally
        # reduces to returning the tuple of the general-purpose
        # "__orig_bases__" dunder attribute formalized by PEP 560, testing
        # whether that tuple is non-empty or not in no way guarantees this
        # object to be a PEP-compliant generic.
        return is_type_subclass(hint, Generic)  # type: ignore[arg-type]
# Else, the active Python interpreter targets Python 3.6.x. In this case,
# implement this function specific to this Python version.
else:
    # Import the Python 3.6.x-specific metaclass required by this tester.
    from typing import GenericMeta  # type: ignore[attr-defined]

    def is_hint_pep484_generic(hint: object) -> bool:

        # Avoid circular import dependencies.
        from beartype._util.hint.pep.proposal.pep484585.utilpepgeneric import (
            get_hint_pep484585_generic_type_or_none)
        from beartype._util.hint.pep.utilpeptest import (
            is_hint_pep_type_typing)

        # If this hint is *NOT* a class, reduce this hint to the object
        # originating this hint if any. See the above tester for details.
        hint_type = get_hint_pep484585_generic_type_or_none(hint)

        # Return true only if...
        #
        # Note that:
        # * The Python >= 3.7.0-specific implementation of this tester does
        #   *NOT* apply to Python < 3.7.0, as this metaclass unconditionally
        #   raises exceptions when user-defined "typing" subclasses internally
        #   requiring this metaclass are passed to the issubclass() builtin.
        # * This tester intentionally avoids returning true for *ALL* generics
        #   (including both those internally defined by the "typing" module and
        #   those externally defined by third-party callers). Why? Because
        #   generics internally defined by the "typing" module are effectively
        #   *NOT* generics and only implemented as such under Python < 3.7.0
        #   for presumably indefensible low-level reasons -- including:
        #   * *ALL* callable types (e.g., "typing.Awaitable",
        #     "typing.Callable", "typing.Coroutine", "typing.Generator").
        #   * *MOST* container and iterable types (e.g., "typing.Dict",
        #     "typing.List", "typing.Mapping", "typing.Tuple").
        #
        # If this tester returned true for *ALL* generics, downstream callers
        # would have no means of distinguishing genuine generics from
        # disingenuous "typing" pseudo-generics.
        return (
            # The metaclass of this hint is the "typing.GenericMeta" metaclass
            # *AND*...
            isinstance(hint_type, GenericMeta) and
            # This hint is either...
            (
                # A parametrization of the "typing.Generic" class (e.g.,
                # "Generic[S, T]") *OR*...
                hint_type is Generic or
                # A subclass *NOT* defined by the "typing" module. See above.
                not is_hint_pep_type_typing(hint_type)
            )
        )


# Docstring for this function regardless of implementation details.
is_hint_pep484_generic.__doc__ = '''
    ``True`` only if the passed object is a :mod:`typing` **generic** (i.e.,
    class superficially subclassing at least one non-class PEP-compliant
    object defined by the :mod:`typing` module).

    Specifically, this tester returns ``True`` only if this object is a class
    subclassing a combination of:

    * At least one of:

      * The :pep:`484`-compliant :mod:`typing.Generic` superclass.
      * The `PEP 544`-_compliant :mod:`typing.Protocol` superclass.

    * Zero or more non-class :mod:`typing` pseudo-superclasses (e.g.,
      ``typing.List[int]``).
    * Zero or more other standard superclasses.

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Design
    ----------
    Since *all* :mod:`typing` generics subclass the :pep:`484`-compliant
    :mod:`typing.Generic` superclass first introduced with :pep:`484`, this
    tester is intentionally:

    * Defined in the :pep:`484`-specific submodule rather than either the `PEP
      585`_-specific submodule *or* higher-level PEP-agnostic test submodule.
    * Named ``is_hint_pep484_generic`` rather than
      ``is_hint_pep484or544_generic`` or ``is_hint_pep_typing_generic``.

    From the end user perspective, *all* :mod:`typing` generics are effectively
    indistinguishable from :pep:`484`-compliant generics and should typically
    be generically treated as such.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    bool
        ``True`` only if this object is a :mod:`typing` generic.
    '''

# ....................{ TESTERS ~ newtype                 }....................
# If the active Python interpreter targets Python >= 3.10 and thus defines
# "typing.NewType" type hints as instances of that class, implement this tester
# unique to prior Python versions to raise an exception.
if IS_PYTHON_AT_LEAST_3_10:
    def is_hint_pep484_newtype_pre_python310(hint: object) -> bool:
        raise BeartypeDecorHintPep484Exception(
            'is_hint_pep484_newtype_pre_python310() assumes Python < 3.10, '
            'but current Python interpreter targets Python >= 3.10.'
        )
# Else, the active Python interpreter targets Python < 3.10 and thus defines
# "typing.NewType" type hints as closures returned by that function. Since
# these closures are sufficiently dissimilar from all other type hints to
# require unique detection, implement this tester unique to this obsolete
# Python version to detect these closures.
else:
    def is_hint_pep484_newtype_pre_python310(hint: object) -> bool:

        # Return true only if...
        return (
            # This hint is a pure-Python function *AND*...
            #
            # Note that we intentionally do *NOT* call the callable() builtin
            # here, as that builtin erroneously returns false positives for
            # non-standard classes defining the __call__() dunder method to
            # unconditionally raise exceptions. Critically, this includes most
            # PEP 484-compliant type hints, which naturally fail to define both
            # the "__module__" *AND* "__qualname__" dunder instance variables
            # accessed below. Shoot me now, fam.
            isinstance(hint, FunctionType) and
            # This callable is a closure created and returned by the
            # typing.NewType() function. Note that:
            #
            # * The "__module__" and "__qualname__" dunder instance variables
            #   are *NOT* generally defined for arbitrary objects but are
            #   specifically defined for callables.
            # * "__qualname__" is safely available under Python >= 3.3.
            # * This test derives from the observation that the concatenation
            #   of this callable's "__qualname__" and "__module" dunder
            #   instance variables suffices to produce a string unambiguously
            #   identifying whether this hint is a "NewType"-generated closure:
            #       >>> from typing import NewType
            #       >>> UserId = t.NewType('UserId', int)
            #       >>> UserId.__qualname__
            #       >>> 'NewType.<locals>.new_type'
            #       >>> UserId.__module__
            #       >>> 'typing'
            f'{hint.__module__}.{hint.__qualname__}'.startswith(
                'typing.NewType.')
        )


is_hint_pep484_newtype_pre_python310.__doc__ = '''
    ``True`` only if the passed object either is a :pep:`484`-compliant **new
    type** (i.e., closure created and returned by the :func:`typing.NewType`
    closure factory function).

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Caveats
    ----------
    **New type aliases are a complete farce and thus best avoided.**
    Specifically, these PEP-compliant type hints are *not* actually types but
    rather **identity closures** that return their passed parameters as is.
    Instead, where distinct types are:

    * *Not* required, simply annotate parameters and return values with the
      desired superclasses.
    * Required, simply:

      * Subclass the desired superclasses as usual.
      * Annotate parameters and return values with those subclasses.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    bool
        ``True`` only if this object is a :pep:`484`-compliant new type.
    '''

# ....................{ GETTERS ~ forwardref              }....................
@callable_cached
def get_hint_pep484_forwardref_type_basename(hint: Any) -> str:
    '''
    **Unqualified classname** (i.e., name of a class *not* containing a ``.``
    delimiter and thus relative to the fully-qualified name of the lexical
    scope declaring that class) referred to by the passed :pep:`484`-compliant
    **forward reference type hint** (i.e., instance of the
    :class:`typing.ForwardRef` class implicitly replacing all string arguments
    subscripting :mod:`typing` objects).

    This tester is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    str
        Unqualified classname referred to by this :pep:`484`-compliant forward
        reference type hint.

    Raises
    ----------
    BeartypeDecorHintForwardRefException
        If this object is *not* a :pep:`484`-compliant forward reference.

    See Also
    ----------
    :func:`is_hint_pep484_forwardref`
        Further commentary.
    '''

    # If this object is *NOT* a PEP 484-compliant forward reference, raise an
    # exception.
    if not is_hint_pep484_forwardref(hint):
        raise BeartypeDecorHintForwardRefException(
            f'Type hint {repr(hint)} not forward reference.')
    # Else, this object is a PEP 484-compliant forward reference.

    # Return the unqualified classname referred to by this reference. Note
    # that:
    # * This requires violating privacy encapsulation by accessing a dunder
    #   instance variable unique to the "typing.ForwardRef" class.
    # * This object defines a significant number of other "__forward_"-prefixed
    #   dunder instance variables, which exist *ONLY* to enable the blatantly
    #   useless typing.get_type_hints() function to avoid repeatedly (and thus
    #   inefficiently) reevaluating the same forward reference. *sigh*
    return hint.__forward_arg__

# ....................{ GETTERS ~ newtype                 }....................
def get_hint_pep484_newtype_class(hint: Any) -> type:
    '''
    User-defined class aliased by the passed :pep:`484`-compliant **new type**
    (i.e., closure created and returned by the :func:`typing.NewType` closure
    factory function).

    This getter is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    type
        User-defined class aliased by this :pep:`484`-compliant new type.

    Raises
    ----------
    BeartypeDecorHintPep484Exception
        If this object is *not* a :pep:`484`-compliant new type.

    See Also
    ----------
    :func:`is_hint_pep484_newtype`
        Further commentary.
    '''

    # Avoid circular import dependencies.
    from beartype._util.hint.pep.utilpepget import get_hint_pep_sign

    # If this object is *NOT* a PEP 484-compliant "NewType" hint, raise an
    # exception.
    if get_hint_pep_sign(hint) is not HintSignNewType:
        raise BeartypeDecorHintPep484Exception(
            f'Type hint {repr(hint)} not "typing.NewType".')
    # Else, this object is a PEP 484-compliant "NewType" hint.

    # Return the unqualified classname referred to by this reference. Note
    # that this requires violating privacy encapsulation by accessing a dunder
    # instance variable unique to closures created by the typing.NewType()
    # closure factory function.
    return hint.__supertype__

# ....................{ GETTERS ~ generic                 }....................
@callable_cached
def get_hint_pep484_generic_base_erased_from_unerased(hint: Any) -> type:
    '''
    Erased superclass originating the passed :pep:`484`-compliant **unerased
    pseudo-superclass** (i.e., :mod:`typing` object originally listed as a
    superclass prior to its implicit type erasure by the :mod:`typing` module).

    This getter is intentionally *not* memoized (e.g., by the
    :func:`callable_cached` decorator), as the implementation trivially reduces
    to an efficient one-liner.

    Parameters
    ----------
    hint : object
        :pep:`484`-compliant unerased pseudo-superclass to be reduced to its
        erased superclass.

    Returns
    ----------
    type
        Erased superclass originating this :pep:`484`-compliant unerased
        pseudo-superclass.

    Raises
    ----------
    BeartypeDecorHintPep484Exception
        if this object is *not* a :pep:`484`-compliant unerased
        pseudo-superclass.
    '''

    # Avoid circular import dependencies.
    from beartype._util.hint.pep.utilpepget import get_hint_pep_origin_or_none

    # Erased superclass originating this unerased pseudo-superclass if any *OR*
    # "None" otherwise.
    hint_type_origin = get_hint_pep_origin_or_none(hint)

    # If this hint originates from *NO* such superclass, raise an exception.
    if hint_type_origin is None:
        raise BeartypeDecorHintPep484Exception(
            f'Unerased PEP 484 generic or PEP 544 protocol {repr(hint)} '
            f'originates from no erased superclass.'
        )
    # Else, this hint originates from such a superclass.

    # Return this superclass.
    return hint_type_origin


@callable_cached
def get_hint_pep484_generic_bases_unerased(hint: Any) -> tuple:
    '''
    Tuple of all unerased :mod:`typing` **pseudo-superclasses** (i.e.,
    :mod:`typing` objects originally listed as superclasses prior to their
    implicit type erasure under :pep:`560`) of the passed :pep:`484`-compliant
    **generic** (i.e., class subclassing at least one non-class :mod:`typing`
    object).

    This getter is memoized for efficiency.

    Parameters
    ----------
    hint : object
        Object to be inspected.

    Returns
    ----------
    Tuple[object]
        Tuple of the one or more unerased pseudo-superclasses of this
        :mod:`typing` generic. Specifically:

        * If this generic defines an ``__orig_bases__`` dunder instance
          variable, the value of that variable.
        * Else, the value of the ``__mro__`` dunder instance variable stripped
          of all ignorable classes conveying no semantic meaning, including:

          * This generic itself.
          * The :class:`typing.Generic` superclass.
          * The :class:`object` root superclass.

    Raises
    ----------
    BeartypeDecorHintPep484Exception
        If this hint is either:

        * *Not* a :mod:`typing` generic.
        * A :mod:`typing` generic that erased *none* of its superclasses but
          whose method resolution order (MRO) lists strictly less than four
          classes. Valid :pep:`484`-compliant generics should list at least
          four classes, including (in order):

          #. This class itself.
          #. The one or more :mod:`typing` objects directly subclassed by this
             generic.
          #. The :class:`typing.Generic` superclass.
          #. The :class:`object` root superclass.

    See Also
    ----------
    :func:`beartype._util.hint.pep.proposal.pep484585.utilpepgeneric.get_hint_pep484585_generic_bases_unerased`
        Further details.
    '''

    #FIXME: This tuple appears to be implemented erroneously -- at least under
    #Python 3.7, anyway. Although this tuple is implemented correctly for the
    #common case of user-defined types directly subclassing "typing" types,
    #this tuple probably is *NOT* implemented correctly for the edge case of
    #user-defined types indirectly subclassing "typing" types: e.g.,
    #
    #    >>> import collections.abc, typing
    #    >>> T = typing.TypeVar('T')
    #    >>> class Direct(collections.abc.Sized, typing.Generic[T]): pass
    #    >>> Direct.__orig_bases__
    #    (collections.abc.Sized, typing.Generic[~T])
    #    >>> class Indirect(collections.abc.Container, Direct): pass
    #    >>> Indirect.__orig_bases__
    #    (collections.abc.Sized, typing.Generic[~T])
    #
    #*THAT'S COMPLETELY INSANE.* Clearly, their naive implementation failed to
    #account for actual real-world use cases.
    #
    #On the bright side, the current implementation prevents us from actually
    #having to perform a breadth-first traversal of all original superclasses
    #of this class in method resolution order (MRO). On the dark side, it's
    #pants-on-fire balls -- but there's not much we can do about that. *sigh*
    #
    #If we ever need to perform that breadth-first traversal, resurrect this:
    #
    #    # If this class was *NOT* subject to type erasure, reduce to a noop.
    #    if not hint_bases:
    #        return hint_bases
    #
    #    # Fixed list of all typing super attributes to be returned.
    #    superattrs = acquire_fixed_list(SIZE_BIG)
    #
    #    # 0-based index of the last item of this list.
    #    superattrs_index = 0
    #
    #    # Fixed list of all transitive superclasses originally listed by this
    #    # class iterated in method resolution order (MRO).
    #    hint_orig_mro = acquire_fixed_list(SIZE_BIG)
    #
    #    # 0-based indices of the current and last items of this list.
    #    hint_orig_mro_index_curr = 0
    #    hint_orig_mro_index_last = 0
    #
    #    # Initialize this list with the tuple of all direct superclasses of this
    #    # class, which iteration then expands to all transitive superclasses.
    #    hint_orig_mro[:len(hint_bases)] = hint_bases
    #
    #    # While the heat death of the universe has been temporarily forestalled...
    #    while (True):
    #        # Currently visited superclass of this class.
    #        hint_base = hint_orig_mro[hint_orig_mro_index_curr]
    #
    #        # If this superclass is a typing attribute...
    #        if is_hint_pep_type_typing(hint_base):
    #            # Avoid inserting this attribute into the "hint_orig_mro" list.
    #            # Most typing attributes are *NOT* actual classes and those that
    #            # are have no meaningful public superclass. Ergo, iteration
    #            # terminates with typing attributes.
    #            #
    #            # Insert this attribute at the current item of this list.
    #            superattrs[superattrs_index] = hint_base
    #
    #            # Increment this index to the next item of this list.
    #            superattrs_index += 1
    #
    #            # If this class subclasses more than the maximum number of "typing"
    #            # attributes supported by this function, raise an exception.
    #            if superattrs_index >= SIZE_BIG:
    #                raise BeartypeDecorHintPep560Exception(
    #                    '{} PEP type {!r} subclasses more than '
    #                    '{} "typing" types.'.format(
    #                        exception_prefix,
    #                        hint,
    #                        SIZE_BIG))
    #        # Else, this superclass is *NOT* a typing attribute. In this case...
    #        else:
    #            # Tuple of all direct superclasses originally listed by this class
    #            # prior to PEP 484 type erasure if any *OR* the empty tuple
    #            # otherwise.
    #            hint_base_bases = getattr(hint_base, '__orig_bases__')
    #
    #            #FIXME: Implement breadth-first traversal here.
    #
    #    # Tuple sliced from the prefix of this list assigned to above.
    #    superattrs_tuple = tuple(superattrs[:superattrs_index])
    #
    #    # Release and nullify this list *AFTER* defining this tuple.
    #    release_fixed_list(superattrs)
    #    del superattrs
    #
    #    # Return this tuple as is.
    #    return superattrs_tuple
    #
    #Also resurrect this docstring snippet:
    #
    #    Raises
    #    ----------
    #    BeartypeDecorHintPep560Exception
    #        If this object defines the ``__orig_bases__`` dunder attribute but that
    #        attribute transitively lists :data:`SIZE_BIG` or more :mod:`typing`
    #        attributes.
    #
    #Specifically:
    #  * Acquire a fixed list of sufficient size (e.g., 64). We probably want
    #    to make this a constant in "utilcachelistfixedpool" for reuse
    #    everywhere, as this is clearly becoming a common idiom.
    #  * Slice-assign "__orig_bases__" into this list.
    #  * Maintain two simple 0-based indices into this list:
    #    * "bases_index_curr", the current base being visited.
    #    * "bases_index_last", the end of this list also serving as the list
    #      position to insert newly discovered bases at.
    #  * Iterate over this list and keep slice-assigning from either
    #    "__orig_bases__" (if defined) or "__mro__" (otherwise) into
    #    "list[bases_index_last:len(__orig_bases__)]". Note that this has the
    #    unfortunate disadvantage of temporarily iterating over duplicates,
    #    but... *WHO CARES.* It still works and we subsequently
    #    eliminate duplicates at the end.
    #  * Return a frozenset of this list, thus implicitly eliminating
    #    duplicate superclasses.

    # Avoid circular import dependencies.
    from beartype._util.hint.pep.proposal.pep484585.utilpepgeneric import (
        get_hint_pep484585_generic_type_or_none)

    # If this hint is *NOT* a class, reduce this hint to the object originating
    # this hint if any. See is_hint_pep484_generic() for details.
    hint = get_hint_pep484585_generic_type_or_none(hint)

    # If this hint is *NOT* a PEP 484-compliant generic, raise an exception.
    if not is_hint_pep484_generic(hint):
        raise BeartypeDecorHintPep484Exception(
            f'Type hint {repr(hint)} neither '
            f'PEP 484 generic nor PEP 544 protocol.'
        )
    # Else, this hint is a PEP 484-compliant generic.

    # Unerased pseudo-superclasses of this generic if any *OR* "None"
    # otherwise (e.g., if this generic is a single-inherited protocol).
    hint_bases = getattr(hint, '__orig_bases__', None)

    # If this generic erased its superclasses, return these superclasses as is.
    if hint_bases is not None:
        return hint_bases
    # Else, this generic erased *NONE* of its superclasses. These superclasses
    # *MUST* by definition be unerased and thus safely returnable as is. In
    # this case...

    # Unerased superclasses of this generic defined by the method resolution
    # order (MRO) for this generic.
    hint_bases = hint.__mro__

    # Substring prefixing all exceptions raised below.
    EXCEPTION_STR_PREFIX = (
        f'PEP 484 generic {repr(hint)} '
        f'method resolution order {repr(hint_bases)}'
    )

    # If this MRO lists strictly less than four classes, raise an exception.
    # The MRO for any unerased generic should list at least four classes:
    # * This class itself.
    # * The one or more "typing" objects directly subclassed by this generic.
    # * The "typing.Generic" superclass.
    # * The "object" root superclass.
    if len(hint_bases) < 4:
        raise BeartypeDecorHintPep484Exception(
            f'{EXCEPTION_STR_PREFIX} lists less than four classes.')
    # Else, this MRO lists at least four classes.
    #
    # If any class listed by this MRO fails to comply with the above
    # expectations, raise an exception.
    elif hint_bases[0] != hint:
        raise BeartypeDecorHintPep484Exception(
            f'{EXCEPTION_STR_PREFIX} first item not {hint}.')
    elif hint_bases[-2] != Generic:
        raise BeartypeDecorHintPep484Exception(
            f'{EXCEPTION_STR_PREFIX} second-to-last item not {Generic}.')
    elif hint_bases[-1] != object:
        raise BeartypeDecorHintPep484Exception(
            f'{EXCEPTION_STR_PREFIX} last item not {object}.')
    # Else, all classes listed by this MRO comply with the above expectations.

    # Return a slice of this tuple preserving *ONLY* the non-ignorable
    # superclasses listed by this tuple for conformance with the tuple returned
    # by this getter from the "__orig_bases__", which similarly lists *ONLY*
    # non-ignorable superclasses. Specifically, strip from this tuple:
    # * This class itself.
    # * The "typing.Generic" superclass.
    # * The "object" root superclass.
    return hint_bases[1:-2]