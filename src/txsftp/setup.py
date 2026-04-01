import os, os.path, subprocess, warnings
from typing import Any, Generator

has_git: bool | None = None

def find_files_for_git(dirname: str) -> Generator[str, None, None]:
    global has_git
    if(has_git is None):
        git = subprocess.Popen(['env', 'git', '--version'], stdout=subprocess.PIPE)
        git.wait()
        has_git = (git.returncode == 0)
    if(has_git):
        git = subprocess.Popen(['git', 'ls-files', dirname], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert git.stdout is not None
        for line in git.stdout:
            path = os.path.join(dirname, line.strip().decode('utf-8'))
            yield path
    else:
        warnings.warn("Can't find git binary.")

def pluginModules(moduleNames: list[str]) -> Generator[Any, None, None]:
    from twisted.python.reflect import namedAny
    for moduleName in moduleNames:
        try:
            yield namedAny(moduleName)
        except ImportError:
            pass
        except ValueError as ve:
            if ve.args[0] != 'Empty module name':
                import traceback
                traceback.print_exc()
        except:
            import traceback
            traceback.print_exc()

def regeneratePluginCache() -> None:
    pluginPackages = ['twisted.plugins']

    from twisted import plugin

    for pluginModule in pluginModules(pluginPackages):
        plugin_gen = plugin.getPlugins(plugin.IPlugin, pluginModule)
        try:
            next(iter(plugin_gen))
        except StopIteration:
            pass
        except TypeError as e:
            print('TypeError: %s' % e)
