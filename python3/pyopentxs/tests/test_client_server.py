import pytest
from pyopentxs import (server, ReturnValueError, is_message_success, error, instrument)
from pyopentxs.nym import Nym
from pyopentxs.asset import Asset
from pyopentxs.account import Account
from datetime import datetime, timedelta
from pyopentxs.instrument import transfer, write
from pyopentxs.tests import data
from pyopentxs import cash

# def test_check_server_id():
#     nym_id = pyopentxs.create_nym()
#     assert pyopentxs.check_server_id(get_server_id(), nym_id)


@pytest.mark.parametrize("issue_for_other_nym,expect_success", [[True, False], [False, True]])
@pytest.mark.goatary
def test_issue_asset_contract(issue_for_other_nym, expect_success):
    server_id = server.first_active_id()
    nym = Nym().register(server_id)
    issue_for_nym = Nym().register(server_id) if issue_for_other_nym else nym
    with error.expected(None if expect_success else ReturnValueError):
        Asset().issue(nym, open(data.btc_contract_file), server_id, issue_for_nym=issue_for_nym)


def new_cheque(source, target, amount, valid_from=-10000, valid_to=10000, source_nym=None):
    now = datetime.utcnow()
    return instrument.Cheque(
        source.server_id,
        amount,
        now + timedelta(0, valid_from),
        now + timedelta(0, valid_to),
        source,
        source_nym or source.nym,
        "test cheque!",
        target.nym
    )


def new_voucher(source, target, amount, source_nym=None):
    return instrument.Voucher(
        source.server_id, amount, source, source_nym or source.nym, "test cheque!", target.nym)


def new_transfer(source, target, amount):
    return amount


def new_cash(_, __, amount):
    return instrument.Cash(amount)


class TestGenericTransfer:
    def pytest_generate_tests(self, metafunc):
        transfer_amount_data = [
            (-10, False),
            (10, True),
            (200, False),
            (0, False),
            (2 ** 63 - 100, False),
            (2 ** 63 - 1, False),
            (-(2 ** 63), False),
        ]
        instrument_data = [
            new_cheque,
            new_voucher,
            new_transfer,
            new_cash
        ]
        metafunc.parametrize("amount,should_pass", argvalues=transfer_amount_data)
        metafunc.parametrize("instrument_constructor", argvalues=instrument_data)

    def test_simple_transfer(self, prepared_accounts, amount, should_pass, instrument_constructor):
        instrument = instrument_constructor(
            prepared_accounts.source, prepared_accounts.target, amount)

        if instrument_constructor == new_cash:
            # skip if testing with large amount
            if amount > 1000:
                pytest.skip("https://github.com/Open-Transactions/opentxs/issues/536")
            # make sure there's a mint created for this asset
            cash.create_mint(prepared_accounts.asset)

        with error.expected(None if should_pass else ReturnValueError):
            transfer(instrument, prepared_accounts.source, prepared_accounts.target)
        if should_pass:
            prepared_accounts.assert_balances(-100, 100 - amount, amount)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)


class TestIssuerGenericTransfer:
    def pytest_generate_tests(self, metafunc):
        transfer_amount_data = [
            (-10, False),
            (0, False),
            (10, True),
            # this is the maximal amount that we can transfer, so issuer balance is INT64_MIN
            (2 ** 63 - 100, True),
            # now we transfer so big amount that issuer balance should be INT64_MIN - 1
            (2 ** 63 - 100 + 1, False),
        ]
        instrument_data = [new_cheque,
                           new_voucher,
                           new_transfer]
        metafunc.parametrize("amount,should_pass", argvalues=transfer_amount_data)
        metafunc.parametrize("instrument_constructor", argvalues=instrument_data)

    def test_simple_transfer(self, prepared_accounts, amount, should_pass, instrument_constructor):
        instrument = instrument_constructor(
            prepared_accounts.issuer, prepared_accounts.target, amount)
        with error.expected(None if should_pass else ReturnValueError):
            transfer(instrument, prepared_accounts.issuer, prepared_accounts.target)
        if should_pass:
            prepared_accounts.assert_balances(-100 - amount, 100, amount)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)


