# Development environment installation

Zulip supports a wide range of ways to install the Zulip development
environment.  We recommend using the Vagrant development environment,
since it is easiest to setup and uninstall.

If you have a very slow network connection, however, you may want to
avoid using Vagrant (which involves downloading an Ubuntu image) and
either [install directly](install-ubuntu-without-vagrant-dev.html) or
use [the manual install process](install-generic-unix-dev.html)
instead.  Note that those options only support Linux.

An alternative option if you have poor network connectivity is to rent a cloud server
(with at least 2GB of RAM), install
the [remote development environment](dev-remote.html), and connect to the
development environment over mosh or SSH.

#### For OS X

* [Detailed tutorial for Vagrant development environment](dev-env-first-time-contributors.html).  Recommended for first-time contributors.
* [Brief installation instructions for Vagrant development environment](brief-install-vagrant-dev.html)
* [Using Docker (experimental)](install-docker-dev.html)

#### For LINUX/ Other UNIX Platforms

* [Detailed tutorial for Vagrant development environment](dev-env-first-time-contributors.html).  Recommended for first-time contributors.
* [Brief installation instructions for Vagrant development environment](brief-install-vagrant-dev.html)
* [Installing on Ubuntu 14.04 Trusty or 16.04 Xenial directly](install-ubuntu-without-vagrant-dev.html).
  This offers the most convenient developer experience, but is difficult to uninstall.
* [Installing manually on other UNIX platforms](install-generic-unix-dev.html)
* [Using Docker (experimental)](install-docker-dev.html)

#### For Windows

* [Development on a Remove Environment](dev-remote.html).  Recommended for first-time contributors. Vagrant is usable on windows but can be tricky to setup.
* [Detailed tutorial for Vagrant development environment](dev-env-first-time-contributors.html)
* [Brief installation instructions for Vagrant development environment](brief-install-vagrant-dev.html)

## Using the Development Environment & Testing

Once you've installed the Zulip development environment, you'll want
to read these documents to learn how to use it:

* [Using the Development Environment](using-dev-environment.html)
* [Testing](testing.html)

