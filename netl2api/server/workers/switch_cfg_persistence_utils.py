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


from netl2api.server.utils import RedisClient
from netl2api.lib.config import get_netl2server_cfg, setup_netl2server_logger, setup_persistence_ctrl_logger


__all__ = ["defer_save_switch_cfg", "acquire_persistence_lock", "list_pending_persistence_jobs",
           "finish_persistence_job"]


cfg = get_netl2server_cfg()
logger_netl2server  = setup_netl2server_logger(cfg)
logger_persist_ctrl = setup_persistence_ctrl_logger(cfg)
redis_cli = RedisClient()


def defer_save_switch_cfg(device=None):
    try:
        sw_persist_ctrl_db = redis_cli.get_connection()
    except Exception, e:
        logger_netl2server.exception("Error in redis_cli connection (persistence control database)")
        return
    sw_persist_ctrl_db.incr("rwopts:%s:counter" % device, amount=1)


def acquire_persistence_lock(device=None):
    try:
        sw_persist_ctrl_db = redis_cli.get_connection()
    except Exception, e:
        logger_persist_ctrl.exception("Error in redis_cli connection (persistence control database)")
        return
    persistence_daemon_lock = sw_persist_ctrl_db.lock("rwopts:%s:lock" % device, 300)
    if persistence_daemon_lock.acquire(blocking=False) is True:
        return persistence_daemon_lock


def list_pending_persistence_jobs():
    try:
        sw_persist_ctrl_db = redis_cli.get_connection()
    except Exception, e:
        logger_persist_ctrl.exception("Error in redis_cli connection (persistence control database)")
        return
    return [sw.split(":")[1] for sw in sw_persist_ctrl_db.keys("rwopts:*:counter") \
                if int(sw_persist_ctrl_db.get(sw)) > 0]


def finish_persistence_job(device=None):
    try:
        sw_persist_ctrl_db = redis_cli.get_connection()
    except Exception, e:
        logger_persist_ctrl.exception("Error in redis_cli connection (persistence control database)")
        return
    sw_persist_ctrl_db.set("rwopts:%s:counter" % device, 0)
