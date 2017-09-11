# Copyright (c) 2006-2010, 2012-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2014-2016 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2015 Aru Sahni <arusahni@gmail.com>

# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/master/COPYING

"""utilities for Pylint configuration :

* pylintrc
* pylint.d (PYLINTHOME)
"""
from __future__ import print_function

import abc
import argparse
import contextlib
import collections
import copy
import functools
import io
import numbers
import os
import pickle
import re
import sys
import time

import configparser
import six
from six.moves import range

from pylint import exceptions, utils


USER_HOME = os.path.expanduser('~')
if 'PYLINTHOME' in os.environ:
    PYLINT_HOME = os.environ['PYLINTHOME']
    if USER_HOME == '~':
        USER_HOME = os.path.dirname(PYLINT_HOME)
elif USER_HOME == '~':
    PYLINT_HOME = ".pylint.d"
else:
    PYLINT_HOME = os.path.join(USER_HOME, '.pylint.d')


def _get_pdata_path(base_name, recurs):
    base_name = base_name.replace(os.sep, '_')
    return os.path.join(PYLINT_HOME, "%s%s%s"%(base_name, recurs, '.stats'))


def load_results(base):
    data_file = _get_pdata_path(base, 1)
    try:
        with open(data_file, _PICK_LOAD) as stream:
            return pickle.load(stream)
    except Exception: # pylint: disable=broad-except
        return {}

if sys.version_info < (3, 0):
    _PICK_DUMP, _PICK_LOAD = 'w', 'r'
else:
    _PICK_DUMP, _PICK_LOAD = 'wb', 'rb'

def save_results(results, base):
    if not os.path.exists(PYLINT_HOME):
        try:
            os.mkdir(PYLINT_HOME)
        except OSError:
            print('Unable to create directory %s' % PYLINT_HOME, file=sys.stderr)
    data_file = _get_pdata_path(base, 1)
    try:
        with open(data_file, _PICK_DUMP) as stream:
            pickle.dump(results, stream)
    except (IOError, OSError) as ex:
        print('Unable to create file %s: %s' % (data_file, ex), file=sys.stderr)


def find_pylintrc_in(search_dir):
    """Find a pylintrc file in the given directory.

    :param search_dir: The directory to search.
    :type search_dir: str

    :returns: The path to the pylintrc file, if found. Otherwise None.
    :rtype: str or None
    """
    path = None

    search_dir = os.path.expanduser(search_dir)
    if os.path.isfile(os.path.join(search_dir, 'pylintrc')):
        path = os.path.join(search_dir, 'pylintrc')
    elif os.path.isfile(os.path.join(search_dir, '.pylintrc')):
        path = os.path.join(search_dir, '.pylintrc')

    return path


def find_nearby_pylintrc(search_dir=''):
    """Search for the nearest pylint rc file.

    :param search_dir: The directory to search.
    :type search_dir: str

    :returns: The absolute path to the pylintrc file, if found.
        Otherwise None
    :rtype: str or None
    """
    search_dir = os.path.expanduser(search_dir)
    path = find_pylintrc_in(search_dir)

    if not path:
        for search_dir in utils.walk_up(search_dir):
            if not os.path.isfile(os.path.join(search_dir, '__init__.py')):
                break
            path = find_pylintrc_in(search_dir)
            if path:
                break

    if path:
        path = os.path.abspath(path)

    return path


def find_global_pylintrc():
    """Search for the global pylintrc file.

    :returns: The absolute path to the pylintrc file, if found. Otherwise None.
    :rtype: str or None
    """
    pylintrc = None

    if 'PYLINTRC' in os.environ and os.path.isfile(os.environ['PYLINTRC']):
        pylintrc = os.environ['PYLINTRC']
    else:
        search_dirs = ('~', os.path.join('~', '.config'), '/etc/pylintrc')
        for search_dir in search_dirs:
            path = find_pylintrc_in(search_dir)
            if path:
                pylintrc = path
                break

    return pylintrc


