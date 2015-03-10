import opentxs
from contextlib import closing
import os
import sys
import psutil
import shutil
import pyopentxs

# OTME = OpenTransactions MadeEasy
otme = opentxs.OT_ME()

# The directory where OT stores its state
config_dir = os.environ['HOME'] + "/.ot/"


class ReturnValueError(BaseException):
    """
    The return value of an API function has signaled an error condition
    """
    def __init__(self, return_value):
        self.return_value = return_value

    def __str__(self):
        return "API function has returned error value %r" % self.return_value


class ProcessUserCommand:
    """
    These return values are used by ProcessUserCommand() and bubble up
    to different higher-level APIs. The return value is documented in
    OTClient::ProcessUserCommand()
    """
    # TODO: currently unused. remove or use

    # error, don't send message
    Error = 0               # error, don't send message

    # no error, no message sent
    NoMessageSent = -1

    # Paraphrasing the documentation
    # message is sent, no request number returns > 0 for
    # processInbox, containing the number that was there
    # before processing -- FIXME unclear
    MessageSent = 1

    # This is sometimes returned by  OTClient::CalcReturnVal()
    # Low-level networking error
    RequestNumberMismatch = -2


def decode(stream):
    ''', and return as string'''
    with closing(stream):
        decoded = opentxs.OTAPI_Wrap_Decode(stream.read(), True)
    return decoded


def is_message_success(message):
    '''Returns true if message has success=true'''
    if message == '':
        raise ReturnValueError(message)
    else:
        return opentxs.OTAPI_Wrap_Message_GetSuccess(message) == 1


def _remove_pid():
    """
    Remove the PID file if one exists
    """

    # There should not be a long-running opentxs client running anyway.
    # An existing PID file probably indicates a crashed process, not a running
    # instance
    pid_file = os.path.expanduser("~/.ot/client_data/ot.pid")
    if os.path.exists(pid_file):
        print("removing lockfile %s" % pid_file, file=sys.stderr)
        os.remove(pid_file)


def init():
    """
    Initialize the OTAPI in order to get a working state
    """
    # This should only be done once per process.
    _remove_pid()
    opentxs.OTAPI_Wrap_AppInit()
    opentxs.OTAPI_Wrap_LoadWallet()


def cleanup():
    opentxs.OTAPI_Wrap_AppCleanup()


def killall(process_name):
    for proc in psutil.process_iter():
        if proc.name() == process_name:
            proc.kill()
            psutil.wait_procs([proc], timeout=10)
    print("killed all %s" % process_name)


def create_fresh_wallet():
    # this creates fresh data in OT client data dir
    if os.path.exists(pyopentxs.config_dir):
        shutil.rmtree(pyopentxs.config_dir)

    # create a client wallet just for making the server contract
    os.system("opentxs --dummy-passphrase changepw")