@pytest.mark.parametrize("instrument_constructor", [new_cheque, new_voucher])
def test_not_account_owner(prepared_accounts, instrument_constructor):
    '''Test that we get a graceful failure when we try to deposit an
       instrument for an account we don't own'''

    instrument = instrument_constructor(
        prepared_accounts.source, prepared_accounts.target, 50,
        source_nym=prepared_accounts.target.nym)
    with error.expected(ReturnValueError):
        transfer(instrument, prepared_accounts.source, prepared_accounts.target)


@pytest.mark.parametrize("instrument_constructor",
                         [new_cheque,

                          pytest.mark.skipif(
                              True,
                              reason="https://github.com/Open-Transactions/opentxs/issues/324")
                          ((new_voucher,)),

                          new_transfer])
def test_wrong_asset_type(instrument_constructor):
    '''Try to transfer eg a cheque from one asset account to another of a
       different type. Should fail'''
    ta_asset1 = data.TransferAccounts().initial_balance()
    ta_asset2 = data.TransferAccounts().initial_balance()
    source = ta_asset1.source
    target = ta_asset2.target
    instrument = instrument_constructor(source, target, 50)
    with error.expected(ReturnValueError):
        transfer(instrument, source, target)
    ta_asset2.assert_balances(-100, 100, 0)


@pytest.mark.parametrize("instrument_constructor",
                         [new_cheque, new_voucher])
def test_cancel_instrument(instrument_constructor):
    '''Cancel an instrument and make sure it can't be deposited.'''
    accounts = data.TransferAccounts().initial_balance()
    instrument = instrument_constructor(accounts.source, accounts.target, 50)
    write(instrument)
    instrument.cancel()
    with error.expected(ReturnValueError):
        instrument.deposit(accounts.target.nym, accounts.target)
    accounts.assert_balances(-100, 100, 0)


class TestChequeTransfer:
    @pytest.mark.parametrize("amount,first_valid,later_income,second_valid", [
        # not enough funds
        (200, False, 100, True),
        (200, False, 50, False),
        # cheque can be used only once
        (10, True, 0, False),
        (10, True, 1, False),
    ])
    def test_deposit_twice(self, prepared_accounts, amount, first_valid, later_income,
                           second_valid):
        # create cheque and try to deposit it
        cheque = new_cheque(prepared_accounts.source, prepared_accounts.target, amount)
        with error.expected(None if first_valid else ReturnValueError):
            transfer(cheque, prepared_accounts.source, prepared_accounts.target)

        expected_source = 100
        expected_target = 0
        if (first_valid):
            expected_source -= amount
            expected_target += amount
        prepared_accounts.assert_balances(-100, expected_source, expected_target)

        # now transfer more funds to source
        if later_income != 0:
            income = new_cheque(prepared_accounts.issuer, prepared_accounts.source, later_income)
            transfer(income, prepared_accounts.issuer, prepared_accounts.source)
        expected_source += later_income

        # and repeat cheque deposit
        with error.expected(None if second_valid else ReturnValueError):
            deposit = cheque.deposit(prepared_accounts.target.nym, prepared_accounts.target)
        if second_valid:
            expected_source -= amount
            expected_target += amount
            assert is_message_success(deposit)

        prepared_accounts.assert_balances(-100 - later_income, expected_source, expected_target)

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
        with error.expected(None if valid else ReturnValueError):
            transfer(new_cheque(prepared_accounts.source, prepared_accounts.target, 10,
                                valid_from, valid_to),
                     prepared_accounts.source,
                     prepared_accounts.target)
        if valid:
            prepared_accounts.assert_balances(-100, 90, 10)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)

    @pytest.mark.parametrize("recipient_is_blank", [True, False])
    def test_write_cheque_to_unregistered_nym(self, prepared_accounts, recipient_is_blank):
        unreg_nym = Nym().create()
        now = datetime.utcnow()
        c = instrument.Cheque(
            prepared_accounts.source.server_id,
            50,
            now + timedelta(0, -1000),
            now + timedelta(0, 1000),
            prepared_accounts.source,
            prepared_accounts.source.nym,
            "test cheque!",
            None if recipient_is_blank else unreg_nym
        )
        c.write()
        # now register the nym and deposit
        unreg_nym.register()
        new_acct = Account(prepared_accounts.source.asset, unreg_nym).create()
        c.deposit(unreg_nym, new_acct)
        prepared_accounts.assert_balances(-100, 50, 0)

    def test_send_cheque(self, prepared_accounts):
        amount = 10
        cheque = new_cheque(prepared_accounts.source, prepared_accounts.target, amount)
        result = cheque.send()
        assert result, "failed to send cheque"
        cheque.deposit(prepared_accounts.target.nym, prepared_accounts.target)
        prepared_accounts.assert_balances(-100, 100 - amount, amount)