def find_pylintrc():
    """Search for a pylintrc file.
    The locations searched are, in order:
    - The current directory
    - Each parent directory that contains a __init__.py file
    - The value of the `PYLINTRC` environment variable
    - The current user's home directory
    - The `.config` folder in the current user's home directory
    - /etc/pylintrc

    :returns: The path to the pylintrc file, or None if one was not found.
    :rtype: str or None
    """
    # TODO: Find nearby pylintrc files as well
    #return find_nearby_pylintrc() or find_global_pylintrc()
    return find_global_pylintrc()


PYLINTRC = find_pylintrc()

ENV_HELP = '''
The following environment variables are used:
    * PYLINTHOME
    Path to the directory where the persistent for the run will be stored. If
not found, it defaults to ~/.pylint.d/ or .pylint.d (in the current working
directory).
    * PYLINTRC
    Path to the configuration file. See the documentation for the method used
to search for configuration file.
''' % globals()


def _multiple_choice_validator(choices, name, value):
    values = utils._check_csv(value)
    for csv_value in values:
        if csv_value not in choices:
            msg = "option %s: invalid value: %r, should be in %s"
            raise argparse.ArgumentError(msg % (name, csv_value, choices), name)
    return values


# pylint: disable=unused-argument
def _csv_validator(value):
    return utils._check_csv(value)


# pylint: disable=unused-argument
def _regexp_validator(value):
    if hasattr(value, 'pattern'):
        return value
    return re.compile(value)

# pylint: disable=unused-argument
def _regexp_csv_validator(value):
    return [_regexp_validator(val) for val in _csv_validator(value)]

def _yn_validator(value):
    if isinstance(value, int):
        return bool(value)
    if value in ('y', 'yes'):
        return True
    if value in ('n', 'no'):
        return False
    import pdb
    pdb.set_trace()
    msg = "Invalid yn value %r, should be in (y, yes, n, no)"
    raise exceptions.ConfigurationError(msg % value)


def _file_yn_validator(value):
    # OptionParser does some converting of it's own so translate that first.
    if value in ('1', 'True'):
        return True
    if value in ('0', 'False'):
        return False
    return _yn_validator(value)


def _non_empty_string_validator(value):
    if not value:
        msg = "indent string can't be empty."
        raise exceptions.ConfigurationError(msg)
    return utils._unquote(value)


VALIDATORS = {
    'string': utils._unquote,
    'int': int,
    'regexp': re.compile,
    'regexp_csv': _regexp_csv_validator,
    'csv': _csv_validator,
    'yn': _yn_validator,
    'multiple_choice': _multiple_choice_validator,
    'non_empty_string': _non_empty_string_validator,
}


