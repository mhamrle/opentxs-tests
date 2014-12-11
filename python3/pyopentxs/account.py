from pyopentxs import ReturnValueError
from pyopentxs.nym import Nym
import opentxs

from bs4 import BeautifulSoup
from pyopentxs import otme
import re


class Account:
    def __init__(self, asset=None, nym=None, server_id=None, _id=None):
        self.server_id = server_id or (asset and asset.server_id)
        self.nym = nym or Nym().register()
        self.asset = asset
        self._id = _id

    def create(self):
        if self._id:
            raise ValueError("Can't create the same account twice,\
            to create an account of the same type, create a new Account object first.")
        account_xml = otme.create_asset_acct(self.server_id, self.nym._id, self.asset._id)
        s = BeautifulSoup(account_xml)
        if s.registeraccountresponse:
            self._id = s.registeraccountresponse['accountid']
            return self

        if s.createaccountresponse:
            self._id = s.createaccountresponse['accountid']
            return self

        # raise ReturnValueError("No account id present in response, account not created.")

        # try the old way (todo: remove once all PR's before the change
        # to the *Response suffix are closed).
        valid_xml = re.sub("<@createAccount", "<createAccount", account_xml)
        s = BeautifulSoup(valid_xml)
        if s.createaccount:
            self._id = s.createaccount['accountid']
            return self
        # end of old way

        raise ReturnValueError("No account id present in response, account not created.")

    def delete(self):
        deleted = opentxs.OTAPI_Wrap_deleteAssetAccount(self.server_id, self.nym._id, self._id)
        print("deleting {} returned {}".format(self._id, deleted))
        assert deleted > 0, "Unable to delete account {}, return code {}".format(self._id, deleted)

    def balance(self):
        """
        refresh local account files from server and return account balance
        """
        assert self._id, "Account must be created first."
        
        if hasattr(opentxs, 'OTAPI_Wrap_getAccountData'): # new api name
            res = opentxs.OTAPI_Wrap_getAccountData(self.server_id, self.nym._id, self._id)
        else: # old api name, remove in due time
            res = opentxs.OTAPI_Wrap_getAccountFiles(self.server_id, self.nym._id, self._id)
        if res < 0:
            raise ReturnValueError(res)
        return opentxs.OTAPI_Wrap_GetAccountWallet_Balance(self._id)

    def __repr__(self):
        return "<Account id={}, asset={}, nym={}, server_id={}>".format(
            self._id, self.asset, self.nym, self.server_id)


def get_all_ids():
    account_count = opentxs.OTAPI_Wrap_GetAccountCount()
    accounts = []
    for i in range(account_count):
        _id = opentxs.OTAPI_Wrap_GetAccountWallet_ID(i)
        accounts.append(_id)

    return accounts
