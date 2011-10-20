# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

import ez_setup
ez_setup.use_setuptools()

import sys, os, os.path, subprocess

try:
	from twisted import plugin
except ImportError, e:
	print >>sys.stderr, "setup.py requires Twisted to create a proper txsftp installation. Please install it before continuing."
	sys.exit(1)

from distutils import log
log.set_threshold(log.INFO)

# disables creation of .DS_Store files inside tarballs on Mac OS X
os.environ['COPY_EXTENDED_ATTRIBUTES_DISABLE'] = 'true'
os.environ['COPYFILE_DISABLE'] = 'true'

postgenerate_cache_commands = ('build', 'build_py', 'build_ext',
	'build_clib', 'build_scripts', 'install', 'install_lib',
	'install_headers', 'install_scripts', 'install_data',
	'develop', 'easy_install')

pregenerate_cache_commands = ('sdist', 'bdist', 'bdist_dumb',
	'bdist_rpm', 'bdist_wininst', 'upload', 'bdist_egg', 'test')

def autosetup():
	from setuptools import setup, find_packages
	return setup(
		name			= "txsftp",
		version			= "1.0",

		packages		= find_packages('src') + ['twisted.plugins'],
		package_dir		= {
			''			: 'src',
		},
		include_package_data = True,

		entry_points	= {
			'setuptools.file_finders'	: [
				'git = txsftp.setup:find_files_for_git',
			]
		},
		
		zip_safe		= False,
		
		install_requires = ['%s%s' % x for x in {
			'twisted'			: ">=11.0",
			'psycopg2'			: ">=2.4.1",
			'simplejson'		: ">=2.1.1",
			#'python-gnupg'		: ">=0.2.8",
		}.items()],
		
		# metadata for upload to PyPI
		author			= "Phil Christensen",
		author_email	= "phil@bubblehouse.org",
		url				= "https://github.com/philchristensen/txsftp",
	)


if(__name__ == '__main__'):
	if(sys.argv[-1] in pregenerate_cache_commands):
		dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
		if(dist_dir not in sys.path):
			sys.path.insert(0, dist_dir)

		from txsftp import setup
		print 'Regenerating plugin cache...'
		setup.regeneratePluginCache()

	dist = autosetup()
	if(sys.argv[-1] in postgenerate_cache_commands):
		subprocess.Popen(
			[sys.executable, '-c', 'from txsftp import setup; setup.regeneratePluginCache(); print "Regenerating plugin cache..."'],
		).wait()
