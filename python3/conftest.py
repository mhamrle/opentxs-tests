import pytest
import pyopentxs


def pytest_addoption(parser):
    parser.addoption("--notary-version", type=int, default=0,
                     help="Version of opentxs notary being tested. 0=c++, 1=goatary")


@pytest.yield_fixture(autouse=True, scope="session")
def notary_setup(pytestconfig):
    ver = pytestconfig.getoption("--notary-version")
    if ver == 1:
        # goatary
        from pyopentxs import goatary
        contract_dir = goatary.create_server_contract()
        pyopentxs.create_fresh_wallet()
        goatary.start_notary(contract_dir)
        goatary.add_server_contract(contract_dir)
        yield
        pyopentxs.cleanup()
    else:
        from pyopentxs import notary
        notary.fresh_setup()
        yield
        pyopentxs.cleanup()