class OptionsManagerMixIn(object):
    """Handle configuration from both a configuration file and command line options"""

    def __init__(self, usage, config_file=None, version=None, quiet=0):
        self.config_file = config_file
        self.reset_parsers(usage, version=version)
        # list of registered options providers
        self.options_providers = []
        # dictionary associating option name to checker
        self._all_options = collections.OrderedDict()
        self._short_options = {}
        # TODO: Move this to the runner when this class is removed.
        self._global_config = Configuration()
        # verbosity
        self.quiet = quiet

    def reset_parsers(self, usage='', version=None):
        # configuration file parser
        self.cfgfile_parser = IniFileParser()
        # command line parser
        self.cmdline_parser = CLIParser(usage)

    def register_options_provider(self, provider, own_group=True):
        """register an options provider"""
        assert provider.priority <= 0, "provider's priority can't be >= 0"
        provider.config = self._global_config
        for i in range(len(self.options_providers)):
            if provider.priority > self.options_providers[i].priority:
                self.options_providers.insert(i, provider)
                break
        else:
            self.options_providers.append(provider)

        self.cmdline_parser.add_option_definitions(provider.options)
        self.cfgfile_parser.add_option_definitions(provider.options)

        # Set the defaults
        these_options = [option for option, _ in provider.options]
        default_config = self.cmdline_parser.get_defaults(*these_options)
        provider.config += default_config

    def generate_config(self, stream=None, skipsections=(), encoding=None):
        """write a configuration file according to the current configuration
        into the given stream or stdout
        """
        options_by_section = {}
        sections = []
        for provider in self.options_providers:
            for section, options in provider.options_by_section():
                if section is None:
                    section = provider.name
                if section in skipsections:
                    continue
                options = [(n, d, v) for (n, d, v) in options
                           if d.get('type') is not None
                           and not d.get('deprecated')]
                if not options:
                    continue
                if section not in sections:
                    sections.append(section)
                alloptions = options_by_section.setdefault(section, [])
                alloptions += options
        stream = stream or sys.stdout
        encoding = utils._get_encoding(encoding, stream)
        printed = False
        for section in sections:
            if printed:
                print('\n', file=stream)
            utils.format_section(stream, section.upper(),
                                 sorted(options_by_section[section]),
                                 encoding)
            printed = True

    def generate_manpage(self, pkginfo, section=1, stream=None):
        # TODO
        raise NotImplementedError

    def load_config_file(self, config_file=None):
        """Read the configuration file.

        :param config_file: The path to the config file to read.
        :type config_file: str
        """
        if config_file is None:
            config_file = self.config_file
        if config_file is not None:
            config_file = os.path.expanduser(config_file)

        use_config_file = config_file and os.path.exists(config_file)
        if use_config_file:
            self.cfgfile_parser.parse(config_file, self._global_config)

        if self.quiet:
            return

        if use_config_file:
            msg = 'Using config file {0}'.format(os.path.abspath(config_file))
        else:
            msg = 'No config file found, using default configuration'
        print(msg, file=sys.stderr)


    def load_configuration(self, **kwargs):
        """override configuration according to given parameters"""
        return self.load_configuration_from_config(kwargs)

    def load_configuration_from_config(self, config):
        for opt, opt_value in config.items():
            opt = opt.replace('_', '-')
            provider = self._all_options[opt]
            provider.config.set_option(opt, opt_value)

    def load_command_line_configuration(self, args=None):
        """Override configuration according to command line parameters

        return additional arguments
        """
        if args is None:
            args = sys.argv[1:]
        else:
            args = list(args)
        self.cmdline_parser.parse(args, self._global_config)
        return self._global_config.module_or_package

    def add_help_section(self, title, description, level=0):
        """add a dummy option section for help purpose """
        group = self.cmdline_parser._parser.add_argument_group(
            title.capitalize(), description, level=level
        )

    def help(self, level=0):
        """return the usage string for available options """
        return self.cmdline_parser._parser.format_help(level)


class OptionsProviderMixIn(object):
    """Mixin to provide options to an OptionsManager"""

    # those attributes should be overridden
    priority = -1
    name = 'default'
    options = ()
    level = 0

    def __init__(self):
        self.config = None

    def option_attrname(self, opt, optdict=None):
        """get the config attribute corresponding to opt"""
        if optdict is None:
            optdict = self.get_option_def(opt)
        return optdict.get('dest', opt.replace('-', '_'))

    def option_value(self, opt):
        """get the current value for the given option"""
        return getattr(self.config, self.option_attrname(opt), None)

    def get_option_def(self, opt):
        """return the dictionary defining an option given its name"""
        assert self.options
        for option in self.options:
            if option[0] == opt:
                return option[1]
        raise argparse.ArgumentError('no such option %s in section %r'
                                   % (opt, self.name), opt)

    def options_by_section(self):
        """return an iterator on options grouped by section

        (section, [list of (optname, optdict, optvalue)])
        """
        sections = {}
        for optname, optdict in self.options:
            sections.setdefault(optdict.get('group'), []).append(
                (optname, optdict, self.option_value(optname)))
        if None in sections:
            yield None, sections.pop(None)
        for section, options in sorted(sections.items()):
            yield section.upper(), options

    def options_and_values(self, options=None):
        if options is None:
            options = self.options
        for optname, optdict in options:
            yield (optname, optdict, self.option_value(optname))


