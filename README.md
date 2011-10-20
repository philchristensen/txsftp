txsftp 1.0
===========

17 October 2011

by Phil Christensen

`mailto:phil@bubblehouse.org`

txSFTP uses the extremely powerful Twisted networking library to create a
virtualized SFTP server where all users are configured via Postgres database,
chroot'ed into a limited directory, and run via an unprivileged service.

Additional features will include PGP/GPG support (to auto encrypt incoming/
outgoing files via a user-provided key), and IP range requirements (to require
VPN access).