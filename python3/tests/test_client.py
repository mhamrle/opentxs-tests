import pyopentxs
import pytest

pytest.mark.usefixtures("setup_ot_config")


def test_create_nym():
    nym_id = pyopentxs.create_nym(1024, "", "")
    nym_ids = pyopentxs.get_nym_ids()

    assert (nym_id in nym_ids), "nym_id=%r" % nym_id


def test_list_servers():
    servers = pyopentxs.get_servers()
    assert servers != []
    assert servers[0][1] == "Transactions.com"  # from localhost.xml server contract

def test_nym_stats():
    nym_id = pyopentxs.create_nym(1024, "", "")
    stats = pyopentxs.get_nym_stats(nym_id)
    assert stats.find(nym_id) >= 0