class ConfigurationMixIn(OptionsManagerMixIn, OptionsProviderMixIn):
    """basic mixin for simple configurations which don't need the
    manager / providers model
    """
    def __init__(self, *args, **kwargs):
        if not args:
            kwargs.setdefault('usage', '')
        kwargs.setdefault('quiet', 1)
        OptionsManagerMixIn.__init__(self, *args, **kwargs)
        OptionsProviderMixIn.__init__(self)
        if not getattr(self, 'option_groups', None):
            self.option_groups = []
            for _, optdict in self.options:
                try:
                    gdef = (optdict['group'].upper(), '')
                except KeyError:
                    continue
                if gdef not in self.option_groups:
                    self.option_groups.append(gdef)
        self.register_options_provider(self, own_group=False)


OptionDefinition = collections.namedtuple(
    'OptionDefinition', ['name', 'definition']
)


class Configuration(object):
    def set_option(self, option, value):
        setattr(self, option, value)

    def copy(self):
        result = self.__class__()

        for option in self.__dict__:
            value = getattr(self, option)
            setattr(result, option, value)

        return result

    def update(self, other):
        self += other

    def __add__(self, other):
        result = self.copy()
        result += other
        return result

    def __iadd__(self, other):
        for option in other.__dict__:
            value = getattr(other, option, None)
            setattr(self, option, value)

        return self

    def __repr__(self):
        this = self.__class__.__name__
        items = sorted(self.__dict__.items())
        items = ', '.join('{}={}'.format(k, repr(v)) for k, v in items)
        return '{}({})'.format(this, items)


class ConfigurationStore(object):
    def __init__(self, global_config):
        """A class to store configuration objects for many paths.

        :param global_config: The global configuration object.
        :type global_config: Configuration
        """
        self.global_config = global_config

        self._store = {}
        self._cache = {}

    def add_config_for(self, path, config):
        """Add a configuration object to the store.

        :param path: The path to add the config for.
        :type path: str
        :param config: The config object for the given path.
        :type config: Configuration
        """
        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        self._store[path] = config
        self._cache = {}

    def _get_parent_configs(self, path):
        """Get the config objects for all parent directories.

        :param path: The absolute path to get the parent configs for.
        :type path: str

        :returns: The config objects for all parent directories.
        :rtype: generator(Configuration)
        """
        for cfg_dir in utils.walk_up(path):
            if cfg_dir in self._cache:
                yield self._cache[cfg_dir]
                break
            elif cfg_dir in self._store:
                yield self._store[cfg_dir]

    def get_config_for(self, path):
        """Get the configuration object for a file or directory.
        This will merge the global config with all of the config objects from
        the root directory to the given path.

        :param path: The file or directory to the get configuration object for.
        :type path: str

        :returns: The configuration object for the given file or directory.
        :rtype: Configuration
        """
        # TODO: Until we turn on local pylintrc searching,
        # this is always going to be the global config
        return self.global_config

        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        config = self._cache.get(path)

        if not config:
            config = self.global_config.copy()

            parent_configs = self._get_parent_configs(path)
            for parent_config in reversed(parent_configs):
                config += parent_config

            self._cache['path'] = config

        return config

    def __getitem__(self, path):
        return self.get_config_for(path)

    def __setitem__(self, path, config):
        return self.add_config_for(path, config)


@six.add_metaclass(abc.ABCMeta)
class ConfigParser(object):
    def __init__(self):
        self._option_definitions = {}
        self._option_groups = set()

    def add_option_definitions(self, option_definitions):
        self._option_definitions.update(option_definitions)

        self._option_groups.update(
            d['group'].upper() for _, d in option_definitions if 'group' in d
        )

    def add_option_definition(self, option_definition):
        self.add_option_definitions([option_definition])

    @staticmethod
    def _get_type_func(option_definition):
        """Get the type function for an option definition.

        :param option_definition: The option definition to get the
            type function for.
        :type param: OptionDefinition

        :returns: The type function, which takes a single argument,
            or None if one has not been configured.
        :rtype: callable or None

        :raises ConfigurationError: When the option definition is invalid.
        """
        type_ = None

        option, definition = option_definition

        if 'type' in definition:
            if definition['type'] in ('choice', 'multiple_choice'):
                if 'choices' not in definition:
                    msg = 'No choice list given for option "{0}" of type "choice".'
                    msg = msg.format(option)
                    raise ConfigurationError(msg)

                if definition['type'] == 'multiple_choice':
                    validator = VALIDATORS[definition['type']]
                    type_ = functools.partial(
                        validator, definition['choices'], option,
                    )
            elif definition['type'] in VALIDATORS:
                type_ = VALIDATORS[definition['type']]
            else:
                msg = 'Unsupported type "{0}"'.format(definition['type'])
                raise ConfigurationError(msg)

        return type_

    @abc.abstractmethod
    def parse(self, to_parse, config):
        """Parse the given object into the config object.

        :param to_parse: The object to parse.
        :type to_parse: object
        :param config: The config object to parse into.
        :type config: Configuration
        """


