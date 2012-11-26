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
from netl2api.lib.config import get_netl2server_cfg


__all__ = ["RedisClient"]


cfg = get_netl2server_cfg()


class RedisClient(object):
    def __init__(self, db=7, timeout=3):
        self.host = cfg.get("redis", "host")
        self.port = cfg.getint("redis", "port")
        self.timeout  = timeout
        self.redis_db = db
        self._redis   = redis.Redis(host=self.host, port=self.port, db=self.redis_db,
                                      socket_timeout=self.timeout)

    def get_connection(self):
        if self._redis is None or not self._redis.ping():
            self._redis = redis.Redis(host=self.host, port=self.port, db=self.redis_db,
                                      socket_timeout=self.timeout)
        return self._redis
