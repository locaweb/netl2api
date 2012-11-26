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


import re
import os
import sys
import pwd
#import netl2api.lib.servicenow
from multiprocessing import Process
from netl2api.server.http_cache import cached, invalidate_cache
from netl2api.server.http_utils import reply_json, validate_input, context
from netl2api.server.workers import switch_cfg_persistence
from netl2api.server.workers.switch_cfg_persistence_utils import defer_save_switch_cfg
from netl2api.lib.utils import switches, get_switch_instance
from netl2api.lib.config import get_netl2server_cfg, setup_netl2server_logger
from bottle import debug, run, route, get, put, delete, error, request, response, abort


cfg          = get_netl2server_cfg()
logger       = setup_netl2server_logger(cfg)
netl2debug   = cfg.get("logger", "level").lower() == "debug"


RE_TYPE_VLAN_TAGGED = re.compile(r"^(?:True|False)$", re.IGNORECASE)


@get("/devices")
@context
@reply_json
def devices_list():
    # MUST return ONLY switch names -- for CLI completion purpose
    logger.info("Listing available devices -- context: %s" % request["context"])
    return switches.keys()


@get("/info/<device>")
@context
@reply_json
@cached(ttl=3600)
def device_info(device=None):
    logger.info("Showing generic information for device %s -- context: %s" %\
                    (device, request["context"]))
    swinfo = {}
    swinst = get_switch_instance(device)
    swinfo["hostname"] = swinst.show_hostname()
    swinfo["version"]  = swinst.show_version()
    swinfo["l2api"]    = { "device.mgmt-api":  "%s.%s" % (swinst.__class__.__module__,
                                                          swinst.__class__.__name__),
                           "device.mgmt-host": swinst.transport.host,
                           "device.vendor":    swinst.__VENDOR__,
                           "device.hwtype":    swinst.__HWTYPE__ }
    return swinfo


@get("/version/<device>")
@context
@reply_json
@cached(ttl=3600)
def show_version(device=None):
    logger.info("Showing version information from device '%s' -- context: %s" %\
                     (device, request["context"]))
    swinst = get_switch_instance(device)
    defer_save_switch_cfg(device)
    return swinst.show_version()


@get("/system/<device>")
@context
@reply_json
@cached(ttl=3600)
def show_system(device=None):
    logger.info("Showing system information from device '%s' -- context: %s" %\
                     (device, request["context"]))
    swinst = get_switch_instance(device)
    return swinst.show_system()


RE_ROUTE_INTERFACE_ACTIONS = re.compile(r"^(.+)/((?:at|de)tach_vlan|change_description|(?:dis|en)able)$")
@route(["/interfaces/<device>", "/interfaces/<device>/<remaining_path:path>"], ["get", "put"])
@context
def interfaces_route_actions(device=None, remaining_path=None):
    print remaining_path
    if request.method.lower() == "get":
        return show_interfaces(device=device, interface_id=remaining_path)
    if request.method.lower() == "put":
        m = RE_ROUTE_INTERFACE_ACTIONS.search(remaining_path)
        if m is None:
            abort(404, "Not Found")
        route_act = m.group(2)
        if route_act == "attach_vlan":
            return interface_attach_vlan(device=device, interface_id=m.group(1))
        if route_act == "detach_vlan":
            return interface_detach_vlan(device=device, interface_id=m.group(1))
        if route_act == "change_description":
            return change_interface_description(device=device, interface_id=m.group(1))
        if route_act == "enable":
            return enable_interface(device=device, interface_id=m.group(1))
        if route_act == "disable":
            return disable_interface(device=device, interface_id=m.group(1))
        abort(404, "Not Found")
    abort(405, "Method Not Allowed")


@reply_json
@cached(ttl=3600)
def show_interfaces(device=None, interface_id=None):
    logger.info("Showing interfaces informations from device '%s' -- context: %s" %\
                     (device, request["context"]))
    swinst = get_switch_instance(device)
    return swinst.show_interfaces(interface_id=interface_id)