class CLIParser(ConfigParser):

    def __init__(self, usage=''):
        super(CLIParser, self).__init__()

        self._parser = LongHelpArgumentParser(
            usage=usage.replace("%prog", "%(prog)s"),
            # Only set the arguments that are specified.
            argument_default=argparse.SUPPRESS
        )
        # TODO: Let this be definable elsewhere
        self._parser.add_argument('module_or_package', nargs=argparse.REMAINDER)

    def add_option_definitions(self, option_definitions):
        self._option_definitions.update(option_definitions)
        option_groups = collections.defaultdict(list)

        for option, definition in option_definitions:
            group, args, kwargs = self._convert_definition(option, definition)
            option_groups[group].append((args, kwargs))

        for args, kwargs in option_groups['DEFAULT']:
            self._parser.add_argument(*args, **kwargs)

        del option_groups['DEFAULT']

        # TODO: Allow subsequent calls to this.
        # (ie store groups to update later).
        for group, arguments in six.iteritems(option_groups):
            self._option_groups.add(group)
            # TODO: Level from provider
            self._parser.add_argument_group(group.title())
            for args, kwargs in arguments:
                self._parser.add_argument(*args, **kwargs)

    @classmethod
    def _convert_definition(cls, option, definition):
        """Convert an option definition to a set of arguments for add_argument.

        :param option: The name of the option
        :type option: str
        :param definition: The argument definition to convert.
        :type definition: dict

        :returns: A tuple of the group to add the argument to,
            plus the args and kwargs for :func:`ArgumentParser.add_argument`.
        :rtype: tuple(str, list, dict)

        :raises ConfigurationError: When the definition is invalid.
        """
        args = []

        if 'short' in definition:
            args.append('-{0}'.format(definition['short']))

        args.append('--{0}'.format(option))

        copy_keys = ('action', 'dest', 'help', 'metavar', 'level')
        kwargs = {k: definition[k] for k in copy_keys if k in definition}

        if 'type' in definition:
            kwargs['type'] = cls._get_type_func((option, definition))
            if definition['type'] in ('choice', 'multiple_choice'):
                kwargs['choices'] = definition['choices']

        if definition.get('action') == 'callback':
            callback = definition['callback']
            kwargs['action'] = functools.partial(CallbackAction, callback)

        if definition.get('hide'):
            kwargs['help'] = argparse.SUPPRESS

        group = definition.get('group', 'DEFAULT').upper()

        # Some sanity checks for things that trip up argparse
        assert not any(' ' in arg for arg in args)
        assert not ('metavar' in kwargs and '[' in kwargs['metavar'])

        return group, args, kwargs

    def parse(self, argv, config):
        """Parse the command line arguments into the given config object.

        :param argv: The command line arguments to parse.
        :type argv: list(str)
        :param config: The config object to parse the command line into.
        :type config: Configuration
        """
        self._parser.parse_args(argv, config)

    def preprocess(self, argv):
        """Do some guess work to get a value for the specified option.

        :param argv: The command line arguments to parse.
        :type argv: list(str)

        :returns: A config with the processed options.
        :rtype: Configuration
        """
        config = Configuration()

        args = self._parser.parse_known_args(argv)[0]
        for option in vars(args):
            config.set_option(option, getattr(args, option, None))

        return config

    def get_defaults(self, *options):
        """Get the default values for the given options.

        .. note::
            This will call any callback functions.

        :param options: The names options to get default values for.
        :type options: str

        :returns: The default values set on a config object.
        :rtype: Configuration
        """
        config = Configuration()

        # Use a new parser so that we can temporarily get defaults
        parser = argparse.ArgumentParser()

        for option in options:
            option_definition = self._option_definitions[option]
            _, args, kwargs = self._convert_definition(option, option_definition)
            if 'default' in option_definition:
                kwargs['default'] = option_definition['default']
            kwargs.pop('level', None)
            parser.add_argument(*args, **kwargs)

        args = parser.parse_known_args([])[0]
        for option in vars(args):
            config.set_option(option, getattr(args, option, None))

        return config


