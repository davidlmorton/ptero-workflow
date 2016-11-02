# PTero Workflow Service
[![Build Status](https://travis-ci.org/davidlmorton/ptero-workflow.svg?branch=master)](https://travis-ci.org/davidlmorton/ptero-workflow)
[![Coverage Status](https://coveralls.io/repos/github/davidlmorton/ptero-workflow/badge.svg?branch=master)](https://coveralls.io/github/davidlmorton/ptero-workflow?branch=master)
[![Requirements Status](https://requires.io/github/davidlmorton/ptero-workflow/requirements.svg?branch=master)](https://requires.io/github/davidlmorton/ptero-workflow/requirements/?branch=master)


This project provides the web API for the PTero Workflow system of services.

The workflows are driven using an implementation of [Petri
nets](https://en.wikipedia.org/wiki/Petri_net) with some extensions for
[color](https://en.wikipedia.org/wiki/Coloured_Petri_net) and token data.

The other existing components are: the [petri
core](https://github.com/davidlmorton/ptero-petri) service and a [forking shell
command](https://github.com/davidlmorton/ptero-shell-command) service.


## Testing

The tests for this service depend on a running petri and forking shell command
service.  To run the tests, first install some tools:

    pip install tox

Then setup the [petri](https://github.com/davidlmorton/ptero-petri) service and the
[shell-command](https://github.com/davidlmorton/ptero-shell-command) service. In the
parent directory:

    git clone https://github.com/davidlmorton/ptero-petri.git
    git clone https://github.com/davidlmorton/ptero-shell-command.git

And in the ptero-workflow directory:

    ln -s ../ptero-petri
    ln -s ../ptero-shell-command

Now, you can run the tests using tox:

    tox -e py27

To see a coverage report after successfully running the tests:

    coverage report
