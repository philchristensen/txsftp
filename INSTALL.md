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

    # pip install Twisted
    # pip install --editable .

Using psql, create a user and database for txsftp:

    txsftp=> CREATE USER txsftp WITH ENCRYPTED PASSWORD 'yuCrydCa';
    txsftp=> CREATE DATABASE txsftp WITH OWNER txsftp;

Then import the database schema and initial data:

    # psql -U txsftp < src/txsftp/conf/schema.psql

Next you should be able to start up the server with:

    # twistd -n antioch

The -n will keep it in the foreground. Configuration options are kept in the 
global settings file, *default.json*.

> The default configuration looks for a PostgreSQL server on localhost:5432

Finally, test that the installation is working by running the command-line SFTP client:

    # sftp -oPort=8888 -oIdentityFile=./client_rsa -oUser=user localhost

You should be logged into the home directory provided to the user, with no ability to
change the root directory, create symlinks, or set uid/gid.