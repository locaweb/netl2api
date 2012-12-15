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


import signal
from apscheduler.scheduler import Scheduler
from netl2api.lib.utils import gen_context_uid
from netl2api.lib.utils import get_switch_instance
from netl2api.server.workers.switch_cfg_persistence_utils import *
from netl2api.lib.config import get_netl2server_cfg, setup_persistence_ctrl_logger


cfg            = get_netl2server_cfg()
logger         = setup_persistence_ctrl_logger(cfg)
worker_minutes = cfg.get("job.switch_cfg_persistence", "run_on_minutes")


def worker():
    logger.info("Waking up persistence-control worker...")
    devices = list_pending_persistence_jobs()
    if devices is None:
        logger.info("No pending persistence jobs found")
        return
    for device in devices:
        sw_cfg_persist_lock = acquire_persistence_lock(device)
        if sw_cfg_persist_lock is None:
            logger.warn("Could not acquire persistence lock for device '%s'. Probably because it's already acquired by another instance" % device)
            continue
        context = {"CTX-UUID": gen_context_uid()}
        try:
            logger.info("Starting persistence-job for device '%s' -- context: %s" % (device, context))
            swinst = get_switch_instance(device)
            swinst.save_config()
            finish_persistence_job(device)
        except NotImplementedError, e:
            logger.exception("Error on saving configuration on device '%s' -- context: %s" % (device, context))
            finish_persistence_job(device)
        except Exception, e:
            logger.exception("Error on saving configuration on device '%s' -- context: %s" % (device, context))
        finally:
            logger.info("Persistence for device '%s' is done -- context: %s" % (device, context))
            sw_cfg_persist_lock.release()
    logger.info("The persistence-control worker has just finished its job")


def daemon():
    logger.info("Starting persistence-control daemon...")
    logger.info("The persistence-control worker will run on minutes '%s'..." % worker_minutes)
    sched = Scheduler()
    sched.add_cron_job(worker, minute=worker_minutes)
    sched.start()
    signal.pause()