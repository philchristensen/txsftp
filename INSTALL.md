txsftp Installation
====================
by Phil Christensen
phil@bubblehouse.org

Requirements for Server
-----------------------

As long as you're using Python 2.5 or better, most recent versions of
everything else should work, but to be specific:

* [Python            >=  2.5  ](http://www.python.org)
* [PostgreSQL        >=  8.4  ](http://www.postgresql.org)
* [Twisted           >= 10.1  ](http://www.twistedmatrix.com)
* [psycopg2          >=  2.2.1](http://initd.org/psycopg)

Running the Server
-------------------

Once you install Python and Twisted, the rest will be taken care of by
the setuptools-based installer.

    pip install Twisted
    pip install --editable .

Next you should be able to start up the server with:

    twistd -n antioch

The -n will keep it in the foreground. Configuration options are kept in the 
global settings file, *default.json*.

> The default configuration looks for a PostgreSQL server on localhost:5432
