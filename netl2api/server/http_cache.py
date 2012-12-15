#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# @author: Eduardo S. Scarpellini
# @author: Luiz Ozaki


__copyright__ = "Copyright 2012, Locaweb IDC"


import redis
from hashlib import sha1
from functools import wraps
from bottle import request, response
from netl2api.server.utils import RedisClient
from netl2api.lib.config import get_netl2server_cfg, setup_netl2server_logger

try:
    from cPickle import dumps, loads
except ImportError:
    from pickle import dumps, loads


__all__ = ["cached", "invalidate_cache"]


cfg    = get_netl2server_cfg()
logger = setup_netl2server_logger(cfg)
cache_enable = cfg.get("cache", "enabled") == "true"
redis_cli = RedisClient()


def cached(ttl=600):
    def proxy(f):
        @wraps(f)
        def caching(*args, **kwargs):
            if cache_enable is False:
                return f(*args, **kwargs)
            try:
                cache_db = redis_cli.get_connection()
            except Exception, e:
                logger.exception("Error in redis_cli connection (cache database)")
                return f(*args, **kwargs)
            cache_key     = "%s:%s" % (request.environ.get("REQUEST_METHOD"), request.environ.get("PATH_INFO"))
            cache_subkey  = ";".join(["%s=%s" % (k,v) for k,v in request.query.iteritems() \
                                        if k != "ticket"])
            cache_subkey += ";".join(["%s=%s" % (k,v) for k,v in request.forms.iteritems() \
                                        if k != "ticket"])
            cache_rkey    = "cache:%s:%s" % (cache_key, sha1(cache_subkey).hexdigest())
            cached_r      = cache_db.get(cache_rkey)
            if cached_r is not None:
                #logger.debug("Cache HIT -- context %s" % context)
                response.set_header("X-Cached", "True")
                response.set_header("Cache-Control", "max-age=%s, must-revalidate" % int(cache_db.ttl(cache_rkey)))
                return loads(cached_r)
            #logger.debug("Cache MISS (calling %s()) -- context %s" % (f_name, context))
            r = f(*args, **kwargs)
            response.set_header("X-Cached", "False")
            response.set_header("Cache-Control", "max-age=%s, must-revalidate" % ttl)
            cache_db.setex(cache_rkey, dumps(r), ttl)
            return r
        return caching
    return proxy


def invalidate_cache(key=None):
    try:
        cache_db = redis_cli.get_connection()
    except Exception, e:
        logger.exception("Error in redis_cli connection (cache database)")
        return
    try:
        cache_db.delete(*cache_db.keys("cache:*:%s*" % key))
    except redis.exceptions.ResponseError:
        pass
