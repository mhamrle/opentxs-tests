from pyopentxs.nym import Nym
from pyopentxs.asset import Asset
from pyopentxs import account, error, ReturnValueError, server
from pyopentxs.tests import data
import pytest
import opentxs


@pytest.fixture(scope='function')
def an_account():
    '''Generates a test account (non-issuer)'''
    nym = Nym().register()
    asset = Asset().issue(nym, open(data.btc_contract_file))
    return account.Account(asset, Nym().register())


def test_create_account(an_account):
    an_account.create()
    accounts = account.get_all_ids()
    assert an_account._id in accounts


def test_account_nym_not_registered():
    nym = Nym().register()
    asset = Asset().issue(nym, open(data.btc_contract_file))
    with error.expected(ReturnValueError):
        account.Account(asset, Nym().create()).create()


def test_asset_nym_not_registered():
    with error.expected(ReturnValueError):
        Asset().issue(Nym().create(), open(data.btc_contract_file))


def test_two_assets_same_nym_and_contract():
    '''Should be able to create two asset types with the same contract'''
    nym = Nym().register()
    asset1 = Asset().issue(nym, open(data.btc_contract_file))
    asset2 = Asset().issue(nym, open(data.btc_contract_file))
    assert asset1._id != asset2._id


def test_two_accounts_same_nym_and_asset(an_account):
    '''Test that a nym can create two accounts of the same asset type'''
    second_account = account.Account(an_account.asset, an_account.nym).create()
    assert an_account._id != second_account._id


def test_create_account_nonexistent_asset():
    '''Test that we can't create an account for an asset that doesn't exist'''
    fake_id = Nym().create()._id  # just to get a plausible asset id
    fake_asset = Asset(_id=fake_id, server_id=server.first_active_id())
    acct = account.Account(fake_asset, Nym().register())
    with error.expected(ReturnValueError):
        acct.create()

@pytest.mark.parametrize("parse_string,value,formatted,formatted_symbol", [
    ["12,345", 12345000, "12,345.000", "BTC 12,345.000"],
    ["1", 1000, "1.000", "BTC 1.000"],
    ["0", 0, "0.000", "BTC 0.000"],
    ["-0", 0, "0.000", "BTC 0.000"],
    ["0.001", 1, "0.001", "BTC 0.001"],
    ["-0.001", -1, "-0.001", "-BTC 0.001"],
    ["-12,345", -12345000, "-12,345.000", "-BTC 12,345.000"],
    # 2**62
    ["4611686018427387.904", 4611686018427387904, "4,611,686,018,427,387.904", "BTC 4,611,686,018,427,387.904"],
    # -2**62
    ["-4611686018427387.904", -4611686018427387904, "-4,611,686,018,427,387.904", "-BTC 4,611,686,018,427,387.904"],
    ])
def test_amount_format_btc(parse_string, value, formatted, formatted_symbol):
    nym = Nym().register()
    asset = Asset().issue(nym, open(data.btc_contract_file))
    assert value == opentxs.OTAPI_Wrap_StringToAmount(asset._id, parse_string)
    assert value == opentxs.OTAPI_Wrap_StringToAmount(asset._id, formatted)
    assert formatted == opentxs.OTAPI_Wrap_FormatAmountWithoutSymbol(asset._id, value)
    assert formatted_symbol == opentxs.OTAPI_Wrap_FormatAmount(asset._id, value)

@pytest.mark.parametrize("parse_string,value,formatted,formatted_symbol", [
    ["12,345", 12345, "12,345", "sg 12,345"],
    ["1", 1, "1", "sg 1"],
    ["0", 0, "0", "sg 0"],
    ["-0", 0, "0", "sg 0"],
    ["-1", -1, "-1", "-sg 1"],
    ["-12,345", -12345, "-12,345", "-sg 12,345"],
    # TODO is it correct?
    ["--1000", -1000, "-1,000", "-sg 1,000"],
    # 2**62
    ["4611686018427387904", 4611686018427387904, "4,611,686,018,427,387,904", "sg 4,611,686,018,427,387,904"],
    # -2**62
    ["-4611686018427387904", -4611686018427387904, "-4,611,686,018,427,387,904", "-sg 4,611,686,018,427,387,904"],
    ])
def test_amount_format_silver(parse_string, value, formatted, formatted_symbol):
    nym = Nym().register()
    asset = Asset().issue(nym, open(data.silver_contract_file))
    assert value == opentxs.OTAPI_Wrap_StringToAmount(asset._id, parse_string)
    assert value == opentxs.OTAPI_Wrap_StringToAmount(asset._id, formatted)
    assert formatted == opentxs.OTAPI_Wrap_FormatAmountWithoutSymbol(asset._id, value)
    assert formatted_symbol == opentxs.OTAPI_Wrap_FormatAmount(asset._id, value)


def test_amount_format_error():
    nym = Nym().register()
    asset = Asset().issue(nym, open(data.silver_contract_file))
    assert 0 == opentxs.OTAPI_Wrap_StringToAmount(asset._id, "XXXX")
    assert 0 == opentxs.OTAPI_Wrap_StringToAmount(asset._id, "")

@pytest.mark.skipif(True, reason="https://github.com/Open-Transactions/opentxs/issues/364")
def test_delete_account(an_account):
    an_account.create()
    an_account.delete()
