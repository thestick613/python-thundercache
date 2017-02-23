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

Usage
=====

.. code-block:: python

  # Distributed Lock
  from thundercache import LockFactory, retry_command
  from redis.sentinel import Sentinel

  sentinel = Sentinel()
  redis_sentinel_master_instance = retry_command(sentinel.master_for, "your_sentinel_service_name", socket_timeout=20)

  locks = LockFactory(expires=720, timeout=10, redis=redis_sentinel_master_instance)

  with locks('my_lock'):
      # do stuff with a distributed redis lock across different processes and networks
      # pretty cool right!
      pass


  # Local Redis Cache
  from thundercache import SmartLocalRedisCacheFactory, BaseCacheMixin)
  import time

  lcached = SmartLocalRedisCacheFactory()


  class MyClass(BaseCacheMixin):

      @lcached("method", max_age=10, critical=2)
      def method(self, n):
      time.sleep(n)
          return n*n

  @lcached("somefunc', max_age=10, critical=2)
  def somefunc(n):
      time.sleep(n)
      return n*n


  mc = MyClass()
  print mc.method(3)
  # prints "9" after three seconds
  print mc.method(3)
  # prints "9" instantly

  print somefunc(2)
  # prints "4" after two seconds
  print somefunc(2)
  # prints 4



  # Distributed Redis Cache
  from thundercache import SmartRedisCacheFactory, retry_command
  from redis.sentinel import Sentinel

  sentinel = Sentinel()
  cached = SmartRedisCacheFactory(sentinel, "your_sentinel_service_name")
  # you can now use the @cached decorator in the same way you use @lcached



  # Per process cache
  from thundercache import BaseCache

  class MyClass(BaseCacheMixin):
      @BaseCache("mymethod", max_age=10)
      def mymethod(self, n):
          time.sleep(n)
          return n*n

  @BaseCache("otherfunc', max_age=10)
  def otherfunc(n):
      time.sleep(n)
      return n*n


  # You can also chain these decorators
  @BaseCache('x', 10)
  @cached('y', 60)
      def funct_or_method(*args,  **kwargs):
      return None

::