@reply_json
@validate_input(src="forms", vlan_id=int, tagged=RE_TYPE_VLAN_TAGGED)
def interface_attach_vlan(device=None, interface_id=None):
    logger.info("Attaching VLAN to the interface '%s' in device '%s' -- context: %s" %\
                    (interface_id, device, request["context"]))
    vlan_id = request.forms.get("vlan_id")
    tagged  = request.forms.get("tagged", "").lower() == "true"
    swinst  = get_switch_instance(device)
    swinst.interface_attach_vlan(interface_id=interface_id, vlan_id=vlan_id, tagged=tagged)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)


@validate_input(src="forms", vlan_id=int, tagged=RE_TYPE_VLAN_TAGGED)
def interface_detach_vlan(device=None, interface_id=None):
    logger.info("Detaching VLAN from the interface '%s' in device '%s' -- context: %s" %\
                    (device, interface_id, request["context"]))
    vlan_id = request.forms.get("vlan_id")
    tagged  = request.forms.get("tagged", "").lower() == "true"
    swinst  = get_switch_instance(device)
    swinst.interface_detach_vlan(interface_id=interface_id, vlan_id=vlan_id, tagged=tagged)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)


@validate_input(src="forms", interface_description=str)
def change_interface_description(device=None, interface_id=None):
    logger.info("Changing interface '%s' description in device '%s' -- context: %s" %\
                    (interface_id, device, request["context"]))
    interface_description = request.forms.get("interface_description")
    swinst  = get_switch_instance(device)
    swinst.change_interface_description(interface_id=interface_id,
                                        interface_description=interface_description)
    defer_save_switch_cfg(device)
    invalidate_cache("/interfaces/%s" % device)


def enable_interface(device=None, interface_id=None):
    logger.info("Enabling interface '%s' in device '%s' -- context: %s" %\
                    (interface_id, device, request["context"]))
    swinst  = get_switch_instance(device)
    swinst.enable_interface(interface_id=interface_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/interfaces/%s" % device)


def disable_interface(device=None, interface_id=None):
    logger.info("Disabling interface '%s' in device '%s' -- context: %s" %\
                    (interface_id, device, request["context"]))
    swinst  = get_switch_instance(device)
    swinst.disable_interface(interface_id=interface_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/interfaces/%s" % device)


@put("/vlans/<device>/<vlan_id>")
@context
@reply_json
def create_vlan(device=None, vlan_id=None):
    logger.info("Creating new VLAN with id '%s' in device '%s' -- context: %s" %\
                     (vlan_id, device, request["context"]))
    vlan_description = request.forms.get("vlan_description")
    swinst = get_switch_instance(device)
    swinst.create_vlan(vlan_id=vlan_id, vlan_description=vlan_description)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)
    response.status = 201


@put("/vlans/<device>/<vlan_id>/change_description")
@context
@reply_json
@validate_input(src="forms", vlan_description=str)
def change_vlan_description(device=None, vlan_id=None):
    logger.info("Changing VLAN '%s' description in device '%s' -- context: %s" %\
                    (vlan_id, device, request["context"]))
    vlan_description = request.forms.get("vlan_description")
    swinst  = get_switch_instance(device)
    swinst.change_vlan_description(vlan_id=vlan_id,
                                   vlan_description=vlan_description)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)


@delete("/vlans/<device>/<vlan_id>")
@context
@reply_json
def destroy_vlan(device=None, vlan_id=None):
    logger.info("Removing VLAN '%s' from device '%s' -- context: %s" %\
                     (vlan_id, device, request["context"]))
    swinst = get_switch_instance(device)
    swinst.destroy_vlan(vlan_id=vlan_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)
    response.status = 204


@get(["/vlans/<device>", "/vlans/<device>/<vlan_id>"])
@context
@reply_json
@cached(ttl=3600)
def show_vlans(device=None, vlan_id=None):
    logger.info("Showing VLAN information from device '%s' -- context: %s" %\
                    (device, request["context"]))
    swinst = get_switch_instance(device)
    return swinst.show_vlans(vlan_id=vlan_id)


