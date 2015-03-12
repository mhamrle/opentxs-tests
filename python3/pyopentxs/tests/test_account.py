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


@pytest.fixture(scope='function')
def an_asset():
    return Asset().issue(Nym().register(), open(data.btc_contract_file))


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


def test_asset_count_increments():
    then = opentxs.OTAPI_Wrap_GetAssetTypeCount()
    Asset().issue(Nym().register(), open(data.btc_contract_file))
    now = opentxs.OTAPI_Wrap_GetAssetTypeCount()
    assert then + 1 == now


def test_asset_id_retrievable(an_asset):
    num_assets = opentxs.OTAPI_Wrap_GetAssetTypeCount()
    ids = [opentxs.OTAPI_Wrap_GetAssetType_ID(i) for i in range(num_assets)]
    assert an_asset._id in set(ids)


def test_asset_attributes_retrievable(an_asset):
    assert opentxs.OTAPI_Wrap_GetAssetType_Name(an_asset._id) == "Bitcoins"
    assert opentxs.OTAPI_Wrap_GetAssetType_TLA(an_asset._id) == "BTC"


def test_asset_attributes_nonexistent_id():
    """Ensure empty return value if asset id not found"""
    assert opentxs.OTAPI_Wrap_GetAssetType_Name("foo") == ""
    assert opentxs.OTAPI_Wrap_GetAssetType_TLA("bar") == ""


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


@pytest.mark.skipif(True, reason="https://github.com/Open-Transactions/opentxs/issues/364")
def test_delete_account(an_account):
    an_account.create()
    an_account.delete()


def test_account_count_increments(an_account):
    then = opentxs.OTAPI_Wrap_GetAccountCount()
    an_account.create()
    now = opentxs.OTAPI_Wrap_GetAccountCount()
    assert then + 1 == now


def test_account_asset_id_retrievable(an_account):
    an_account.create()
    asset_id = opentxs.OTAPI_Wrap_GetAccountWallet_InstrumentDefinitionID(an_account._id)
    assert asset_id == an_account.asset._id


def test_account_data_retrievable(an_account):
    an_account.name = "my foo account"
    an_account.create()
    internal_name = opentxs.OTAPI_Wrap_GetAccountWallet_Name(an_account._id)
    assert an_account.name == internal_name
    notary_id = opentxs.OTAPI_Wrap_GetAccountWallet_NotaryID(an_account._id)
    assert notary_id == an_account.server_id
    nym_id = opentxs.OTAPI_Wrap_GetAccountWallet_NymID(an_account._id)
    assert nym_id == an_account.nym._id
    acct_type = opentxs.OTAPI_Wrap_GetAccountWallet_Type(an_account._id)
    assert acct_type == "user"


def test_account_id_retrievable(an_account):
    an_account.create()
    num_accts = opentxs.OTAPI_Wrap_GetAccountCount()
    ids = [opentxs.OTAPI_Wrap_GetAccountWallet_ID(i) for i in range(num_accts)]
    assert an_account._id in set(ids)
