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
import re
import sys
import pty
import time
import errno
import shlex
import signal
import select
import resource
import collections

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


__all__ = ["SystemSSH"]


AUTH_PASSWD_RE = re.compile(r"password:[\s]*$", re.IGNORECASE)
#AUTH_ERROR_RE  = re.compile(r"(?:Permission denied|try again|Authentications that can continue)", re.IGNORECASE)


class SystemSSH(object):
    def __init__(self, host=None, port=22, username=None, passwd=None):
        self.host     = host
        self.port     = port if port is not None else 22
        self.username = username
        self.passwd   = passwd
        self.blocking = True
        self.timeout  = None
        self.path     = "/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin"
        self._ssh_connect_timeout = 30
        self._ssh_auth_timeout    = 60
        self._ssh_child_pid       = None
        self._ssh_master_pty_fd   = None
        self.shell_prompt         = None
        self._ssh_cmd = shlex.split("""ssh -t '-o ConnectTimeout=%s' '-o Protocol=2,1'
            '-o StrictHostKeyChecking=no' '-o PreferredAuthentications=password,keyboard-interactive'
            '-o NumberOfPasswordPrompts=1' '-o TCPKeepAlive=yes' '-o ServerAliveInterval=60'
            '-o ControlMaster=no' '-o LogLevel=INFO' '-p %s' %s@%s""" % (self._ssh_connect_timeout,
                self.port, self.username, self.host))

    @property
    def opened(self):
        try:
            self._check_child_state()
        except (SSHProcessException, SSHNotReady):
            return False
        return True

    @property
    def closed(self):
        return self.opened == False

    def _check_child_basic(self):
        if self._ssh_master_pty_fd is None or self._ssh_child_pid is None:
            raise SSHNotReady("SSH connection is not started/ready")

    def _check_child_state(self):
        self._check_child_basic()
        try:
            pid, exit_st = os.waitpid(self._ssh_child_pid, os.WNOHANG)
        except OSError, e:
            if e.errno == errno.ECHILD:
                self._reset()
            raise SSHProcessException("Error on os.waitpid(%s): %s" % (self._ssh_child_pid, e))
        if pid == 0 and exit_st == 0:
            return
        ssh_pid       = self._ssh_child_pid
        ssh_exit_code = None
        ssh_signal    = None
        ssh_err_msg   = "SSH process (pid='%s') has died:" % ssh_pid
        self._reset()
        if os.WIFSIGNALED(exit_st):
            ssh_signal  = os.WTERMSIG(exit_st)
            ssh_err_msg = "%s killed with signal '%s'" % (ssh_err_msg, ssh_signal)
        elif os.WIFEXITED(exit_st):
            ssh_exit_code = os.WEXITSTATUS(exit_st)
            ssh_err_msg   = "%s exited with code '%s'" % (ssh_err_msg, ssh_exit_code)
        raise SSHProcessException(ssh_err_msg, pid=ssh_pid, exit_code=ssh_exit_code, signal=ssh_signal)

    def _select_fd(self, read=None, write=None, no_wait=False):
        no_wait = bool(no_wait)
        timeout = 0 if no_wait is True else self.timeout
        r_ready_fd, w_ready_fd, error_fd = select.select([read] if read else [],
                                                         [write] if write else [], [], timeout)
        if read is not None and read not in r_ready_fd:
            raise SSHTimeout("A timeout has occurred when waiting for new data")
        if write is not None and write not in w_ready_fd:
            raise SSHTimeout("A timeout has occurred when trying to send new data")
        return (r_ready_fd, w_ready_fd, error_fd)

    def setblocking(self, flag):
        if flag not in (0, 1):
            raise ValueError("Blocking flag must be 0 or 1 (int)")
        self.blocking = bool(flag)
        if flag == 0:
            self.timeout = 0.0
        else:
            self.timeout = None

    def settimeout(self, value):
        if type(value) not in (int, float, type(None)):
            raise ValueError("Timeout value must be int, float or NoneType")
        self.timeout = value
        if value is None:
            self.blocking = True
        elif value == 0:
            self.blocking = False

    def gettimeout(self):
        return self.timeout

    def recv_ready(self):
        self._check_child_state()
        try:
            self._select_fd(read=self._ssh_master_pty_fd, no_wait=True)
        except SSHTimeout:
            return False
        return True

    def write_ready(self):
        self._check_child_state()
        try:
            self._select_fd(write=self._ssh_master_pty_fd, no_wait=True)
        except SSHTimeout:
            return False
        return True

    def open_session(self):
        try:
            self._check_child_basic()
        except SSHNotReady:
            pass
        else:
            raise SSHProcessException("SSH is already started")
        try:
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        except ValueError:
            # ValueError: signal only works in main thread
            pass
        try:
            child_pid, master_pty_fd = pty.fork()
        except OSError, e:
            raise SSHProcessException("Error on pty.fork(): %s" % e)
        if child_pid == pty.CHILD:
            self._spawn_ssh()
        else:
            self._ssh_master_pty_fd = master_pty_fd
            self._ssh_child_pid     = child_pid
            time.sleep(0.05) # give time to kernel fork the process
            self._ssh_auth()

    def _spawn_ssh(self):
        self._close_fds()
        time.sleep(0.1) # wait the parent
        os.execvpe(self._ssh_cmd[0], self._ssh_cmd, self._get_env())
        sys.exit(127)

    @staticmethod
    def _close_fds():
        max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        for fd in xrange(3, max_fd):
            try:
                os.close(fd)
            except OSError:
                pass

    # def _redir_stderr(self, to=None):
    #     stderr_fd = sys.__stderr__.fileno()
    #     os.close(stderr_fd)
    #     sys.stderr = os.fdopen(to, "w", 0)
    #     os.dup2(to, stderr_fd)

    def _get_env(self):
        env = os.environ
        if not env.has_key("PATH"):
            env["PATH"] = self.path
        return env

    def _ssh_auth(self):
        old_block_flag    = int(self.blocking)
        old_timeout_value = self.timeout
        self.setblocking(1)
        self.settimeout(self._ssh_auth_timeout)
        try:
            self._ssh_auth_wait_passwd_prompt()
            self._ssh_auth_send_passwd()
            self._ssh_auth_wait_shell_prompt()
        finally:
            self.setblocking(old_block_flag)
            self.settimeout(old_timeout_value)

    def _ssh_auth_wait_passwd_prompt(self):
        buff = StringIO()
        while True:
            try:
                buff.write(self.recv())
            except SSHProcessException, e:
                if buff.getvalue():
                    raise SSHProcessException(buff.getvalue().strip())
                raise e
            if AUTH_PASSWD_RE.search(buff.getvalue()):
                return

    def _ssh_auth_send_passwd(self):
        self.send("%s\r\n" % self.passwd)
        time.sleep(0.1)

    def _ssh_auth_wait_shell_prompt(self):
        buff           = StringIO()
        last_read_lens = collections.deque(maxlen=10)
        crlf_sent      = False
        try:
            while True:
                #time.sleep(0.05)
                curr_line = None
                prev_line = None
                buff_recv = self.recvall()
                buff.write(buff_recv)
                buff_lines = buff.getvalue().split("\n") # some shells don't use CRLF
                last_read_lens.append(len(buff_recv))
                if len(buff_lines) == 0:
                    continue
                if len(buff_lines) >= 1:
                    curr_line = buff_lines[-1].strip()
                if len(curr_line) == 0:
                    continue
                if len(buff_lines) >= 2:
                    prev_line = buff_lines[-2].strip()
                if AUTH_PASSWD_RE.search(buff.getvalue()):
                    raise AuthenticationFailed("Authentication failed (invalid username and/or passwd)")
                staled = len(last_read_lens) == last_read_lens.maxlen and \
                                reduce(lambda x,y: x+y, last_read_lens) == 0
                if crlf_sent is False and staled is True:
                    self.send("\r\n")
                    crlf_sent = True
                    time.sleep(0.1)
                    continue
                if crlf_sent is True:
                    if (len(buff_recv) == 0 and curr_line == prev_line):
                        self.shell_prompt = curr_line
                        break
                    if staled:
                        break
        except SSHTimeout:
            self.close()
            raise AuthenticationFailed("Timeout on SSH authentication")
        except SSHProcessException, e:
            if hasattr(e, "exit_code") and getattr(e, "exit_code") == 255:
                    #\ and AUTH_ERROR_RE.search(buff.getvalue()):
                raise AuthenticationFailed("Authentication failed (invalid username and/or passwd)")
            raise e

    def recv(self, recv_bytes=4096):
        if not bytes:
            return
        if self.blocking is True:
            self._check_child_state()
            self._select_fd(read=self._ssh_master_pty_fd)
        else:
            if self.recv_ready() is False:
                raise IOError("SSH file descriptor (stdout) is not ready for read operations")
        #time.sleep(0.05) # give some time to kernel fill the buffer
        try:
            buff = os.read(self._ssh_master_pty_fd, recv_bytes)
        except (OSError, ValueError), e:
            self._check_child_state()
            raise e
        return buff

    def recvall(self):
        buff = StringIO()
        while self.recv_ready() is True:
            buff.write(self.recv(8192))
            time.sleep(0.05) # give some time to kernel fill the buffer - next recv
        return buff.getvalue()

    def send(self, data=""):
        if not data:
            return
        if self.blocking is True:
            self._check_child_state()
            self._select_fd(write=self._ssh_master_pty_fd)
        else:
            if self.write_ready() is False:
                raise IOError("SSH file descriptor (stdin) is not ready for write operations")
        #time.sleep(0.05)
        try:
            sent_bytes = os.write(self._ssh_master_pty_fd, data)
        except (OSError, ValueError), e:
            self._check_child_state()
            raise e
        return sent_bytes

    def _reset(self):
        self._ssh_child_pid     = None
        self._ssh_master_pty_fd = None
        self.shell_prompt        = None

    def close(self):
        try:
            self._check_child_state()
        except (SSHProcessException, SSHNotReady):
            pass
        finally:
            try:
                os.kill(self._ssh_child_pid, signal.SIGTERM)
                os.wait()
                os.close(self._ssh_master_pty_fd)
            except OSError:
                pass
            finally:
                self._reset()


class SystemSSHException(Exception):
    pass

#class SSHProcessException(SystemSSHException):
#    pass

class SSHProcessException(SystemSSHException):
    def __init__(self, *args, **kwargs):
        super(SSHProcessException, self).__init__()
        self.msg = args[0]
        self.__dict__.update(kwargs)
    def __str__(self):
        return repr(self.__dict__)

class SSHNotReady(SystemSSHException):
    pass

class SSHTimeout(SystemSSHException):
    pass

class AuthenticationFailed(SystemSSHException):
    pass