@put("/vlans/<device>/<vlan_id>/enable")
@context
@reply_json
def enable_vlan(device=None, vlan_id=None):
    logger.info("Enabling VLAN '%s' in device '%s' -- context: %s" %\
                     (vlan_id, device, request["context"]))
    swinst = get_switch_instance(device)
    swinst.enable_vlan(vlan_id=vlan_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)


@put("/vlans/<device>/<vlan_id>/disable")
@context
@reply_json
def disable_vlan(device=None, vlan_id=None):
    logger.info("Disabling VLAN '%s' in device '%s' -- context: %s" %\
                     (vlan_id, device, request["context"]))
    swinst = get_switch_instance(device)
    swinst.disable_vlan(vlan_id=vlan_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/vlans/%s" % device)


@put("/lags/<device>/<lag_id>")
@context
@reply_json
def create_lag(device=None, lag_id=None):
    logger.info("Creating new LAG with id '%s' in device '%s' -- context: %s" %\
                    (lag_id, device, request["context"]))
    lag_description = request.forms.get("lag_description")
    swinst = get_switch_instance(device)
    swinst.create_lag(lag_id=lag_id, lag_description=lag_description)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)
    response.status = 201


@put("/lags/<device>/<lag_id>/change_description")
@context
@reply_json
@validate_input(src="forms", lag_description=str)
def change_lag_description(device=None, lag_id=None):
    logger.info("Changing LAG '%s' description in device '%s' -- context: %s" %\
                    (lag_id, device, request["context"]))
    lag_description = request.forms.get("lag_description")
    swinst  = get_switch_instance(device)
    swinst.change_lag_description(lag_id=lag_id,
                                   lag_description=lag_description)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@delete("/lags/<device>/<lag_id>")
@context
@reply_json
def destroy_lag(device=None, lag_id=None):
    logger.info("Removing LAG '%s' from device '%s' -- context: %s" %\
                     (lag_id, device, context))
    swinst = get_switch_instance(device)
    swinst.destroy_lag(lag_id=lag_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)
    response.status = 204


@get(["/lags/<device>", "/lags/<device>/<lag_id>"])
@context
@reply_json
@cached(ttl=3600)
def show_lags(device=None, lag_id=None):
    logger.info("Showing LAG information from device '%s' -- context: %s" %\
                     (device, request["context"]))
    swinst = get_switch_instance(device)
    return swinst.show_lags(lag_id=lag_id)


