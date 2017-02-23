========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |
        |
    * - package
      - | |version| |downloads| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/python-thundercache/badge/?style=flat
    :target: https://readthedocs.org/projects/python-thundercache
    :alt: Documentation Status

.. |version| image:: https://img.shields.io/pypi/v/thundercache.svg
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/thundercache

.. |commits-since| image:: https://img.shields.io/github/commits-since/thestick613/python-thundercache/v0.1.0.svg
    :alt: Commits since latest release
    :target: https://github.com/thestick613/python-thundercache/compare/v0.1.0...master

.. |downloads| image:: https://img.shields.io/pypi/dm/thundercache.svg
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/thundercache

.. |wheel| image:: https://img.shields.io/pypi/wheel/thundercache.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/thundercache

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/thundercache.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/thundercache

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/thundercache.svg
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/thundercache


.. end-badges

A distributed redis cache library, which solves the Thundering Herd problem.

* Free software: BSD license

Installation
============

::

    pip install thundercache

Documentation
=============

https://python-thundercache.readthedocs.io/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
