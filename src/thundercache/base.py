"""
This is based on
https://github.com/bbangert/retools/blob/master/retools/lock.py
and on
http://stackoverflow.com/a/30698822/3599101
"""

import time
import random
import retry
import redis
import math
import uuid

from redis.sentinel import MasterNotFoundError
from redis.exceptions import ConnectionError, TimeoutError

from datetime import datetime

try:
    import cPickle as pickle
except:
    import pickle


class LockTimeout(BaseException):
    """Raised in the event a timeout occurs while waiting for a lock"""


class BaseCacheMixin(object):
    pass


DISTRIBUTED_ERRORS = [MasterNotFoundError, ConnectionError, TimeoutError]

acquire_lua = """
local result = redis.call('SETNX', KEYS[1], ARGV[1])
if result == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return result"""

release_lua = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0"""

def retry_command(funct, *args, **kwargs):
    return retry.api.retry_call(funct, fargs=args, fkwargs=kwargs,
                                exceptions=DISTRIBUTED_ERRORS,
                                tries=14, backoff=1.8, delay=0.33, jitter=(0.01, 0.99), max_delay=25+(random.random()/2))


class Lock(object):
    def __init__(self, key, expires=60, timeout=10, redis=None):
        """Distributed locking using Redis Lua scripting for CAS operations.
        Usage::
            with Lock('my_lock'):
                print "Critical section"
        :param  expires:    We consider any existing lock older than
                            ``expires`` seconds to be invalid in order to
                            detect crashed clients. This value must be higher
                            than it takes the critical section to execute.
        :param  timeout:    If another client has already obtained the lock,
                            sleep for a maximum of ``timeout`` seconds before
                            giving up. A value of 0 means we never wait.
        :param  redis:      The redis instance to use if the default global
                            redis connection is not desired.
        """
        self.key = key
        self.timeout = timeout
        self.expires = expires
        if not redis:
            redis = global_connection.redis
        self.redis = redis
        self._acquire_lua = redis.register_script(acquire_lua)
        self._release_lua = redis.register_script(release_lua)
        self.lock_key = None

    def __enter__(self):
        return retry_command(self.acquire)

    def __exit__(self, exc_type, exc_value, traceback):
        return retry_command(self.release)

    def acquire(self):
        """Acquire the lock
        :returns: Whether the lock was acquired or not
        :rtype: bool
        """
        self.lock_key = uuid.uuid4().hex
        timeout = self.timeout
        retry_sleep = 0.05
        while timeout >= 0:
            if self._acquire_lua(keys=[self.key],
                                 args=[self.lock_key, self.expires]):
                return
            timeout -= 1
            if timeout >= 0:
                time.sleep(random.uniform(0, retry_sleep))
                retry_sleep = min(retry_sleep*2, 1.5)
        raise LockTimeout("Timeout while waiting for lock")

    def release(self):
        """Release the lock
        This only releases the lock if it matches the UUID we think it
        should have, to prevent deleting someone else's lock if we
        lagged.
        """
        if self.lock_key:
            self._release_lua(keys=[self.key], args=[self.lock_key])
        self.lock_key = None


class BaseHelper(object):
   
    def roughly(self, v):
        return max(0.1, v + random.choice([-3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]) * math.sqrt(v))

    @staticmethod
    def serialize_classes(_args):
        """Used to extract the arguments from decorated function """
        args = []
        for arg in _args:
            #TODO: find an elegant solution
            #using BaseCacheMixin to find out if the arg is actually a class (self)
            if isinstance(arg, BaseCacheMixin):
                args.append(type(arg).__name__)
            else:
                args.append(arg)

        return args


class BaseCache(BaseHelper):
    def __init__(self, key, max_age=60):
        self.responses = {}
        self.namespace = key
        self.max_age = max_age

    #TODO: find more elegant method to prune cached responses based on how close they are to expiration date
    def cleansome(self):
        if random.random() <= 0.05:
            cleanup = False
            cleaned = 0
            while not cleanup:
                if self.responses.keys():
                    k = random.choice(self.responses.keys())
                    if (time.time() - self.responses[k]['ts']) > self.responses[k]['keep_for']:
                        self.responses.pop(k)
                        cleaned += 1
                    else:
                        cleanup = True

                    if cleaned > 20:
                        cleanup = True
                else:
                    cleanup = True

    def __call__(self, fn):
        def inner(*args, **kwargs):
            this_max_age = self.max_age
            params = pickle.dumps({"args": self.serialize_classes(args), "kwargs": kwargs}, 2)
            this_key = "%s_%s" % (self.namespace, params)
            self.cleansome()
            if (this_key) not in self.responses or \
                    (time.time() - self.responses[this_key]['ts'] >
                        self.roughly(self.responses[this_key]['keep_for'])):
                result = fn(*args, **kwargs)
                self.responses[this_key] = {'result': pickle.dumps(result, 2), 'keep_for': this_max_age, 'ts': time.time()}
            return pickle.loads(self.responses[this_key]['result'])
        return inner


class SmartRedisCache(BaseHelper):
    def __init__(self, sentinel_instance, service_name, key, max_age=120, critical=30):
        self.redis = sentinel_instance.master_for(service_name)
        self.max_age = max_age
        self.namespace = key
        self.critical = critical
        self.locks = LockFactory(expires=20+critical+1, timeout=20+critical, redis=self.redis)

    def locking_get(self, key):
        value1 = self.redis.get(key)
        if value1 != "__COMPUTING__" and value1 is not None:
            return value1
        passed = False

        while not passed:
            try:
                with self.locks(key):
                    value = self.redis.get(key)
                    if value is None:
                        self.redis.setex(name=key, time=self.critical, value="__COMPUTING__")
                        return None

                    while value == "__COMPUTING__":
                        time.sleep(self.roughly(math.sqrt(self.critical)))
                        value = self.redis.get(key)

                    passed = True
                    return value

            except LockTimeout:
                backup = self.redis.get("BCK_%s_BCK" % key)
                if backup:
                    return backup
                else:
                    raise

    def __call__(self, fn):
        def inner(*args, **kwargs):
            params = pickle.dumps({"args": self.serialize_classes(args), "kwargs": kwargs}, 2)
            key = "SRC:%s_%s" % (self.namespace, params)

            _old_data = self.locking_get(key)

            if _old_data:
                _old_data = pickle.loads(_old_data)

            if not _old_data or (time.time() - _old_data['ts'] > self.roughly(_old_data['keep_for'])):
                result = fn(*args, **kwargs)

                self.redis.setex(name=key, time=3 * self.max_age,
                                 value=pickle.dumps({'result': pickle.dumps(result, 2), 'keep_for': self.max_age, 'ts': time.time()}, 2))

                self.redis.setex(name="BCK_%s_BCK" % key, time=3600 * 24,
                                 value=pickle.dumps({'result': pickle.dumps(result, 2), 'keep_for': self.max_age, 'ts': time.time()}, 2))

                return result

            return pickle.loads(_old_data['result'])
        return inner


class SmartLocalRedisCache(SmartRedisCache):
    def __init__(self, key, max_age=120, critical=30):
        self.redis = redis.Redis(unix_socket_path='/var/run/redis/redis.sock')
        self.max_age = max_age
        self.namespace = key
        self.critical = critical
        self.locks = LockFactory(expires=20+critical+1, timeout=20+critical, redis=self.redis)


def SmartRedisCacheFactory(sentinel_instance, service_name):
    def _factory(key, max_age, critical=30):
        DBC = SmartRedisCache(sentinel_instance, service_name, key, max_age, critical)
        return DBC
    return _factory


def SmartLocalRedisCacheFactory():
    def _factory(key, max_age, critical=30):
        DBC = SmartLocalRedisCache(key, max_age, critical)
        return DBC
    return _factory


def LockFactory(expires=40, timeout=41, redis=None):
    def get_lock_instance(key):
        return Lock(key="LOCK_FOR:"+key, expires=expires, timeout=timeout, redis=redis)
    return get_lock_instance


if __name__ == "__main__":
    pass
