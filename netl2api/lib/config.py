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


import os
import sys
import stat
import redis
import logging
import ConfigParser
from logging.handlers import SysLogHandler


__all__ = ["get_netl2server_cfg", "get_devices_cfg", "setup_netl2server_logger", "setup_persistence_ctrl_logger"]


ENVVAR_CFGBASE  = "NETL2API_CFG_BASE"
DEFAULT_CFGBASE = "/etc/netl2api"
_LOG_CFG        = { "debug": logging.DEBUG,
                    "info":  logging.INFO,
                    "warn":  logging.WARN,
                    "error": logging.ERROR }


def config_check_perm(config_file=None, chmod=600):
    # convert chmod to octal to be compatible with value returned by S_IMODE()
    if stat.S_IMODE(os.stat(config_file).st_mode) != int(str(chmod), 8):
        raise UnprotectedConfigFile("It is recommended that your config file are NOT accessible by others. Please run: chmod %s %s" \
                % (chmod, config_file))

class UnprotectedConfigFile(Exception):
    pass


_cached_cfg = {}
def get_cfg(cfgfile, check_permission=None):
    if not _cached_cfg.has_key(cfgfile):
        cfg = ConfigParser.ConfigParser()
        cfg_path = os.path.join(os.environ.get(ENVVAR_CFGBASE, DEFAULT_CFGBASE), "%s.cfg" % cfgfile)
        if check_permission is not None:
            config_check_perm(cfg_path, chmod=check_permission)
        cfg.read(cfg_path)
        _cached_cfg[cfgfile] = cfg
    return _cached_cfg[cfgfile]


def section(cfg, cfg_section):
    r = {}
    for k in cfg.options(cfg_section):
        r[k] = cfg.get(cfg_section, k)
    return(r)


def get_netl2server_cfg():
    return get_cfg("netl2server", check_permission=None)


class RedisClient(object):
    # TODO: move-me to a more appropriate library file
    def __init__(self, db=7, timeout=3):
        cfg       = get_netl2server_cfg()
        self.host = cfg.get("redis", "host")
        self.port = cfg.getint("redis", "port")
        self.timeout = timeout
        self.db      = db
        self._redis  = redis.Redis(host=self.host, port=self.port, db=self.db,
                                   socket_timeout=self.timeout)

    def get_connection(self):
        if self._redis is None or not self._redis.ping():
            self._redis = redis.Redis(host=self.host, port=self.port, db=self.db,
                                      socket_timeout=self.timeout)
        return self._redis


def get_devices_cfg():
    switches    = {}
    devices_cfg = get_cfg("devices", check_permission=600)
    for k in devices_cfg.sections():
        if k.startswith("device."):
            switches[k[7:]] = dict([(x,y) for x,y in section(devices_cfg, k).items()])
    return switches


syslog_sockets = {
    "darwin": "/var/run/syslog",
    "linux2": "/dev/log",
}
def setup_logger(cfg, component):
    logging.basicConfig(format="%%(asctime)s [%%(levelname)s] netl2api.%s[%%(process)d/%%(threadName)s]: %%(message)s" % component)
    logger = logging.getLogger(component)
    logger.setLevel(_LOG_CFG.get(cfg.get("logger", "level"), logging.WARN))
    syslog_socket = syslog_sockets.get(sys.platform)
    if syslog_socket is not None:
        syslog = SysLogHandler(address=syslog_socket, facility="daemon")
        syslog.setFormatter(logging.Formatter("%%(asctime)s [%%(levelname)s] netl2api.%s[%%(process)d/%%(threadName)-10s]: %%(message)s" \
            % component, "%b %d %H:%m:%S"))
        logger.addHandler(syslog)
    return logger


def setup_netl2server_logger(cfg):
    return setup_logger(cfg, "netl2server")


def setup_persistence_ctrl_logger(cfg):
    return setup_logger(cfg, "netl2server.job.switch_cfg_persistence")
