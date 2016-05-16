"""Pylint plugin for checking in Sphinx, Google, or Numpy style docstrings
"""
from __future__ import print_function, division, absolute_import

import astroid

from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import node_frame_class
import pylint.extensions._check_docs_utils as utils


class DocstringChecker(BaseChecker):
    """Checker for Sphinx, Google, or Numpy style docstrings

    * Check that all function, method and constructor parameters are mentioned
      in the params and types part of the docstring.  Constructor parameters
      can be documented in either the class docstring or ``__init__`` docstring,
      but not both.
    * Check that there are no naming inconsistencies between the signature and
      the documentation, i.e. also report documented parameters that are missing
      in the signature. This is important to find cases where parameters are
      renamed only in the code, not in the documentation.
    * Check that all explicity raised exceptions in a function are documented
      in the function docstring. Caught exceptions are ignored.

    Activate this checker by adding the line::

        load-plugins=pylint.extensions.check_docs

    to the ``MASTER`` section of your ``.pylintrc``.

    :param linter: linter object
    :type linter: :class:`pylint.lint.PyLinter`
    """
    __implements__ = IAstroidChecker

    name = 'docstring_checks'
    msgs = {
        'W9003': ('"%s" missing or differing in parameter documentation',
                  'missing-param-doc',
                  'Please add parameter declarations for all parameters.'),
        'W9004': ('"%s" missing or differing in parameter type documentation',
                  'missing-type-doc',
                  'Please add parameter type declarations for all parameters.'),
        'W9005': ('"%s" has constructor parameters documented in class and __init__',
                  'multiple-constructor-doc',
                  'Please remove parameter declarations in the class or constructor.'),
        'W9006': ('Raising a "%s" is not documented',
                  'missing-raise-doc',
                  'Please document that this exception type is raised.'),
    }

    options = (('accept-no-param-doc',
                {'default': True, 'type' : 'yn', 'metavar' : '<y or n>',
                 'help': 'Whether to accept totally missing parameter '
                         'documentation in a docstring of a function that has '
                         'parameters.'
                }),
               ('accept-no-raise-doc',
                {'default': True, 'type' : 'yn', 'metavar' : '<y or n>',
                 'help': 'Whether to accept totally missing raises'
                         'documentation in a docstring of a function that'
                         'raises an exception.'
                }),
              )

    priority = -2

    constructor_names = {"__init__", "__new__"}
    not_needed_param_in_docstring = {'self', 'cls'}

    def visit_functiondef(self, node):
        """Called for function and method definitions (def).

        :param node: Node for a function or method definition in the AST
        :type node: :class:`astroid.scoped_nodes.Function`
        """
        node_allow_no_param = None
        node_doc = utils.docstringify(node.doc)

        if node.name in self.constructor_names:
            class_node = node_frame_class(node)
            if class_node is not None:
                class_doc = utils.docstringify(class_node.doc)
                self.check_single_constructor_params(class_doc, node_doc, class_node)

                # __init__ or class docstrings can have no parameters documented
                # as long as the other documents them.
                node_allow_no_param = class_doc.has_params() or None
                class_allow_no_param = node_doc.has_params() or None

                self.check_arguments_in_docstring(
                    class_doc, node.args, class_node, class_allow_no_param)

        self.check_arguments_in_docstring(
            node_doc, node.args, node, node_allow_no_param)

    def visit_raise(self, node):
        func_node = node.frame()
        if not isinstance(func_node, astroid.FunctionDef):
            return

        expected_excs = utils.possible_exc_types(node)
        if not expected_excs:
            return

        doc = utils.docstringify(func_node.doc)
        if not doc.is_valid():
            if doc.doc:
                self._handle_no_raise_doc(expected_excs, func_node)
            return

        found_excs = doc.exceptions()
        missing_excs = expected_excs - found_excs
        self._add_all_raise_messages(missing_excs, func_node)

    def check_arguments_in_docstring(self, doc, arguments_node, warning_node,
                                     accept_no_param_doc=None):
        """Check that all parameters in a function, method or class constructor
        on the one hand and the parameters mentioned in the parameter
        documentation (e.g. the Sphinx tags 'param' and 'type') on the other
        hand are consistent with each other.

        * Undocumented parameters except 'self' are noticed.
        * Undocumented parameter types except for 'self' and the ``*<args>``
          and ``**<kwargs>`` parameters are noticed.
        * Parameters mentioned in the parameter documentation that don't or no
          longer exist in the function parameter list are noticed.
        * If the text "For the parameters, see" or "For the other parameters,
          see" (ignoring additional whitespace) is mentioned in the docstring,
          missing parameter documentation is tolerated.
        * If there's no Sphinx style, Google style or NumPy style parameter
          documentation at all, i.e. ``:param`` is never mentioned etc., the
          checker assumes that the parameters are documented in another format
          and the absence is tolerated.

        :param doc: Docstring for the function, method or class.
        :type doc: str

        :param arguments_node: Arguments node for the function, method or
            class constructor.
        :type arguments_node: :class:`astroid.scoped_nodes.Arguments`

        :param warning_node: The node to assign the warnings to
        :type warning_node: :class:`astroid.scoped_nodes.Node`

        :param accept_no_param_doc: Whether or not to allow no parameters
            to be documented.
            If None then this value is read from the configuration.
        :type accept_no_param_doc: bool or None
        """
        # Tolerate missing param or type declarations if there is a link to
        # another method carrying the same name.
        if not doc.doc:
            return

        if accept_no_param_doc is None:
            accept_no_param_doc = self.config.accept_no_param_doc
        tolerate_missing_params = doc.params_documented_elsewhere()

        # Collect the function arguments.
        expected_argument_names = set(arg.name for arg in arguments_node.args)
        expected_argument_names.update(arg.name for arg in arguments_node.kwonlyargs)
        not_needed_type_in_docstring = (
            self.not_needed_param_in_docstring.copy())

        if arguments_node.vararg is not None:
            expected_argument_names.append(arguments_node.vararg)
            not_needed_type_in_docstring.add(arguments_node.vararg)
        if arguments_node.kwarg is not None:
            expected_argument_names.append(arguments_node.kwarg)
            not_needed_type_in_docstring.add(arguments_node.kwarg)
        params_with_doc, params_with_type = doc.match_param_docs()

        # Tolerate no parameter documentation at all.
        if (not params_with_doc and not params_with_type
                and accept_no_param_doc):
            tolerate_missing_params = True

        def _compare_args(found_argument_names, message_id, not_needed_names):
            """Compare the found argument names with the expected ones and
            generate a message if there are inconsistencies.

            :param list found_argument_names: argument names found in the
                docstring

            :param str message_id: pylint message id

            :param not_needed_names: names that may be omitted
            :type not_needed_names: set of str
            """
            if not tolerate_missing_params:
                missing_or_differing_argument_names = (
                    (expected_argument_names ^ found_argument_names)
                    - not_needed_names)
            else:
                missing_or_differing_argument_names = (
                    (found_argument_names - expected_argument_names)
                    - not_needed_names)

            if missing_or_differing_argument_names:
                self.add_message(
                    message_id,
                    args=(', '.join(
                        sorted(missing_or_differing_argument_names)),),
                    node=warning_node)

        _compare_args(params_with_doc, 'missing-param-doc',
                      self.not_needed_param_in_docstring)
        _compare_args(params_with_type, 'missing-type-doc',
                      not_needed_type_in_docstring)

    def check_single_constructor_params(self, class_doc, init_doc, class_node):
        if class_doc.has_params() and init_doc.has_params():
            self.add_message(
                'multiple-constructor-doc',
                args=(class_node.name,),
                node=class_node)

    def _handle_no_raise_doc(self, excs, node):
        if self.config.accept_no_raise_doc:
            return

        self._add_all_raise_messages(excs, node)

    def _add_all_raise_messages(self, missing_excs, node):
        """
        Adds a message on :param:`node` for each exception type.

        :param missing_excs: A list of missing exception types.
        :type missing_excs: list

        :param node: The node show the messages on.
        """
        for missing_exc in missing_excs:
            self.add_message(
                'missing-raises-doc',
                args=(missing_exc,),
                node=node)

def register(linter):
    """Required method to auto register this checker.

    :param linter: Main interface object for Pylint plugins
    :type linter: Pylint object
    """
    linter.register_checker(DocstringChecker(linter))
