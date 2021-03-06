#!/usr/bin/env python3
import shutil
import psutil
import os
import sys
import pytest
import pyopentxs
from pyopentxs import notary
import subprocess


def create_fresh_ot_config():
    # this creates fresh data in ../ot-clean-data/.ot
    if os.path.exists(pyopentxs.config_dir):
        shutil.rmtree(pyopentxs.config_dir)

    # create a client wallet just for making the server contract
    os.system("opentxs --dummy-passphrase changepw")

    # create server contract and empty the client side data
    setup_data = notary.setup(open('../test-data/sample-contracts/localhost.xml'), total_servers=2)
    p = subprocess.Popen(["opentxs-notary", "--only-init"], stdin=subprocess.PIPE)
    outs, errs = p.communicate(input=setup_data.getvalue(), timeout=20)


def restart_opentxs_notary():
    '''opentxs-notary must be on the PATH'''
    # kill existing processes
    for proc in psutil.process_iter():
        if proc.name() == "opentxs-notary":
            proc.kill()
            psutil.wait_procs([proc], timeout=10)

    create_fresh_ot_config()

    # start new
    os.system("opentxs-notary > opentxs-notary.log 2>&1 &")

    # wait for ready
    # doesn't seem to be necessary
    # time.sleep(2)


def fresh_setup():
    restart_opentxs_notary()
    pyopentxs.init()


if __name__ == "__main__":
    restart_opentxs_notary()
    pyopentxs.init()
    pytest.main(sys.argv[1:])
    pyopentxs.cleanup()
