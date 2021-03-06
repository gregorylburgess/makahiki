#!/usr/bin/python

"""Invocation: scripts/verify.py

Runs pep8, pylint, and tests.
If all are successful, there is no output and program terminates normally.
If any errors, prints output from unsuccessful programs and exits with non-zero error code.
"""

import sys
import os
import getopt


def main(argv):
    """Verify main function. Usage: verify.py [-v | --verbose]"""
    verbose = 0
    try:
        opts, _ = getopt.getopt(argv, "v", ["verbose"])
    except getopt.GetoptError:
        print "Usage verify.py [-v | --verbose]"
        sys.exit(2)

    for opt, _ in opts:
        if opt in ("-v", "--verbose"):
            verbose = 1

    if verbose == 1:
        print "running pep8"
    pep8_command = os.path.join("scripts", "run_pep8.sh")
    status = os.system(pep8_command)
    if status:
        sys.exit(1)

    if verbose == 1:
        print "running pylint"
    pylint_command = os.path.join("scripts", "run_pylint.sh")
    status = os.system(pylint_command)
    if status:
        sys.exit(1)

    if verbose == 1:
        print "cleaning"
    os.system("python manage.py clean_pyc")

    if verbose == 1:
        print "running tests"
    status = os.system("python manage.py test")
    if status:
        sys.exit(1)

    if verbose == 1:
        print "building docs"
    status = os.system("pushd .; cd ../doc; make clean html; popd;")
    if status:
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