@six.add_metaclass(abc.ABCMeta)
class FileParser(ConfigParser):
    @abc.abstractmethod
    def parse(self, file_path, config):
        pass


class IniFileParser(FileParser):
    """Parses a config files into config objects."""

    def __init__(self):
        super(IniFileParser, self).__init__()
        self._parser = configparser.ConfigParser(
            inline_comment_prefixes=('#', ';'),
        )

    def add_option_definitions(self, option_definitions):
        self._option_definitions.update(option_definitions)

        for option, definition in option_definitions:
            group, default = self._convert_definition(option, definition)

            if group != 'DEFAULT':
                try:
                    self._parser.add_section(group)
                except configparser.DuplicateSectionError:
                    pass
                else:
                    self._option_groups.add(group)

            if default:
                self._parser['DEFAULT'].update(default)

    @staticmethod
    def _convert_definition(option, definition):
        """Convert an option definition to a set of arguments for the parser.

        :param option: The name of the option.
        :type option: str
        :param definition: The argument definition to convert.
        :type definition: dict

        :returns: The converted definition.
        :rtype: tuple(str, dict or None)
        """
        default = definition.get('default')
        if isinstance(default, (list, tuple)):
            default = ','.join(default)
        elif isinstance(default, numbers.Number):
            default = str(default)
        elif isinstance(default, type(re.compile('a'))):
            default = default.pattern

        if default is not None:
            default = {option: default}

        group = definition.get('group', 'DEFAULT').upper()
        return group, default

    @classmethod
    def _get_type_func(cls, option_definition):
        type_ = super(IniFileParser, cls)._get_type_func(option_definition)

        if type_:
            definition = option_definition[1]
            if definition['type'] == 'yn':
                type_ = _file_yn_validator

        return type_

    def parse(self, file_path, config):
        self._parser.read(file_path)

        for section in self._parser.sections():
            # Normalise the section titles
            if not section.isupper():
                new_section = section.upper()
                for option, value in self._parser.items(section):
                    self._parser.set(new_section, option, value)
                self._parser.remove_section(section)
                section = section.upper()

            for option, value in self._parser.items(section):
                if option not in self._option_definitions:
                    continue

                definition = self._option_definitions[option]
                type_ = self._get_type_func((option, definition))
                if type_:
                    value = type_(value)
                # TODO: Call relevant Action
                if definition.get('callback'):
                    callback = definition['callback']
                    value = callback(None, option, value, None)

                config.set_option(option, value)


class LongHelpFormatter(argparse.HelpFormatter):
    output_level = None

    def add_argument(self, action):
        if action.level <= self.output_level:
            super(LongHelpFormatter, self).add_argument(action)

    def add_usage(self, usage, actions, groups, prefix=None):
        actions = [action for action in actions if action.level <= self.output_level]
        super(LongHelpFormatter, self).add_usage(
            usage, actions, groups, prefix,
        )


