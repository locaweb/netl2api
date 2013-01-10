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


from functools import wraps
from re import _pattern_type
from bottle import request, response, abort
from netl2api.lib.utils import gen_context_uid
from netl2api.lib.config import get_netl2server_cfg, setup_netl2server_logger

try:
    from simplejson import dumps
except ImportError:
    from json import dumps


__all__ = ["reply_json", "context", "validate_input"]


cfg    = get_netl2server_cfg()
logger = setup_netl2server_logger(cfg)


def reply_json(f):
    @wraps(f)
    def json_dumps(*args, **kwargs):
        r = f(*args, **kwargs)
        if r and type(r) in (dict, list, tuple, str, unicode):
            response.content_type = "application/json; charset=UTF-8"
            return dumps(r)
        return r
    return json_dumps


def context(f):
    @wraps(f)
    def inject_ctx(*args, **kwargs):
        truncate = lambda i: i if len(i) <= 40 else "%s..." % i[:40]
        context  = { "CTX-UUID":                 gen_context_uid(),
                     "HTTP.ENV.SERVER_PROTOCOL": request.environ.get("SERVER_PROTOCOL"),
                     "HTTP.ENV.REQUEST_METHOD":  request.environ.get("REQUEST_METHOD"),
                     "HTTP.ENV.REMOTE_ADDR":     request.environ.get("REMOTE_ADDR"),
                     "HTTP.ENV.PATH_INFO":       request.environ.get("PATH_INFO") }
        if request.headers.get("X-Real-IP"):
            context["HTTP.ENV.X-Real-IP"] = request.headers.get("X-Real-IP")
        if request.headers.get("X-Forwarded-For"):
            context["HTTP.ENV.X-Forwarded-For"] = request.headers.get("X-Forwarded-For")
        for arg, val in kwargs.iteritems():
            if arg not in ("cfg", "logger", "context"):
                context["kwargs.%s" % arg] = truncate(val)
        for arg, val in request.query.iteritems():
            context["HTTP.QUERYSTR.%s" % arg] = truncate(val)
        for arg, val in request.forms.iteritems():
            context["HTTP.FORMDATA.%s" % arg] = truncate(val)
        request["context"] = context
        return f(*args, **kwargs)
    return inject_ctx


def validate_input(src="query", *vargs, **vkwargs):
    """
    Usage:
    >>> @get('/test')
    ... @validate_input(source="query", name=str, age=int, email=re.compile("\w+@\w+.com"), gender=("M", "F"))
    ... def test():
    ...    return request.query.get("name")
    """
    def proxy(f):
        @wraps(f)
        def validate(*args, **kwargs):
            if src not in ("query", "forms", "GET", "POST"):
                raise RuntimeError("invalid 'source' option")
            psource = request.__getattribute__(src)
            for param, ptype in vkwargs.iteritems():
                pvalue = psource.get(param, None)
                try:
                    # lambda
                    if isinstance(ptype, type(lambda: None)):
                    #\ and ptype.__name__ == "<lambda>":
                        if not ptype(pvalue):
                            raise HTTPInvalidParameter()
                        continue
                    if pvalue is None:
                        raise HTTPNullParameter()
                    # exact match
                    if type(ptype) in (str, unicode):
                        assert pvalue == ptype
                        continue
                    # valid option list
                    if type(ptype) in (list, tuple):
                        assert pvalue in ptype
                        continue
                    # int(), str(), etc
                    if type(ptype) is type:
                        ptype(pvalue)
                        continue
                    # regexp
                    if isinstance(ptype, _pattern_type):
                        assert ptype.search(pvalue) is not None
                        continue
                except HTTPNullParameter, e:
                    logger.exception("Error: parameter '%s' is null" % param)
                    abort(400, "Error: parameter '%s' is null" % param)
                except Exception, e:
                    logger.exception("Error: parameter '%s' has an unexpected type or an invalid format" % param)
                    abort(400, "Error: parameter '%s' has an unexpected type or an invalid format" % param)
            return f(*args, **kwargs)
        return validate
    return proxy


class HTTPInvalidParameter(Exception):
    pass

class HTTPNullParameter(Exception):
    pass
