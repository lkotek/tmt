from typing import Any, List, Optional

import click
import fmf

import tmt
import tmt.steps.prepare
import tmt.utils
from tmt.steps.provision import Guest


class PrepareRepository(tmt.steps.prepare.PreparePlugin):  # type: ignore[misc]
    """
    Prepare custom repository

    Example config:

    prepare:
        how: repository
        name: Local repository
        baseurl: file:///repository"
        order: 1
        priority: 99

    """

    # Supported methods
    _methods = [tmt.steps.Method(name='repository', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["name", "baseurl", "order", "priority"]

    @classmethod
    def options(cls, how: Optional[str] = None) -> Any:
        """ Prepare command line options """
        return [
            click.option(
                '-n', '--name', metavar='NAME',
                help='Set name of repository.'),
            click.option(
                '-u', '--baseurl', metavar='BASEURL',
                help='Set baseurl of the repository.'),
            click.option(
                '-o', '--order', metavar='ORDER',
                help='Set order of the repository.'),
            click.option(
                '-p', '--priority', metavar='PRIORITY',
                help='Set priority of the repository.')
            ] + super().options(how)

    def default(self, option: str, default: Optional[Any] = None) -> Any:
        """ Return default data for given option """
        if option == 'name':
            return "Repository"
        if option == 'baseurl':
            return "file:///repository"
        if option == 'order':
            return 1
        if option == 'priority':
            return 99
        return default

    def wake(self, keys: Optional[List[str]] = None) -> None:
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)

        # Convert to list if necessary
        """
        tmt.utils.listify(
            self.data, split=True,
            keys=['name', 'baseurl', 'order', 'priority'])
        """

    def go(self, guest: Guest) -> None:
        """ Prepare the guests """
        super().go(guest)

        #self.info("Add repository into '/etc/yum.repos.d'.")
        repo_path = "/etc/yum.repos.d/demo.repo"
        guest.execute(f"touch {repo_path}")
        guest.execute(f'echo "[demo]" >> {repo_path}')
        for key in self._keys:
            guest.execute(f'echo "{key}={self.get(key)}" >> {repo_path}')
