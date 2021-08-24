import os
import re
from datetime import datetime

from feast import FeatureStore

from feature_repo.repo import driver, driver_hourly_stats_view


def test_end_to_end():
    fs = FeatureStore("feature_repo/")

    # apply repository
    fs.apply([driver, driver_hourly_stats_view])

    # load data into online store
    fs.materialize_incremental(end_date=datetime.now())

    # Read features from online store
    feature_vector = fs.get_online_features(
        features=["driver_hourly_stats:conv_rate"], entity_rows=[{"driver_id": 1001}]
    ).to_dict()
    conv_rate = feature_vector["conv_rate"][0]
    assert conv_rate > 0

    # tear down feature store
    fs.teardown()


def test_cli():
    os.system(
        "PYTHONPATH=$PYTHONPATH:/$(pwd) feast -c feature_repo apply"
    )
    os.system(
        "PYTHONPATH=$PYTHONPATH:/$(pwd) feast -c feature_repo materialize-incremental 2021-08-19T22:29:28 > output"
    )
    with open("output", "r") as f:
        output = f.read()

    try:
        if "feast_custom_online_store.mysql.MySQLOnlineStore" not in output:
            raise Exception(
                f'Failed to successfully use online store from CLI. Output:\n\n {output}'
            )
    finally:
        os.system(
            "PYTHONPATH=$PYTHONPATH:/$(pwd) feast -c feature_repo teardown"
        )
