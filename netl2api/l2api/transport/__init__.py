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
import time
import socket
import logging
from functools import wraps
from netl2api.l2api.exceptions import *
from netl2api.l2api.utils import LF, CRLF
from netl2api.lib.utils import get_context_uid
from errno import EPIPE, ECONNABORTED, ECONNRESET, ENETRESET


__all__ = ["L2Transport"]


def l2api_retry(times=1):
    def proxy(f):
        @wraps(f)
        def retry_exec(self, *args, **kwargs):
            count = 1
            while True:
                try:
                    r = f(self, *args, **kwargs)
                except (socket.error, socket.timeout), e:
                    if isinstance(e, socket.error) and \
                            e.errno not in (EPIPE, ECONNABORTED, ECONNRESET, ENETRESET):
                        raise e
                    if count >= times:
                        raise e
                    count += 1
                    self.close()
                    #if isinstance(e, socket.timeout):
                    #    time.sleep(2)
                    time.sleep(3)
                else:
                    return r
        return retry_exec
    return proxy


class L2Transport(object):
    """
        SSH transport (encrypted) for L2API.

        :host: SSH server (network switch fqdn/ip-address).
            - type: str.
            - ex: "192.168.0.1"

        :port: SSH port.
            - type: int.
            - ex: 22

        :username: Switch username (SSH authentication).
            - type: str.
            - ex: "admin"

        :passwd: Switch user password (SSH authentication).
            - type: str.
            - ex: "s3cr3t.passwd"

        :prompt_mark: Prompt signal.
                        In GNU/Linux systems it's usually be '$' for normal users and '#' for root.
            - type: str.
            - ex: "#"

        :error_mark: Used to recognize an error message.
                        If this string is found on a returned message, a SwitchCommandError() exception is raised.
            - type: str.
            - ex: "% Error:"

        :config_term_cmd: Command used to configure the terminal connected to the network switch.
                            Executed just after the session is opened (authenticated). Usually removes screen paging.
            - type: str.
            - ex: "terminal length 0"

        :socket_timeout: Socket timeout (socket.settimeout()).
                            0 = Operating System default.
            - type: int.
            - ex: 60

        :transaction_timeout: Time to wait for a finalization of each command/interaction.
                        If a "complete response"* is not received within this time, a TransportTransactionException() exception is raised.
                        * A response is considered complete if it ends with prompt_mark or the REGEXP defined in interactions parameter (.execute())
            - type: int.
            - ex: 180

        :close_on_switch_error: Close (self.close()) the connection (self.connection) on 'SwitchCommandError' exception.
            - type: bool.
            - ex: True

        :close_on_transaction_error: Close (self.close()) the connection (self.connection) on 'TransportTransactionException' exception (see also transaction_timeout).
            - type: bool.
            - ex: True
    """

    def __init__(self, host=None, port=22, username=None, passwd=None, prompt_mark=None,
                 error_mark=None, config_term_cmd=None, socket_timeout=None, transaction_timeout=180,
                 close_on_switch_error=False, close_on_transaction_error=True):
        if not host or type(host) not in (str, unicode):
            raise InvalidParameter("'host' parameter is not defined or invalid")
        if not port or type(port) is not int:
            raise InvalidParameter("'port' parameter is not defined or invalid")
        if not username or type(username) not in (str, unicode):
            raise InvalidParameter("'username' parameter is not defined or invalid")
        if not passwd or type(passwd) not in (str, unicode):
            raise InvalidParameter("'passwd' parameter is not defined or invalid")
        if not prompt_mark or type(prompt_mark) not in (str, unicode):
            raise InvalidParameter("'prompt_mark' parameter is not defined or invalid")
        if type(error_mark) not in (type(None), str, unicode):
            raise InvalidParameter("'error_mark' parameter is invalid")
        if type(config_term_cmd) not in (type(None), str, unicode):
            raise InvalidParameter("'config_term_cmd' parameter is invalid")
        if type(socket_timeout) not in (type(None), int, float):
            raise InvalidParameter("'socket_timeout' parameter is invalid")
        if type(transaction_timeout) not in (type(None), int, float):
            raise InvalidParameter("'transaction_timeout' parameter is invalid")
        if type(close_on_switch_error) is not bool:
            raise InvalidParameter("'close_on_switch_error' parameter is invalid")
        if type(close_on_transaction_error) is not bool:
            raise InvalidParameter("'close_on_transaction_error' parameter is invalid")

        self.host     = host
        self.port     = port
        self.username = username
        self.passwd   = passwd
        self.crlf     = CRLF
        self.prompt_mark = prompt_mark
        # self.prompt_mark_re = re.compile(r"(?:\r)?\n(?:%s|%s|[a-z0-9]+(?:%s)?)?%s\s*$" % \
        #         (self.host, self.host.split(".")[0], self.host.split(".")[0][-1:], self.prompt_mark), re.IGNORECASE)
        #self.prompt_mark_re = re.compile(r"(?:\r)?\n(?:%s|%s|[a-z0-9\@\-]+(?:%s)?)?%s\s*$" % \
        #        (self.host, self.host.split(".")[0], self.host.split(".")[0][-1:], self.prompt_mark), re.IGNORECASE)
        self.prompt_mark_re  = re.compile(r"(?:\r)?\n(?:[a-z0-9\.\-\@_]+)?\s*%s\s*$" % self.prompt_mark, re.IGNORECASE)
        self.error_mark      = error_mark
        self.error_mark_re   = re.compile(r"(%s.+)" % self.error_mark)
        self.config_term_cmd = config_term_cmd
        self.socket_timeout  = socket_timeout
        self.transaction_timeout        = transaction_timeout
        self.close_on_switch_error      = close_on_switch_error
        self.close_on_transaction_error = close_on_transaction_error
        self._connection = None
        self._logger     = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(format="%%(asctime)s [%%(levelname)s] %s[%%(process)d/%%(threadName)s]: %%(message)s" %\
                                 self.__class__.__name__)
        self._logger.setLevel(logging.DEBUG)

    @property
    def connection(self):
        """
        Lazy connection-object creation (SSH, Telnet, etc)
        """
        if not self._connection:
            connection = self._setup_connection()
            self._skip_motd(connection=connection)
            self._config_term(connection=connection)
            self._connection = connection
        return self._connection

    def _setup_connection(self):
        """
        Setup (establish, authenticate, etc) connection-object
        """
        raise NotImplementedError("_setup_connection() not implemented")

    def _skip_motd(self, connection=None):
        """
        Skip MOTD (just after succeeded login) and go to the prompt mark
        """
        pass

    def _config_term(self, connection=None):
        """
        Configure terminal (eg. 'terminal length 0') after _skip_motd()
        """
        if self.config_term_cmd is not None:
            self._execute(connection=connection, cmd=self.config_term_cmd)

    def _execute(self, connection=None, cmd=None, interactions=None):
        """
        Execute command 'cmd' (+'interactions') using 'connection' object
        """
        context = {"CTX-UUID": get_context_uid()}

        self._logger.info("%s(%s@%s:%s): Command '%s' invoked with interactions: %s -- context: %s" % \
        (self.__class__.__name__, self.username, self.host, self.port, cmd, \
            "; ".join(["'%s'->'%s'" % (i_res, i_cmd) for i_res, i_cmd in interactions]) \
            if interactions else "''", context))

    @l2api_retry(times=2)
    def execute(self, cmd=None, interactions=None):
        """ Execute commands on remote host

            :cmd: The command to execute
                - type: str.
                - ex: "copy running-config startup-config"

            :interactions: interactions with above cmd (questions+answers)
                - type: list of tuples - [("question-regexp", "action/answer"), ()]
                - ex: [("Proceed to copy.*", "yes")]
        """
        if cmd is None:
            return
        if type(cmd) not in (str, unicode):
            raise InvalidParameter("'cmd' parameter is invalid")
        if interactions is not None and type(interactions) not in (list, tuple):
            raise InvalidParameter("'interactions' parameter is invalid")
        try:
            r = self._execute(connection=self.connection, cmd=cmd, interactions=interactions)
        except SwitchCommandException, e:
            if self.close_on_switch_error is True:
                self.close()
            raise e
        except TransportTransactionException, e:
            if self.close_on_transaction_error is True:
                self.close()
            raise e
        return r

    def close(self):
        """
        Close connection/connection object
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    # def __del__(self):
    #     self.close()
