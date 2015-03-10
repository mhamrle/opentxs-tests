import pyopentxs
import opentxs
from pyopentxs import nym, config_dir, decode, server
from contextlib import closing
from bs4 import BeautifulSoup
import io
import os
import shutil
import configparser
import subprocess


def make_server_contract(contract, server_nym):
    '''Takes a stream for a template contract, returns a tuple of
       (contract, cached_key, decoded_signed_contract)'''
    server_contract = server.add(server_nym._id, contract)
    walletxml = decode(open(config_dir + "client_data/wallet.xml"))
    cached_key = BeautifulSoup(walletxml).wallet.cachedkey.string.strip()
    signed_contract_file = config_dir + "client_data/contracts/" + server_contract
    with closing(open(signed_contract_file)) as f:
        signed_contract = f.read()
    decoded_signed_contract = decode(io.StringIO(signed_contract))
    return (server_contract, cached_key, decoded_signed_contract)


def setup(contract_stream, total_servers=1):
    '''
    Helps create a clean config dir starting from scratch.
    contract_stream is an input stream pointing to a template contract file.
    total_servers is an integer, of how many servers the client should have on file.
    Only the first server will actually exist, the rest will appear as offline.
    '''
    pyopentxs.init()
    server_nym = nym.Nym().create()

    contract = contract_stream.read()
    contract_stream.close()

    server_contract_id, cached_key, decoded_signed_contract \
        = make_server_contract(contract, server_nym)

    walletxml = decode(open(config_dir + "client_data/wallet.xml"))
    cached_key = BeautifulSoup(walletxml).wallet.cachedkey.string.strip()
    signed_contract_file = config_dir + "client_data/contracts/" + server_contract_id
    with closing(open(signed_contract_file)) as f:
        signed_contract = f.read()
    decoded_signed_contract = decode(io.StringIO(signed_contract))

    # copy the credentials to the server
    server_data_dir = config_dir + "server_data/"
    if not os.path.exists(server_data_dir):
        os.mkdir(server_data_dir)
    shutil.copytree(config_dir + "client_data/credentials", server_data_dir + "credentials")
    # remove the client-side data
    shutil.rmtree(config_dir + "client_data")

    # reread the client data (empty)
    pyopentxs.init()
    print("reread client data")
    # since we still don't have programmatic access, just write the info
    # to use later to pipe to the notary process
    output = io.BytesIO()
    writeit = lambda s: output.write(s.encode("utf-8"))
    writeit(server_contract_id + "\n")
    writeit(server_nym._id + "\n")
    writeit(cached_key + "\n~\n~\n")
    writeit(decoded_signed_contract + "\n~\n")

    # the following crashes the process, so we pipe the info manually
    # opentxs.MainFile(None).CreateMainFile(signed_contract, server_contract_id, "", server_nym,
    # cached_key)

    # add the server contract on the client side
    opentxs.OTAPI_Wrap_AddServerContract(decoded_signed_contract)

    # should be just one known active server now
    server.active = [server_contract_id]

    # create any extra fake servers
    for _ in range(total_servers - 1):
        opentxs.OTAPI_Wrap_AddServerContract(
            make_server_contract(contract, nym.Nym().create())[2])

    return output


def restart():
    process_name = "opentxs-notary"
    pyopentxs.killall(process_name)

    # danger, also kill any goataries,
    # since they occupy the same port
    pyopentxs.killall("notary")

    os.system("%s > %s 2>&1 &" % (process_name, "opentxs-notary.log"))
    print("Started %s process" % process_name)
    pyopentxs.init()


def create_fresh_ot_config():
    pyopentxs.create_fresh_wallet()
    # create server contract and empty the client side data
    setup_data = setup(open('../test-data/sample-contracts/localhost.xml'), total_servers=2)
    p = subprocess.Popen(["opentxs-notary", "--only-init"], stdin=subprocess.PIPE)
    outs, errs = p.communicate(input=setup_data.getvalue(), timeout=20)

    # set cron interval to shorter than default
    config_data = config.read()
    config_data['cron']['ms_between_cron_beats'] = '2500'  # in milliseconds
    config.write()


def fresh_setup():
    '''opentxs-notary must be on the PATH'''

    create_fresh_ot_config()
    print("created fresh config, restarting...")
    restart()
    print("restarted.")


class Config:
    def __init__(self, filename=None):
        self.filename = filename or pyopentxs.config_dir + "server.cfg"

    def read(self):
        '''Retrieves the server config file and parses it'''
        self.parser = configparser.ConfigParser()
        self.parser.read(pyopentxs.config_dir + "server.cfg")
        return self.parser

    def write(self):
        f = open(self.filename, 'w')
        self.parser.write(f)
        f.close()

config = Config()