@put("/lags/<device>/<lag_id>/enable")
@context
@reply_json
def enable_lag(device=None, lag_id=None):
    logger.info("Enabling LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    swinst = get_switch_instance(device)
    swinst.enable_lag(lag_id=lag_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@put("/lags/<device>/<lag_id>/disable")
@context
@reply_json
def disable_lag(device=None, lag_id=None):
    logger.info("Disabling LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    swinst = get_switch_instance(device)
    swinst.disable_lag(lag_id=lag_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@put("/lags/<device>/<lag_id>/attach_interface")
@validate_input(src="forms", interface_id=str)
@context
@reply_json
def lag_attach_interface(device=None, lag_id=None):
    logger.info("Attaching a new interface to LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    interface_id = request.forms.get("interface_id")
    swinst       = get_switch_instance(device)
    swinst.lag_attach_interface(lag_id=lag_id, interface_id=interface_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@put("/lags/<device>/<lag_id>/detach_interface")
@validate_input(src="forms", interface_id=str)
@context
@reply_json
def lag_detach_interface(device=None, lag_id=None):
    logger.info("Detaching an interface from LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    interface_id = request.forms.get("interface_id")
    swinst       = get_switch_instance(device)
    swinst.lag_detach_interface(lag_id=lag_id, interface_id=interface_id)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@put("/lags/<device>/<lag_id>/attach_vlan")
@validate_input(src="forms", vlan_id=int, tagged=RE_TYPE_VLAN_TAGGED)
@context
@reply_json
def lag_attach_vlan(device=None, lag_id=None):
    logger.info("Attaching a new VLAN to LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    vlan_id = request.forms.get("vlan_id")
    tagged  = request.forms.get("tagged", "").lower() == "true"
    swinst  = get_switch_instance(device)
    swinst.lag_attach_vlan(lag_id=lag_id, vlan_id=vlan_id, tagged=tagged)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


@put("/lags/<device>/<lag_id>/detach_vlan")
@validate_input(src="forms", vlan_id=int, tagged=RE_TYPE_VLAN_TAGGED)
@context
@reply_json
def lag_detach_vlan(device=None, lag_id=None):
    logger.info("Detaching a VLAN from LAG '%s' in device '%s' -- context: %s" %\
                     (lag_id, device, request["context"]))
    vlan_id = request.forms.get("vlan_id")
    tagged  = request.forms.get("tagged", "").lower() == "true"
    swinst  = get_switch_instance(device)
    swinst.lag_detach_vlan(lag_id=lag_id, vlan_id=vlan_id, tagged=tagged)
    defer_save_switch_cfg(device)
    invalidate_cache("/lags/%s" % device)


# @get(["/networkpath/<from_device>", "/networkpath/<from_device>/<to_device>"])
# @context
# @reply_json
# @cached(ttl=180)
# def trace_network_path(from_device=None, to_device=None):
#     logger.info("Tracing network-path from device '%s' to '%s'  -- context: %s" %\
#                      (from_device, to_device, request["context"]))
#     network_paths = find_network_paths(graph_repr(from_device=from_device),
#                                                   from_device=from_device, to_device=to_device)
#     #logger.debug("Path from device '%s' to device '%s': %s" % (from_device, to_device, network_paths))
#     return network_paths


@error(400)
@reply_json
def error400(err):
    return {"server.status": err.status, "server.message": err.output}

@error(403)
@reply_json
def error403(err):
    return {"server.status": err.status, "server.message": err.output}

@error(404)
@reply_json
def error404(err):
    return {"server.status": err.status, "server.message": err.output}

@error(405)
@reply_json
def error405(err):
    return {"server.status": err.status, "server.message": err.output}

@error(500)
@reply_json
def error500(err):
    err_type = repr(err.exception).split("(")[0]
    err_msg  = err.exception.message
    err_info = { "server.status":     err.status,
                 "app.error.type":    err_type,
                 "app.error.message": err_msg }
    #if isinstance(err.exception, L2Exception):
    if str(type(err.exception)).find("netl2api.l2api") > -1:
        err_info["server.message"] = "L2API Error"
    else:
        err_info["server.message"] = "Internal Server Error"
    return err_info


def start_workers():
    p_switch_cfg_persistence = Process(target=switch_cfg_persistence.daemon)
    p_switch_cfg_persistence.start()


def start():
    debug(netl2debug)
    ps_owner = cfg.get("httpd", "user")
    if ps_owner:
        os.setuid(pwd.getpwnam(ps_owner)[2])

    logger.info("Starting netl2server...")
    start_workers()
    run(server=cfg.get("httpd", "handler"), host=cfg.get("httpd", "host"), port=cfg.getint("httpd", "port"))


def main(action="foreground"):
    from supay import Daemon
    daemon = Daemon(name="netl2server", catch_all_log=cfg.get("httpd", "logfile"))

    if action ==  "start":
        daemon.start()
        start()
    elif action == "foreground":
        start()
    elif action == "stop":
        daemon.stop()
    elif action == "status":
        daemon.status()
    else:
        cli_help()


def cli_help():
    print "Usage: %s <start|stop|status|foreground>" % sys.argv[0]
    sys.exit(1)


def cli():
    if len(sys.argv) < 2:
        cli_help()
    main(action=sys.argv[1])


if __name__ == '__main__':
    cli()
