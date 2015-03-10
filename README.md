# Integration Tests for OpenTransactions

## Requirements

* Build opentxs with python bindings
* python3
* pip-python3

## Building opentxs with python bindings

See the
[build instructions](https://github.com/Open-Transactions/opentxs),
but use the following extra options for cmake. Change the paths below
to match your system if necessary.

```shell
cmake .. \
-DPYTHON=1 \
-DPYTHON_EXECUTABLE=/usr/bin/python3 \
-DPYTHON_LIBRARY=/usr/lib64/libpython3.so \
-DPYTHON_INCLUDE_DIR=/usr/include/python3.3m
```

## Setting up to run tests locally

Clone this repo:

```shell
cd ~/<your-workspace>
git clone https://github.com/monetas/opentxs-tests
```

I recommend creating a virtualenv:

```shell
virtualenv -p `which python3` ~/.virtualenvs/opentxs
```


Then edit `~/.virtualenvs/opentxs/bin/activate` and add the following
environment variables at the bottom (so that you don't have to keep
setting them each time you use a new shell). Edit the paths to reflect
where you installed opentxs libraries, and where you cloned this
repository.

```shell
export PYTHONPATH=/usr/local/lib64/python3.3/site-packages/:~/workspace/opentxs-tests/python3
export LD_LIBRARY_PATH=/usr/local/lib64
```

Now activate the virtualenv:

`. ~/.virtualenvs/opentxs/bin/activate`

Install the required python libs:

```shell
cd ~/workspace/opentxs-tests/python3
pip install -Ur requirements.txt
```

## Running the tests

**Note:** these tests will destroy any running `opentxs-notary` or
  `notary` processes, and all the data in `~/.ot`. If you need any of
  your existing data, back it up first.

```shell
cd ~/workspace/opentxs-tests/python3
./runtests.py
```

## Running against the new (Golang) notary

```shell
cd ~/workspace/opentxs-tests/python3
# selects the new notary version and only tests that currently work with it
./runtests.py --notary-version 1 -m goatary
```

## Logs

The `opentxs-notary` stdout will be redirected to
`opentxs-notary.log`. `notary` stdout will go to
`opentxs-goatary.log`.



