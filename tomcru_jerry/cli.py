import os.path
import sys
import argparse
import inspect

from .utils import import_from_dir


class CommandLineInterface():

    def load_commands(self, fbase='cliapp/', cls_suffix='Command', ctx=None):
        sys.path.append(fbase)

        if ctx is None:
            ctx = self

        self.commands = import_from_dir(ctx, cls_suffix, 'commands', path=os.path.join(fbase, cls_suffix.lower()+'s'), case_insensitive=True)

    def run_command(self, cmd_name, argv=None):
        if ':' in cmd_name:
            # subcommand
            cmd, subcmd = cmd_name.split(':')

            cmd_name = cmd#cmd.title()
            method_name = 'run_'+subcmd
        else:
            # main command
            #cmd_name = cmd#cmd_name.title()
            method_name = 'run'

        cmd_name = cmd_name.lower()

        if cmd_name not in self.commands:
            print(f"Est3: No command called {cmd_name}")
            return

        cmd = self.commands[cmd_name]
        parser = argparse.ArgumentParser(argv)

        if hasattr(cmd, 'add_arguments'):
            # let the user handle the cmd arguments:
            getattr(cmd, 'add_arguments')(parser)
        else:
            # default parameters are determined from method signature:
            sig = inspect.signature(getattr(cmd, method_name))

            for par_name, pee in sig.parameters.items():
                kwargs = {}
                argument = par_name

                if pee.default != inspect._empty:
                    kwargs['default'] = pee.default

                if pee.annotation != inspect._empty:
                    #if pee.annotation in (bool, str, int):
                    if pee.annotation is list:
                        kwargs['nargs'] = '+'
                    else:
                        kwargs['type'] = pee.annotation

                        if kwargs['type'] is bool:
                            argument = '--' + par_name
                            kwargs['action'] = argparse.BooleanOptionalAction
                        elif 'default' in kwargs:
                            argument = '--' + par_name
                            kwargs['required'] = False

                parser.add_argument(argument, **kwargs)

        # finally call the method using args
        method = getattr(cmd, method_name)

        if argv:
            # call method with arguments parsed with argparse
            args = parser.parse_args(argv)

            self.handle_arguments(**vars(args))
            method(**vars(args))
        else:
            # no command arguments
            self.handle_arguments()
            method()
        self.clean_up()

    def run(self, argv=None):
        if argv is None:
            argv = sys.argv
        argv = argv.copy()

        if len(argv) <= 1:
            print("Est3: No command called")
            return

        _script = argv.pop(0)
        cmd_name = argv.pop(0)

        self.run_command(cmd_name, argv)

    # def init_modules(self, modules, cliconf):
    #     for module in modules:
    #         module.init_dal()
    #
    #         if hasattr(module, 'init_cliapp'):
    #             module.init_cliapp(self, cliconf)

    def handle_arguments(self, **kwargs):
        pass

    def clean_up(self):
        pass
