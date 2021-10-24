# Feast Custom Online Store
[![test_custom_online_store](https://github.com/feast-dev/feast-custom-online-store-demo/actions/workflows/test_custom_online_store.yml/badge.svg?branch=main)](https://github.com/feast-dev/feast-custom-online-store-demo/actions/workflows/test_custom_online_store.yml)

### Overview

This repository demonstrates how developers can create their own custom `online store`s for Feast. Custom online stores allow users to use any underlying 
data store to store features for low-latency retrieval, typically needed during model inference.

### Why create a custom online store?

Feast materializes data to online stores for low-latency lookup at model inference time. Typically, key-value stores are used for 
the online stores, however relational databases can be used for this purpose as well.

Feast comes with some online stores built in, e.g, Sqlite, Redis, DynamoDB and Datastore. However, users can develop their
own online stores by creating a class that implements the contract in the [OnlineStore class](https://github.com/feast-dev/feast/blob/master/sdk/python/feast/infra/online_stores/online_store.py#L26).

### What is included in this repository?

* [feast_custom_online_store/](feast_custom_online_store): An example of a custom online store, `MySQLOnlineStore`, which implements `OnlineStore`. This example online store uses MySQL as the backing database.
* [feature_repo/](feature_repo): A simple feature repository that is used to test the custom online store. The repository has been configured to use the `MySQLOnlineStore` as part of it's `feature_store.yaml`
* [test_custom_online_store.py](test_custom_online_store.py): A test case that uses `MySQLOnlineStore` through the `feature_repo/`

### Testing the custom online store in this repository

Run the following commands to test the custom online store ([MySQLOnlineStore](https://github.com/feast-dev/feast-custom-online-store-demo/blob/master/feast_custom_online_store/mysql.py))

```bash
pip install -r requirements.txt
```

```
pytest test_custom_online_store.py
```

It is also possible to run a Feast CLI command, which interacts with the online store. It may be necessary to add the 
`PYTHONPATH` to the path where your online store module is stored.
```
PYTHONPATH=$PYTHONPATH:/$(pwd) feast -c basic_feature_repo apply

```
```
Registered entity driver_id
Registered feature view driver_hourly_stats
Deploying infrastructure for driver_hourly_stats
```

```
$ PYTHONPATH=$PYTHONPATH:/$(pwd) feast -c feature_repo materialize-incremental 2021-08-19T22:29:28
```
```Materializing 1 feature views to 2021-08-19 15:29:28-07:00 into the feast_custom_online_store.mysql.MySQLOnlineStore online store.

driver_hourly_stats from 2020-08-24 05:23:49-07:00 to 2021-08-19 15:29:28-07:00:
100%|████████████████████████████████████████████████████████████████| 5/5 [00:00<00:00, 120.59it/s]
```

### Testing against the Feast test suite

A subset of the Feast test suite, called "universal tests", are designed to test the core behavior of offline and online stores. A custom online store implementation can use the universal tests as follows.

First, note that this repository contains Feast as a submodule. To fetch and populate the directory, run
```
git submodule update --init --recursive
```

Next, confirm that the Feast unit tests run as expected:
```
cd feast
make test
```

The Feast universal tests can be run with the command
```
make test-python-universal
```

If you run it immediately, the tests should fail. The tests are parametrized based on the `FULL_REPO_CONFIGS` variable defined in `sdk/python/tests/integration/feature_repos/repo_configuration.py`. To overwrite these configurations, you can simply create your own file
that contains a `FULL_REPO_CONFIGS`, and point Feast to that file by setting the environment variable `FULL_REPO_CONFIGS_MODULE` to point to that file. In this repo, the file that overwrites `FULL_REPO_CONFIGS` is `feast_custom_online_store/feast_tests.py`, so you would run
```
export FULL_REPO_CONFIGS_MODULE='feast_custom_online_store.feast_tests.py`
make test-python-universal
```
to test the MySQL online store against the Feast universal tests.