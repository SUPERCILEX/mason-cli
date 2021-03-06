import tempfile

from cli.config import Config
from cli.internal.commands.build import BuildCommand
from cli.internal.commands.command import Command
from cli.internal.commands.register import RegisterCommand
from cli.internal.commands.register import RegisterConfigCommand
from cli.internal.utils.io import wait_for_futures


class StageCommand(RegisterCommand):
    def __init__(
        self,
        config: Config,
        config_files: list,
        block: bool,
        mason_version: str,
        working_dir=None
    ):
        super(StageCommand, self).__init__(config)

        self.config_files = config_files
        self.block = block
        self.mason_version = mason_version
        self.working_dir = working_dir or tempfile.mkdtemp()

    @Command.helper('stage')
    def run(self):
        return super(StageCommand, self).run()

    def prepare(self):
        register = RegisterConfigCommand(self.config, self.config_files, self.working_dir)
        return (*register.prepare(), register)

    def register(self, configs: list, register: RegisterConfigCommand):
        register.register(configs)

        build_ops = []

        for config in configs:
            build_command = BuildCommand(
                self.config,
                config.get_name(),
                config.get_version(),
                self.block,
                self.mason_version)

            build_ops.append(self.config.executor.submit(self._build, build_command))

        wait_for_futures(self.config.executor, build_ops)

    def _build(self, build_command: BuildCommand):
        self.config.logger.info('')
        build_command.build()
