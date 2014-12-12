from pyopentxs.nym import Nym
from pyopentxs.asset import Asset
from pyopentxs.account import Account
from pyopentxs.instrument import transfer

btc_contract_file = "../test-data/sample-contracts/btc.xml"
silver_contract_file = "../test-data/sample-contracts/silver.xml"


class TransferAccounts:
    '''A class to hold issuer/source/target accounts to test transfers.
       Start with 100 balance in the source account'''
    def __init__(self, asset=None):
        self.asset = asset or Asset().issue(Nym().register(),
                                            open(btc_contract_file))

        self.source = Account(self.asset, Nym().register()).create()
        self.target = Account(self.asset, Nym().register()).create()
        self.issuer = self.asset.issuer_account

    def initial_balance(self, balance=100):
        # send 100 from issuer to nym_source_id
        # self.cheque = new_cheque(self.issuer, self.source, balance)
        # transfer(self.cheque, self.issuer, self.source)
        transfer(balance, self.issuer, self.source)
        return self

    def assert_balances(self, issuer, source, target):
        assert (issuer, source, target) == (self.issuer.balance(),
                                            self.source.balance(),
                                            self.target.balance()),\
            "Issuer/source/target balances do not match."


class TradeAccount:
    def __init__(self, nym, asset1, asset2):
        self.nym = nym
        self.account1 = Account(asset1, self.nym)
        self.account2 = Account(asset2, self.nym)

    def create(self):
        self.account1.create()
        self.account2.create()
        return self


class MarketAccounts:
    '''A class to hold market trading accounts'''

    def __init__(self, asset1=None, asset2=None):
        self.asset1 = asset1 or Asset().issue(Nym().register(),
                                              open(btc_contract_file))
        self.asset2 = asset2 or Asset().issue(Nym().register(),
                                              open(silver_contract_file))

        accounts = [
            TradeAccount(Nym().register(), self.asset1, self.asset2).create()
            for _ in range(3)
        ]
        self.alice = accounts[0]
        self.bob = accounts[1]
        self.charlie = accounts[2]

    def initial_balance(self, balance=100):
        # start everyone off with 100 of each asset

        transfer(balance, self.asset1.issuer_account, self.alice.account1)
        transfer(balance, self.asset1.issuer_account, self.bob.account1)
        transfer(balance, self.asset1.issuer_account, self.charlie.account1)

        transfer(balance, self.asset2.issuer_account, self.alice.account2)
        transfer(balance, self.asset2.issuer_account, self.bob.account2)
        transfer(balance, self.asset2.issuer_account, self.charlie.account2)
        return self

    def assert_balances(self, issuer, alice, bob, charlie, issuer2, alice2, bob2, charlie2):
        assert (issuer, alice, bob, charlie, issuer2, alice2, bob2, charlie2) == (
                                            self.asset1.issuer_account.balance(),
                                            self.alice.account1.balance(),
                                            self.bob.account1.balance(),
                                            self.charlie.account1.balance(),
                                            self.asset2.issuer_account.balance(),
                                            self.alice.account2.balance(),
                                            self.bob.account2.balance(),
                                            self.charlie.account2.balance(),
                                            )
#            "balances do not match."
