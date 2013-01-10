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


from time import time
from netl2api.l2api.exceptions import *


__all__ = ["L2APIAutoCache"]


class L2APIAutoCache(object):
    """
        Auto/Smart cache for get_*/show_* methods.
        L2API base classes should extend this, declare 'self.use_cache' (bool) and
        'self.cache_config' (dict with cache ttl/clear configuration).

        Ex.:
        class ExampleL2API(L2APIAutoCache):
            def __init__(self):
                use_cache = True
                self.cache_config = {
                     "show_version":    { "ttl":      300,
                                          "clear_on": [] },
                     "show_interfaces": { "ttl":      60,
                                          "clear_on": ["change_interface", "remove_interface"] }
                }

                super(ExampleL2API, self).__init__()

            ...

            def show_version(self):
                ...
    """

    def __init__(self):
        self._cached_attrs = {}
        if not hasattr(self, "use_cache"):
            self.use_cache = False

    def __getattribute__(self, name):
        attr = super(L2APIAutoCache, self).__getattribute__(name)
        if not callable(attr):
            return attr
        if name in self.cache_config.keys():
            def _cache_opt(*args, **kwargs):
                return self._cache_opt(attr, *args, **kwargs)
            return _cache_opt
        else:
            clear_keys = [k for k,v in self.cache_config.iteritems() \
                                if name in v.get("clear_on")]
            if len(clear_keys) == 0:
                return attr
            def _cache_clear_keys(*args, **kwargs):
                return self._cache_clear_keys(clear_keys, attr, *args, **kwargs)
            return _cache_clear_keys

    def _cache_opt(self, f, *args, **kwargs):
        use_cache = kwargs.get("use_cache") if hasattr(self, "cache_config") else False
        if use_cache is None:
            use_cache = self.use_cache
        elif type(use_cache) is not bool:
            raise InvalidParameter("'use_cache' must be boolean (True or False)")
        try:
            del(kwargs["use_cache"])
        except KeyError:
            pass
        if use_cache:
            return self._use_cache(f, *args, **kwargs)
        return f(*args, **kwargs)

    def _use_cache(self, f, *args, **kwargs):
        func_name       = f.__name__
        cache_noarg_key = "__full_resp__"
        cache_f_key     = func_name
        cache_arg_key   = cache_noarg_key
        now             = time()
        cache_is_valid  = lambda k: (now - k["time"]) <= self.cache_config[func_name]["ttl"]
        if args:
            cache_arg_key = args[0]
        elif kwargs:
            cache_arg_key = kwargs.values()[0]
        if not self._cached_attrs.has_key(cache_f_key):
            self._cached_attrs[cache_f_key] = {}
        if self._cached_attrs[cache_f_key].has_key(cache_arg_key) and \
                cache_is_valid(self._cached_attrs[cache_f_key][cache_arg_key]):
            return self._cached_attrs[cache_f_key][cache_arg_key]["value"]
        if cache_arg_key is not cache_noarg_key and \
                self._cached_attrs[cache_f_key].has_key(cache_noarg_key) and \
                type(self._cached_attrs[cache_f_key][cache_noarg_key]["value"]) is dict and \
                self._cached_attrs[cache_f_key][cache_noarg_key]["value"].has_key(cache_arg_key) and \
                cache_is_valid(self._cached_attrs[cache_f_key][cache_noarg_key]):
            return { cache_arg_key: self._cached_attrs[cache_f_key][cache_noarg_key]["value"][cache_arg_key] }
        r = f(*args, **kwargs)
        if cache_arg_key is cache_noarg_key:
            self._cached_attrs[cache_f_key] = {}
        elif self._cached_attrs[cache_f_key].has_key(cache_noarg_key) and \
                not cache_is_valid(self._cached_attrs[cache_f_key][cache_noarg_key]):
            del(self._cached_attrs[cache_f_key][cache_noarg_key])
        self._cached_attrs[cache_f_key][cache_arg_key] = { "time": now, "value": r }
        return r

    def _cache_clear_keys(self, clear_keys, f, *args, **kwargs):
        r = f(*args, **kwargs)
        for cachekey in clear_keys:
            try:
                del(self._cached_attrs[cachekey])
            except KeyError:
                pass
        return r

    def clear_cache(self):
        self._cached_attrs = {}
