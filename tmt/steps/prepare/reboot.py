import dataclasses
from typing import Any, List, Optional

import click
import fmf
import json
import os

import tmt
import tmt.steps.prepare
import tmt.utils
import pkg_resources
from tmt.steps.provision import Guest
from tmt.steps.execute import TMT_REBOOT_SCRIPT

# File for requesting reboot
REBOOT_REQUEST_FILENAME = TMT_REBOOT_SCRIPT.created_file

# Scripts source directory
SCRIPTS_SRC_DIR = pkg_resources.resource_filename(
    'tmt', 'steps/execute/scripts')


# TODO: remove `ignore` with follow-imports enablement
@dataclasses.dataclass
class PrepareRebootData(tmt.steps.prepare.PrepareStepData):  # type: ignore[misc]
    script: List[str] = dataclasses.field(default_factory=list)

    _normalize_script = tmt.utils.NormalizeKeysMixin._normalize_string_list


@tmt.steps.provides_method('reboot')
class PrepareReboot(tmt.steps.prepare.PreparePlugin):  # type: ignore[misc]
    """
    Reboot system via provided script
    Example config:
    prepare:
        how: reboot
        script: ./reboot-script
    """

    _data_class = PrepareRebootData

    @classmethod
    def options(cls, how: Optional[str] = None) -> Any:
        """ Prepare command line options """
        return [
            click.option(
                '-n', '--name', metavar='NAME',
                help='Set name of the reboot step.'),
            click.option(
                '-n', '--script', metavar='NAME',
                help='Set path to the reboot script.')
            ] + super().options(how)

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option == 'name':
            return "Reboot script name"
        if option == 'reboot':
            return "reboot-script"
        return default

    def prepare_scripts(self, guest: "tmt.steps.provision.Guest") -> None:
        """
        Prepare additional scripts for testing
        """
        # Install all scripts on guest
        script = TMT_REBOOT_SCRIPT
        source = os.path.join(
            SCRIPTS_SRC_DIR, os.path.basename(script.path))

        for dest in [script.path] + script.aliases:
            guest.push(
                source=source,
                destination=dest,
                options=["-p", "--chmod=755"])

    def _will_reboot(self):
        """ True if reboot is requested """
        return os.path.exists(self._reboot_request_path())

    def _reboot_request_path(self):
        """ Return reboot_request """
        reboot_request_path = os.path.join(
            self.step.plan.data_directory,
            TMT_REBOOT_SCRIPT.created_file)
        return reboot_request_path

    def _handle_reboot(self, guest):
        """
        Reboot the guest if the test requested it.

        Check for presence of a file signalling reboot request
        and orchestrate the reboot if it was requested. Also increment
        REBOOTCOUNT variable, reset it to 0 if no reboot was requested
        (going forward to the next test). Return whether reboot was done.
        """
        if self._will_reboot():
            self._reboot_count += 1
            self.debug(f"Reboot during prepare step "
                       f"with reboot count {self._reboot_count}.")
            reboot_request_path = self._reboot_request_path()
            with open(reboot_request_path, 'r') as reboot_file:
                reboot_data = json.loads(reboot_file.read())
            reboot_command = reboot_data.get('command')
            try:
                timeout = int(reboot_data.get('timeout'))
            except ValueError:
                timeout = None
            # Reset the file
            data = os.path.join(
                self.step.plan.data_directory)
            os.remove(reboot_request_path)
            #guest.push(data)
            try:
                guest.reboot(command=reboot_command, timeout=timeout)
            except tmt.utils.RunError:
                self.fail(
                    f"Failed to reboot guest using the "
                    f"custom command '{reboot_command}'.")
                raise
            except tmt.utils.ProvisionError:
                self.warn(
                    "Guest does not support soft reboot, "
                    "trying hard reboot.")
                guest.reboot(hard=True, timeout=timeout)
            return True
        return False

    def go(self, guest: Guest) -> None:
        """ Prepare the guests """
        super().go(guest)

        # Prepare scripts, except localhost guest
        if not guest.localhost:
            self.prepare_scripts(guest)

        # Define and set reboot count
        if not hasattr(self, "_reboot_count"):
            self._reboot_count = 0

        # Set all supported reboot variables
        self.step.plan._environment["TMT_REBOOT_REQUEST"] = os.path.join(
            self.step.plan.data_directory,
            TMT_REBOOT_SCRIPT.created_file)
        for reboot_variable in TMT_REBOOT_SCRIPT.related_variables:
           self.step.plan._environment[reboot_variable] = str(self._reboot_count)

        # Execute script for reboot
        script = self.get("script")
        #self.verbose('script', script, 'green')
        #script_with_options = f'{tmt.utils.SHELL_OPTIONS}; {script}'
        try:
            #self.run(script, cwd=self.step.plan.worktree, env=self.step.plan.environment)
            guest.execute(script, cwd=self.step.plan.worktree)
        except:
            self.verbose("reboot script executed")
        guest.pull(source=self.step.plan.data_directory)

        #self.verbose(f"reboot? {self._will_reboot()}")
        self.verbose(f"file? {self._reboot_request_path()}")
        # Handle reboot, abort, exit-first
        if self._will_reboot():
            # Output before the reboot
            self.verbose("reboot in progress")
            self._handle_reboot(guest)