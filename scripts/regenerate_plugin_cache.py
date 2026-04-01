#!/usr/bin/env python3
"""
Regenerate the Twisted plugin cache for txsftp.

Run this after installing or updating the package to ensure twistd can
discover the txsftp plugin:

    python scripts/regenerate_plugin_cache.py
"""

import traceback


def _plugin_modules(package_names):
    from twisted.python.reflect import namedAny
    for name in package_names:
        try:
            yield namedAny(name)
        except ImportError:
            pass
        except ValueError as e:
            if e.args[0] != 'Empty module name':
                traceback.print_exc()
        except Exception:
            traceback.print_exc()


def main():
    from twisted import plugin

    for mod in _plugin_modules(['twisted.plugins']):
        gen = plugin.getPlugins(plugin.IPlugin, mod)
        try:
            next(iter(gen))
        except StopIteration:
            pass
        except TypeError as e:
            print(f'TypeError: {e}')

    print('Plugin cache regenerated.')


if __name__ == '__main__':
    main()
