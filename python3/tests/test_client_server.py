import pyopentxs
import unittest
import pytest
from datetime import datetime, timedelta

# def test_check_server_id():
#     nym_id = pyopentxs.create_nym()
#     assert pyopentxs.check_server_id(get_server_id(), nym_id)

btc_contract_file = "../test-data/sample-contracts/btc.xml"


def register_new_nym():
    nym_id = pyopentxs.create_nym()
    pyopentxs.register_nym(pyopentxs.first_server_id(), nym_id)
    return nym_id


def test_register_nym():
    register_new_nym()


def test_issue_asset_contract():
    nym_id = register_new_nym()
    server_id = pyopentxs.first_server_id()
    pyopentxs.issue_asset_type(server_id, nym_id, open(btc_contract_file))

class Account(object):
    def __init__(self, nym_id):
        self.nym_id = nym_id
        self.account_id = None

class TestWriteCheque(unittest.TestCase):
    def setup_method(self, method):
        self.server_id = pyopentxs.first_server_id()

        self.source = Account(register_new_nym())
        self.target = Account(register_new_nym())

        self.issuer = Account(register_new_nym())
        self.asset = pyopentxs.issue_asset_type(self.server_id, self.issuer.nym_id, open(btc_contract_file))

        self.target.account_id = pyopentxs.create_account(self.server_id, self.target.nym_id, self.asset.asset_id)
        self.source.account_id = pyopentxs.create_account(self.server_id, self.source.nym_id, self.asset.asset_id)
        self.issuer.account_id = self.asset.issuer_account_id

        #send 100 from issuer to nym_source_id
        self.transfer(100, source=self.issuer, target=self.source)

        # check that all account has expected balance
        self.check_balance(-100, 100, 0)

    def check_balance(self, issuer, source, target):
        assert issuer == pyopentxs.get_account_balance(self.server_id, self.issuer.nym_id, self.issuer.account_id)
        assert source == pyopentxs.get_account_balance(self.server_id, self.source.nym_id, self.source.account_id)
        assert target == pyopentxs.get_account_balance(self.server_id, self.target.nym_id, self.target.account_id)

    def transfer(self, amount, source=None, target=None, valid_from = -1, valid_to=1000, valid=True):
        if not source:
            source = self.source
        if not target:
            target = self.target
        now = datetime.utcnow()
        cheque = pyopentxs.Cheque(self.server_id, amount, now + timedelta(0, valid_from), now + timedelta(0, valid_to),
                      source.account_id, source.nym_id, "memo", target.nym_id)

        cheque.write()
        deposit = cheque.deposit(target.nym_id, target.account_id)
        if valid:
            assert pyopentxs.is_message_success(deposit)
        else:
            with pytest.raises(pyopentxs.ReturnValueError):
                pyopentxs.is_message_success(deposit)
        return cheque

    def test_one_deposit(self):
        self.transfer(10)
        self.check_balance(-100, 90, 10)

    def test_not_enough_funds(self):
        #first attempt fails because source does not have enough funds
        cheque = self.transfer(200, valid=False)
        self.check_balance(-100, 100, 0)
        
        #now transfer more funds to source
        self.transfer(100, source=self.issuer, target=self.source)
        #and repeat cheque deposit
        deposit = cheque.deposit(self.target.nym_id, self.target.account_id)
        assert pyopentxs.is_message_success(deposit)

        self.check_balance(-200, 0, 200)

    def test_two_deposits(self):
        cheque = self.transfer(10)

        # check balance after first transfer
        self.check_balance(-100, 90, 10)

        # second deposit should fail
        deposit = cheque.deposit(self.target.nym_id, self.target.account_id)
        with pytest.raises(pyopentxs.ReturnValueError):
            pyopentxs.is_message_success(deposit)

        # check that balance is not changed by second deposit
        self.check_balance(-100, 90, 10)

    def test_expired_cheque(self):
        self.transfer(10, valid_from=-100, valid_to=-1, valid=False)
        self.check_balance(-100, 100, 0)

    def test_not_yet_valid_cheque(self):
        self.transfer(10, valid_from=10, valid_to=100, valid=False)
        self.check_balance(-100, 100, 0)

    def test_negative_transfer(self):
        self.transfer(-10, valid=False)
        self.check_balance(-100, 100, 0)
        

def test_create_account():
    server_id = pyopentxs.first_server_id()
    nym_id = register_new_nym()
    asset = pyopentxs.issue_asset_type(server_id, nym_id, open(btc_contract_file))
    account_id = pyopentxs.create_account(server_id, nym_id, asset.asset_id)

    accounts = pyopentxs.get_account_ids()

    assert account_id in accounts
