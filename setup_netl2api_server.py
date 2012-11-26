#!/usr/bin/python
# -*- coding: utf-8; -*-

from setuptools import setup, find_packages


data_files = [ ("/etc/netl2api",
                    ["etc/netl2api/netl2server.cfg", "etc/netl2api/devices.cfg"]
             ) ]

setup(
    name               = "netl2api.server",
    namespace_packages = ["netl2api"],
    version            = "1.5.6",
    packages           = ["netl2api", "netl2api.server", "netl2api.server.workers"],
    zip_safe           = False,
    install_requires   = ["netl2api.lib", "netl2api.l2api", "simplejson", "bottle", "paste", "Supay", "apscheduler", "redis"],

    entry_points = {
        "console_scripts": [
            "netl2server     = netl2api.server.httpd:cli",
        ]
    },

    data_files = data_files,

    author       = "Eduardo S. Scarpellini",
    author_email = "eduardo.scarpellini@locaweb.com.br",
    description  = "HTTP/REST generic API (vendor agnostic) for network/L2 operations",
    keywords     = "http rest generic vendor agnostic switch l2 api",
    url          = "https://github.com/locaweb/netl2api",
)
