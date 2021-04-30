#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype code-based object validation classes** (i.e.,
:mod:`beartype`-specific classes enabling callers to define PEP-compliant
validators from arbitrary caller-defined objects tested via explicitly
supported object introspectors efficiently generating stack-free code).

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                              }....................
# All "FIXME:" comments for this submodule reside in this package's "__init__"
# submodule to improve maintainability and readability here.

# ....................{ IMPORTS                           }....................
from beartype.roar import BeartypeValeSubscriptionException
from beartype.vale._valeisabc import _IsABC
from beartype.vale._valeissub import _SubscriptedIs
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.data.utildatadict import update_mapping
from beartype._util.func.utilfuncscope import (
    CallableScope,
    add_func_scope_attr,
)
from beartype._util.text.utiltextmagic import (
    CODE_INDENT_1,
    # LINE_RSTRIP_INDEX_AND,
)
from beartype._util.text.utiltextrepr import represent_object
from beartype._util.utilobject import SENTINEL
from typing import Any, Tuple

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ CLASSES ~ subscriptable           }....................
#FIXME: Unit test us up.
#FIXME: Finalize docstring example.
class IsAttr(_IsABC):
    '''
    **Beartype object attribute validator factory** (i.e., class that, when
    subscripted (indexed) by both the name of any object attribute *and* any
    :class:`_SubscriptedIs` object created by subscripting any
    :mod:`beartype.vale` class for validating that attribute, creates another
    :class:`_SubscriptedIs` object suitable for subscripting (indexing)
    :attr:`typing.Annotated` type hints, which validates that
    :mod:`beartype`-decorated callable parameters and returns annotated by
    those hints define an attribute with that name satisfying that attribute
    validator).

    This class efficiently validates that callable parameters and returns
    define arbitrary object attributes satisfying arbitrary validators
    subscripting (indexing) this class. Any :mod:`beartype`-decorated callable
    parameter or return annotated by a :attr:`typing.Annotated` type hint
    subscripted (indexed) by this class subscripted (indexed) by any object
    attribute name and validator (e.g., ``typing.Annotated[{cls},
    beartype.vale.IsAttr[{attr_name}, {attr_validator}]]`` for any class
    ``{cls}``, object attribute name ``{attr_name}`, and object attribute
    validator ``{attr_validator}``) validates that parameter or return value to
    be an instance of that class defining an attribute with that name
    satisfying that attribute validator.

    **This class incurs no time performance penalties at call time.** Whereas
    the general-purpose :class:`beartype.vale.Is` class necessarily calls the
    caller-defined callable subscripting that class at call time and thus
    incurs a minor time performance penalty, this class efficiently reduces to
    one-line tests in :mod:`beartype`-generated wrapper functions *without*
    calling any callables and thus incurs *no* time performance penalties.

    Examples
    ----------
    .. _code-block:: python

       # Import the requisite machinery.
       >>> import numpy as np
       >>> from beartype import beartype
       >>> from beartype.vale import IsAttr, IsEqual
       >>> from typing import Annotated

       # Type hint matching only two-dimensional NumPy arrays of 64-bit floats.
       >>> Numpy2DArrayOfFloats = typing.Annotated[
       ...     ndarray,
       ...     IsAttr['dtype.type', IsEqual[np.float64]],
       ...     IsAttr['ndim', IsEqual[2]],
       ... ]

       # Type hint matching only one-dimensional NumPy arrays of 64-bit floats.
       >>> Numpy1DArrayOfFloats = typing.Annotated[
       ...     ndarray,
       ...     IsAttr['dtype.type', IsEqual[np.float64]],
       ...     IsAttr['ndim', IsEqual[2]],
       ... ]

       # NumPy arrays of well-known real number series.
       >>> FAREY_2D_ARRAY_OF_FLOATS = np.array(
       ...     [[0/1, 1/8,], [1/7, 1/6,], [1/5, 1/4], [2/7, 1/3], [3/8, 2/5]])
       >>> FAREY_1D_ARRAY_OF_FLOATS = np.array(
       ...     [3/7, 1/2, 4/7, 3/5, 5/8, 2/3, 5/7, 3/4, 4/5, 5/6, 6/7, 7/8])

       # Annotate callables by those type hints.
       >>> @beartype
       ... def sqrt_sum_2d(
       ...     array: Numpy2DArrayOfFloats) -> Numpy1DArrayOfFloats:
       ...     """
       ...     One-dimensional NumPy array of 64-bit floats produced by first
       ...     summing the passed two-dimensional NumPy array of 64-bit floats
       ...     along its second dimension and then square-rooting those sums.
       ...     """
       ...     return np.sqrt(array.sum(axis=1))

       #FIXME: Resume here tomorrow, please.
       # Call those callables with parameters satisfying those hints.
       >>> sqrt_sum_2d(FAREY_2D_ARRAY_OF_FLOATS)
       ????????????????????????????????????

       # Call those callables with parameters not satisfying those hints.
       >>> sqrt_sum_2d(FAREY_1D_ARRAY_OF_FLOATS)
       ????????????????????????????????????

    See Also
    ----------
    :class:`beartype.vale.Is`
        Further commentary.
    '''

    # ..................{ DUNDERS                           }..................
    #FIXME: Implement us up, please.
    #FIXME: Unit test memoization, please.
    @callable_cached
    def __class_getitem__(
        cls, args: Tuple[str, _SubscriptedIs]) -> _SubscriptedIs:
        '''
        `PEP 560`_-compliant dunder method creating and returning a new
        :class:`_SubscriptedIs` object validating object attributes with the
        passed name satisfying the passed validator, suitable for subscripting
        `PEP 593`_-compliant :attr:`typing.Annotated` type hints.

        This method is memoized for efficiency.

        Parameters
        ----------
        args : Tuple[str, _SubscriptedIs]
            2-tuple ``(attr_name, attr_validator)``, where:

            * ``attr_name`` is the arbitrary attribute name to validate that
              parameters and returns define satisfying the passed validator.
            * ``attr_validator`` is the attribute validator to validate that
              attributes with the passed name of parameters and returns
              satisfy.

        Returns
        ----------
        _SubscriptedIs
            New object encapsulating this validation.

        Raises
        ----------
        BeartypeValeSubscriptionException
            If this class was subscripted by either:

            * *No* arguments.
            * One argument.
            * Three or more arguments.

        See Also
        ----------
        :class:`IsAttr`
            Usage instructions.

        .. _PEP 560:
           https://www.python.org/dev/peps/pep-0560
        .. _PEP 593:
           https://www.python.org/dev/peps/pep-0593
        '''

        # If this class was subscripted by one non-tuple argument, raise an
        # exception.
        if not isinstance(args, tuple):
            raise BeartypeValeSubscriptionException(
                f'{repr(cls)} subscripted by one non-tuple argument:\n'
                f'{represent_object(args)}'
            )
        # Else, this class was subscripted by either no *OR* two or more
        # arguments (contained in this tuple).
        #
        # If this class was *NOT* subscripted by two arguments...
        elif len(args) != 2:
            # If this class was subscripted by one or more arguments, then by
            # deduction this class was subscripted by three or more arguments.
            # In this case, raise a human-readable exception.
            if args:
                raise BeartypeValeSubscriptionException(
                    f'{repr(cls)} subscripted by three or more arguments:\n'
                    f'{represent_object(args)}'
                )
            # Else, this class was subscripted by *NO* arguments. In this case,
            # raise a human-readable exception.
            else:
                raise BeartypeValeSubscriptionException(
                    f'{repr(cls)} subscripted by empty tuple.')
        # Else, this class was subscripted by exactly two arguments.

        # Localize these arguments to human-readable local variables.
        attr_name, attr_validator = args

        # Representer (i.e., callable accepting *NO* arguments returning a
        # machine-readable representation of this validator), defined *AFTER*
        # localizing these validator arguments.
        get_repr = lambda: (
            f'{cls.__name__}[{repr(attr_name)}, {repr(attr_validator)}]')

        # If this name is *NOT* a string, raise an exception.
        if not isinstance(attr_name, str):
            raise BeartypeValeSubscriptionException(
                f'{get_repr()} subscripted first argument '
                f'{repr(attr_name)} not string.'
            )
        # Else, this name is a string.
        #
        # If this name is the empty string, raise an exception.
        elif not attr_name:
            raise BeartypeValeSubscriptionException(
                f'{get_repr()} subscripted first argument '
                f'{repr(attr_name)} empty.'
            )
        # Else, this name is a non-empty string.
        #
        # Note that this name has *NOT* yet been validated to be valid Python
        # identifier. While we could do so here by calling our existing
        # is_identifier_qualified() tester, doing so would inefficiently repeat
        # the split on "." characters performed below. Instead, we iteratively
        # validate each split substring to be a valid Python identifier below.

        # Callable inefficiently validating object attributes with this name
        # against this validator.
        # is_valid: SubscriptedIsValidator = None  # type: ignore[assignment]

        # Code snippet efficiently validating object attributes with this name
        # against this validator.
        is_valid_code = ''

        # Dictionary mapping from the name to value of each local attribute
        # referenced in the "is_valid_code" snippet defined below.
        is_valid_code_locals: CallableScope = {}

        # If this attribute name is unqualified (i.e., contains no "."
        # delimiters), prefer an efficient optimization avoiding iteration.
        if '.' not in attr_name:
            # If this name is *NOT* a valid Python identifier, raise an
            # exception.
            if not attr_name.isidentifier():
                raise BeartypeValeSubscriptionException(
                    f'{get_repr()} subscripted first argument '
                    f'{repr(attr_name)} syntactically invalid '
                    f'(i.e., not valid Python identifier).'
                )
            # Else, this name is a valid Python identifier.

            def is_valid(pith: Any) -> bool:
                f'''
                ``True`` only if the passed object defines an attribute named
                {repr(attr_name)} whose value satisfies the validator
                {repr(attr_validator)}.
                '''

                # Attribute of this object with this name if this object
                # defines such an attribute *OR* a sentinel placeholder
                # otherwise (i.e., if this object defines *NO* such attribute).
                pith_attr = getattr(pith, attr_name, SENTINEL)

                # Return true only if...
                return (
                    # This object defines an attribute with this name *AND*...
                    pith_attr is not SENTINEL and
                    # This attribute satisfies this validator.
                    attr_validator.is_valid(pith_attr)
                )

            # Names of new parameters added to the signature of wrapper
            # functions enabling this validator to be tested in those functions
            # *WITHOUT* additional stack frames whose values are:
            # * The sentinel placeholder.
            sentinel_name = add_func_scope_attr(
                attr=SENTINEL, attr_scope=is_valid_code_locals)

            # Generate locals safely merging the locals required by both the
            # code generated below *AND* the code validating this attribute.
            update_mapping(
                is_valid_code_locals, attr_validator._is_valid_code_locals)

            # Name of a local variable in this code whose:
            # * Name is sufficiently obfuscated as to be hopefully unique to
            #   the code generated by this validator.
            # * Value is the value of this attribute of the arbitrary object
            #   being validated by this code.
            obj_attr_name = f'__beartype_isattr_{attr_name}'

            # Code validating this attribute's value, formatted so as to be
            # safely embeddable in the larger code expression defined below.
            obj_attr_value_is_valid_expr = (
                attr_validator._is_valid_code.format(
                    # Replace the placeholder substring "{obj}" in this code
                    # with the local variable whose value is the value of the
                    # desired object attribute.
                    obj=obj_attr_name,
                    # Replace the placeholder substring "{index}" in this code
                    # with an indentation increased by one level.
                    index=f'{{index}}{CODE_INDENT_1}',
                ))

            # Code snippet efficiently validating against this object.
            is_valid_code = VALE_CODE_CHECK_ISATTR.format(
                obj_attr_name=obj_attr_name,
                obj_attr_value_is_valid_expr=obj_attr_value_is_valid_expr,
                sentinel_name=sentinel_name,
            )
        # Else, this attribute name is qualified (i.e., contains one or more
        # "." delimiters), fallback to a general solution performing iteration.
        else:
            #FIXME: Implement us up when we find the time, please. We currently
            #raise an exception simply because we ran out of time for this. :{
            raise BeartypeValeSubscriptionException(
                f'{get_repr()} subscripted first argument '
                f'{repr(attr_name)} not unqualified Python identifier '
                f'(i.e., contains one or more "." characters).'
            )

        # Create and return this subscription.
        return _SubscriptedIs(
            is_valid=is_valid,
            is_valid_code=is_valid_code,
            is_valid_code_locals=is_valid_code_locals,
            get_repr=get_repr,
        )

# ....................{ CONSTANTS                         }....................
#FIXME: Shift into a new "_valesnip" submodule, please.
VALE_CODE_CHECK_ISATTR = '''(
{{index}}    # Attribute of this object with this name if this object defines
{{index}}    # such an attribute *OR* a sentinel placeholder otherwise.
{{index}}    {obj_attr_name} := getattr(
{{index}}        {{obj}}, {repr(attr_name)}, {sentinel_name}
{{index}}    ) is not {sentinel_name} and
{{index}}    {obj_attr_value_is_valid_expr}
{{index}})'''
'''
:mod:`beartype.vale.IsAttr`-specific code snippet validating an arbitrary
object to define an attribute with an arbitrary name satisfying an arbitrary
expression evaluating to a boolean.
'''