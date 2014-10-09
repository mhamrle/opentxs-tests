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

def transfer_cheque(self, amount, source=None, target=None, valid_from = -1, valid_to=1000, valid=True):
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
    
def transfer_voucher(self, amount, source=None, target=None, valid_from = -1, valid_to=1000, valid=True):
    if not source:
        source = self.source
    if not target:
        target = self.target

    voucher = pyopentxs.Voucher(self.server_id, amount, source.account_id, source.nym_id, "memo", target.nym_id)

    if valid:
        voucher.generate()
    else:
        with pytest.raises(pyopentxs.ReturnValueError):
            voucher.generate()
        return

    deposit = voucher.deposit(target.nym_id, target.account_id)
    if valid:
        assert pyopentxs.is_message_success(deposit)
    else:
        with pytest.raises(pyopentxs.ReturnValueError):
            pyopentxs.is_message_success(deposit)
    

@pytest.fixture(params=(transfer_cheque, transfer_voucher), ids=("transfer_cheque", "transfer_voucher"))
def transfer_generic(request):
    return request.param

@pytest.fixture()
def prepared_accounts(request):
    class TransferAccounts:
        def setup_method(self):
            self.server_id = pyopentxs.first_server_id()

            self.source = Account(register_new_nym())
            self.target = Account(register_new_nym())

            self.issuer = Account(register_new_nym())
            self.asset = pyopentxs.issue_asset_type(self.server_id, self.issuer.nym_id, open(btc_contract_file))

            self.target.account_id = pyopentxs.create_account(self.server_id, self.target.nym_id, self.asset.asset_id)
            self.source.account_id = pyopentxs.create_account(self.server_id, self.source.nym_id, self.asset.asset_id)
            self.issuer.account_id = self.asset.issuer_account_id

            #send 100 from issuer to nym_source_id
            transfer_cheque(self, 100, source=self.issuer, target=self.source)

            # check that all account has expected balance
            self.check_balance(-100, 100, 0)
        def check_balance(self, issuer, source, target):
            assert issuer == pyopentxs.get_account_balance(self.server_id, self.issuer.nym_id, self.issuer.account_id)
            assert source == pyopentxs.get_account_balance(self.server_id, self.source.nym_id, self.source.account_id)
            assert target == pyopentxs.get_account_balance(self.server_id, self.target.nym_id, self.target.account_id)
    ret = TransferAccounts()
    ret.setup_method()
    return ret

class TestGenericTransfer:
    @pytest.mark.parametrize("amount,should_pass", [
    # TODO: this crash in voucher
    #    (-10, False),
    # TODO: this crash
    #    (0, True),
        (10, True),
        (200, False),
    ])
    def test_simple_transfer(self, prepared_accounts, transfer_generic, amount, should_pass):
        transfer_generic(prepared_accounts, amount, valid = should_pass)
        if should_pass:
            prepared_accounts.check_balance(-100, 100 - amount, amount)
        else:
            prepared_accounts.check_balance(-100, 100, 0)

class TestChequeTransfer:
    @pytest.mark.parametrize("amount,first_valid,later_income,second_valid", [
        # not enough funds
        (200, False, 100, True),
        (200, False, 50, False),
        # cheque can ube used only once
        (10, True, 0, False),
        (10, True, 1, False),
    ])
    def test_deposit_twice(self, prepared_accounts, amount,first_valid,later_income,second_valid):
        # create cheque and try to deposit it
        cheque = transfer_cheque(prepared_accounts, amount, valid=first_valid)

        expected_source = 100
        expected_target = 0
        if (first_valid):
            expected_source -= amount
            expected_target += amount
        prepared_accounts.check_balance(-100, expected_source, expected_target)
        
        #now transfer more funds to source
        if later_income != 0:
            transfer_cheque(prepared_accounts, later_income, source=prepared_accounts.issuer, target=prepared_accounts.source)
        expected_source += later_income

        #and repeat cheque deposit
        deposit = cheque.deposit(prepared_accounts.target.nym_id, prepared_accounts.target.account_id)
        if second_valid:
            expected_source -= amount
            expected_target += amount
            assert pyopentxs.is_message_success(deposit)
        else:
            with pytest.raises(pyopentxs.ReturnValueError):
                assert pyopentxs.is_message_success(deposit)

        prepared_accounts.check_balance(-100 - later_income, expected_source, expected_target)

    @pytest.mark.parametrize("valid_from,valid_to,valid", [
        # valid cheque
        (-100, 100, True),
        # cheque is expired
        (-100, -50, False),
        # not yet valid
        (500, 100, False),
        # incorrect intervals
        (-100, -200, False),
        (100, -100, False),
        (200, 100, False),
    ])
    def test_expired_cheque(self, prepared_accounts, valid_from, valid_to, valid):
        transfer_cheque(prepared_accounts, 10, valid_from=valid_from, valid_to=valid_to, valid=valid)
        if valid:
            prepared_accounts.check_balance(-100, 90, 10)
        else:
            prepared_accounts.check_balance(-100, 100, 0)

    #TODO: test cheque discard

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

    def test_maximal_amount(self):
        self.check_balance(-100, 100, 0)
        maxint = 2**63 - 1
        self.transfer(maxint - 100, source=self.issuer, target=self.target)
        self.check_balance(-maxint, 100, maxint - 100)

        self.transfer(1, source=self.issuer, target=self.target)
        self.check_balance(-maxint - 1, 100, maxint - 100 + 1)
        
        #TODO integer overflow
        self.transfer(1, source=self.issuer, target=self.target)
        self.check_balance(-maxint - 2, 100, maxint - 100 + 2)
        
    def test_maximal_amount2(self):
        self.check_balance(-100, 100, 0)
        maxint = 2**63 - 1
        self.transfer(maxint - 100, source=self.issuer, target=self.target)
        self.check_balance(-maxint, 100, maxint - 100)

        self.transfer(maxint, source=self.issuer, target=self.target, valid=False)
        self.check_balance(-maxint, 100, maxint - 100)

    def test_maximal_amount3(self):
        self.check_balance(-100, 100, 0)
        maxint = 2**63 - 1
        self.transfer(maxint - 100, source=self.issuer, target=self.target)
        self.check_balance(-maxint, 100, maxint - 100)

        self.transfer(1, source=self.issuer, target=self.target)
        self.check_balance(-maxint - 1, 100, maxint - 100 + 1)

        #TODO integer overflow
        self.transfer(50, source=self.issuer, target=self.target)
        self.check_balance(-maxint - 1 - 50, 100, maxint - 100 + 1 + 50)

def test_create_account():
    server_id = pyopentxs.first_server_id()
    nym_id = register_new_nym()
    asset = pyopentxs.issue_asset_type(server_id, nym_id, open(btc_contract_file))
    account_id = pyopentxs.create_account(server_id, nym_id, asset.asset_id)

    accounts = pyopentxs.get_account_ids()

    assert account_id in accounts