class LongHelpAction(argparse.Action):
    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None,
                 nargs=0,
                 level=0,
                 **kwargs
                 ):
        super(LongHelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            help=help,
            nargs=nargs,
            **kwargs
        )
        self.level = level

    @staticmethod
    def _parse_option_string(option_string):
        level = 0
        if option_string:
            level = option_string.count('l-') or option_string.count('long-')
        return level

    @staticmethod
    def build_add_args(level, prefix_chars='-'):
        default_prefix = '-' if '-' in prefix_chars else prefix_chars[0]
        return (
            default_prefix + '-'.join(['l'] * level) + '-h',
            default_prefix * 2 + '-'.join(['long'] * level) + '-help',
        )

    def __call__(self, parser, namespace, values, option_string=None):
        level = self._parse_option_string(option_string)
        parser.print_help(level=level)
        parser.exit()


class LongHelpArgumentParser(argparse.ArgumentParser):
    def __init__(self, formatter_class=LongHelpFormatter, **kwargs):
        self._max_level = 0
        super(LongHelpArgumentParser, self).__init__(
            formatter_class=formatter_class, **kwargs
        )

    # Stop ArgumentParser __init__ adding the wrong help formatter
    def register(self, registry_name, value, object):
        if registry_name == 'action' and value == 'help':
            object = LongHelpAction

        super(LongHelpArgumentParser, self).register(
            registry_name, value, object
        )

    def _add_help_levels(self):
        level = max(action.level for action in self._actions)
        if level > self._max_level and self.add_help:
            for new_level in range(self._max_level + 1, level + 1):
                action = super(LongHelpArgumentParser, self).add_argument(
                    *LongHelpAction.build_add_args(new_level, self.prefix_chars),
                    action='help',
                    default=argparse.SUPPRESS,
                    help=('show a {0} verbose help message and exit'.format(
                        ' '.join(['really'] * (new_level - 1))
                    ))
                )
                action.level = 0
            self._max_level = level

    def parse_known_args(self, *args, **kwargs):
        self._add_help_levels()
        return super(LongHelpArgumentParser, self).parse_known_args(
            *args, **kwargs
        )

    def add_argument(self, *args, **kwargs):
        """See :func:`argparse.ArgumentParser.add_argument`.

        Patches in the level to each created action instance.

        :returns: The created action.
        :rtype: argparse.Action
        """
        level = kwargs.pop('level', 0)
        action = super(LongHelpArgumentParser, self).add_argument(*args, **kwargs)
        action.level = level
        return action

    def add_argument_group(self, *args, **kwargs):
        level = kwargs.pop('level', 0)
        group = super(LongHelpArgumentParser, self).add_argument_group(
            *args, **kwargs
        )
        group.level = level
        return group

    # These methods use yucky way of passing the level to the formatter class
    # without having to rely on argparse implementation details.
    def format_usage(self, level=0):
        if hasattr(self.formatter_class, 'output_level'):
            if self.formatter_class.output_level is None:
                self.formatter_class.output_level = level
        return super(LongHelpArgumentParser, self).format_usage()

    def format_help(self, level=0):
        if hasattr(self.formatter_class, 'output_level'):
            if self.formatter_class.output_level is None:
                self.formatter_class.output_level = level
            else:
                level = self.formatter_class.output_level

        # Unfortunately there's no way of publicly accessing the groups or
        # an easy way of overriding format_help without using protected methods.
        old_action_groups = self._action_groups
        try:
            self._action_groups = [group for group in self._action_groups if group.level <= level]
            result = super(LongHelpArgumentParser, self).format_help()
        finally:
            self._action_groups = old_action_groups

        return result

    def print_usage(self, file=None, level=0):
        if hasattr(self.formatter_class, 'output_level'):
            if self.formatter_class.output_level is None:
                self.formatter_class.output_level = level
        super(LongHelpArgumentParser, self).print_usage(file)

    def print_help(self, file=None, level=0):
        if hasattr(self.formatter_class, 'output_level'):
            if self.formatter_class.output_level is None:
                self.formatter_class.output_level = level
        super(LongHelpArgumentParser, self).print_help(file)


class CallbackAction(LongHelpAction):
    """Doesn't store the value on the config."""
    def __init__(self, callback, nargs=None, **kwargs):
        self._callback = callback
        nargs = nargs or int('metavar' in kwargs)
        super(CallbackAction, self).__init__(
            nargs=nargs, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string):
        self._callback(self, option_string, values, parser)
        return values
