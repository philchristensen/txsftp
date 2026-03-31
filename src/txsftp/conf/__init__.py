# txsftp
# Copyright (c) 1999-2011 Phil Christensen
#
#
# See LICENSE for details

"""
JSON configuration file support.
"""

import sys, os.path, json
import importlib.resources as pkg_res

DEFAULT_CONF_PATH = '/etc/txsftp.json'

config = None

def load(path=DEFAULT_CONF_PATH):
	global config
	if(config):
		return config
	config = read_config(path)
	return config

def get(key):
	c = load()
	return c[key]

def read_config(path):
	result = {}

	ref = pkg_res.files('txsftp.conf').joinpath('default.json')
	with ref.open('r', encoding='utf-8') as f:
		result.update(_read_config(f))

	local_ref = pkg_res.files('txsftp.conf').joinpath('local.json')
	try:
		with local_ref.open('r', encoding='utf-8') as f:
			print("Loading local.json configuration...", file=sys.stderr)
			result.update(_read_config(f))
	except FileNotFoundError:
		pass

	if(os.path.exists(path)):
		print("Loading %s configuration..." % path, file=sys.stderr)
		with open(path) as f:
			result.update(_read_config(f))

	return result

def _read_config(f):
	try:
		c = json.load(f)
	except Exception as e:
		raise SyntaxError('config parse error: %s' % e)
	if(not isinstance(c, dict)):
		raise SyntaxError("config file doesn't contain a single top-level object.")
	return c