@pytest.mark.parametrize("recipient_is_blank",
                         [pytest.mark.skipif(
                             True,
                             reason="https://github.com/Open-Transactions/opentxs/issues/388")
                          ([True]), False])
def test_withdraw_voucher_to_unregistered_nym(prepared_accounts, recipient_is_blank):
    unreg_nym = Nym().create()
    v = instrument.Voucher(
        prepared_accounts.source.server_id,
        50,
        prepared_accounts.source,
        prepared_accounts.source.nym,
        "test cheque!",
        None if recipient_is_blank else unreg_nym
    )
    v.withdraw()
    # now register the nym and deposit
    unreg_nym.register()
    new_acct = Account(prepared_accounts.source.asset, unreg_nym).create()
    v.deposit(unreg_nym, new_acct)
    prepared_accounts.assert_balances(-100, 50, 0)


# def test_auditor_traffic():
#     '''Test that generates specific traffic for the auditor.
#     see https://docs.google.com/a/monetas.net/\
#     document/d/1q9LxqSaywjM_20uGfl5msL-EFWkxxaotbZpI9c0zhAE/edit#
#     '''
#     alice = Nym().register()
#     opentxs.OTAPI_Wrap_getRequest()
#     asset = Asset().issue(alice, open(data.btc_contract_file),
#                           alice.server_id)
#     alice_issuer_account = asset.issuer_account
#     downloaded = opentxs.OTAPI_Wrap_getAccountFiles(
#         alice.server_id,
#         alice._id,
#         alice_issuer_account._id
#     )
#     if downloaded < 0:
#         raise ReturnValueError(
#             "Could not get accountFiles, returned {}".format(downloaded))
#     txnum = opentxs.OTAPI_Wrap_getTransactionNumber(alice.server_id,
#                                                     alice._id)
#     gotnymbox = opentxs.OTAPI_Wrap_getNymbox(alice.server_id,
#                                              alice._id)
#     if downloaded < 0:
#         raise ReturnValueError("Couldn't get nymbox, returned {}".format(gotnymbox))

#     boxreceipt = opentxs.OTAPI_Wrap_getBoxReceipt(
#         alice.server_id,
#         alice._id,
#         alice_issuer_account._id,
#     )

@pytest.mark.parametrize("amount,should_pass",
                         [[-10, True],
                          [-110, False],
                          [10, False]])
def test_invoice(prepared_accounts, amount, should_pass):
    '''an invoice is just a cheque for a negative amount, so the target
       will invoice the source by writing him a cheque for a negative
       amount.  After a successful deposit, funds move from source to
       target.

    '''
    invoice = new_cheque(prepared_accounts.target, prepared_accounts.source, amount)
    invoice.write()
    with error.expected(None if should_pass else ReturnValueError):
        invoice.deposit(prepared_accounts.source.nym, prepared_accounts.source)
    prepared_accounts.assert_balances(-100,
                                      100 + amount if should_pass else 100,
                                      -amount if should_pass else 0)


@pytest.mark.parametrize("amount",
                         [10, 2 ** 63 - 100 - 1, -10, -100])
def test_issuer_bidirectional(prepared_accounts, amount):
    '''Test a cheque and then an invoice for the same amount, from issuer
    to source (or the other way around)'''
    first_transfer = new_cheque(prepared_accounts.issuer, prepared_accounts.source, amount)
    transfer(first_transfer, prepared_accounts.issuer, prepared_accounts.source)
    prepared_accounts.assert_balances(-100 - amount, 100 + amount, 0)
    second_transfer = new_cheque(prepared_accounts.issuer, prepared_accounts.source, -amount)
    transfer(second_transfer, prepared_accounts.issuer, prepared_accounts.source)
    prepared_accounts.assert_balances(-100, 100, 0)
