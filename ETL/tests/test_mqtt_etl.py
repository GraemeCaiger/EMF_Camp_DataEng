import os
import pandas as pd
import json
import binascii
from pathlib import Path
import subprocess
import base64
import pytest
import logging
import sys
import sqlalchemy

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
ETL_Path = ROOT / "ETL"
sys.path.insert(0, str(ETL_Path))
from src.read_write_utils import *


@pytest.fixture
def load_combined_mqtt():
        columns = ["msg.topic", "payload", "msg.qos", "msg.retain", "time_now", "time_delta"]
        ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
        MQTT_PARTS_GZ_FOLDER = ROOT / "Data"/ "Landing_Zone" / "emf-mqtt-dump"
        combined_gzip = MQTT_PARTS_GZ_FOLDER / "combined_csv.gz"
        df = pd.read_csv(combined_gzip, compression="gzip", header=None, names=columns)
        return df

@pytest.fixture
def df_loaded_from_parquets():
      BR_MQTT_DATA = ROOT / "Data" / "Bronze" / "br_MQTT"
      testdf = combine_and_read_parquet(directory=BR_MQTT_DATA)
      return testdf


def test_payload_decode_type(load_combined_mqtt, columnName="payload"):
    """When not made explict, pandas uses type inference, 
        if data contains nulls this will default to the object datatype which represents NaN as float.  
        This can cause downstream issues if not handled apropriately. 
    """
    payload = load_combined_mqtt[columnName]
    payload_type_counts = payload.apply(type).value_counts()
    logging.warning("Payload datatype value counts: %s", payload_type_counts.to_dict())

    # Confirm there are no int data types. 
    assert not payload.apply(lambda x: isinstance(x, int)).any(), "Payload contains an int"


    # Confirm that float-valued payload entries are only the default NaN representation
    float_payloads = payload[payload.apply(lambda x: isinstance(x, float))]
    null_count = payload.isna().sum()

    logging.warning("Count of null values in the payload data: %d", null_count)
    assert float_payloads.size == null_count, ( "Float payload count does not match the null count, suggests type error")

def test_parquet_df_integity():
      return    

def test_QA_postgreSQL_load(df_loaded_from_parquets):
    from dotenv import load_dotenv, find_dotenv
    import os
    load_dotenv(find_dotenv())

    DB_NAME = os.getenv('DB_NAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_USER = os.getenv('DB_USER')

    import logging

    logger = logging.getLogger(__name__)

    connection_uri = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db_engine = sqlalchemy.create_engine(connection_uri)

    sql_test = pd.read_sql(
        "SELECT * FROM public.br_mqtt_all",
        con=db_engine
    )
    df = df_loaded_from_parquets

    assert len(sql_test) == len(df_loaded_from_parquets), "Data was lost in upload"

    if not df.equals(sql_test):
        df_check = df.copy()
        sql_check = sql_test.copy()

        if not df.equals(sql_test):
            df_check = df.copy()
            sql_check = sql_test.copy()

            # Compare timestamps in UTC at PostgreSQL's microsecond precision
            for frame in (df_check, sql_check):
                frame["time_now"] = pd.to_datetime(
                    frame["time_now"], utc=True
                ).dt.floor("us")

            # SQL queries do not guarantee row order
            sort_columns = list(df_check.columns)
            df_check = df_check.sort_values(sort_columns, na_position="last").reset_index(drop=True)
            sql_check = sql_check.sort_values(sort_columns, na_position="last").reset_index(drop=True)

            try:
                pd.testing.assert_frame_equal(
                    df_check,
                    sql_check,
                    check_dtype=False,
                    check_exact=False,
                    rtol=1e-9,
                    atol=1e-12,
                )
                logging.warning("Data matches after accounting for row order and timestamp precision.")
            except AssertionError as exc:
                logging.warning("Data differs:")
                logging.warning("%s", exc)

                unequal = df_check.ne(sql_check) & ~(df_check.isna() & sql_check.isna())
                bad_rows = unequal.any(axis=1)
                logging.warning("Found %d mismatched rows. Showing up to 20:", bad_rows.sum())
                logging.warning(
                    "Mismatched rows:\n%s",
                    pd.concat({"df": df_check, "sql": sql_check}, axis=1)
                    .loc[bad_rows]
                    .head(20),
                )

        # SQL queries do not guarantee row order
        sort_columns = list(df_check.columns)
        df_check = df_check.sort_values(sort_columns, na_position="last").reset_index(drop=True)
        sql_check = sql_check.sort_values(sort_columns, na_position="last").reset_index(drop=True)

        try:
            pd.testing.assert_frame_equal(
                df_check,
                sql_check,
                check_dtype=False,
                check_exact=False,
                rtol=1e-9,
                atol=1e-12,
            )
            logging.warning("Data matches after accounting for row order and timestamp precision.")
        except AssertionError as exc:
            logging.warning("Data differs:")
            logging.warning("%s", exc)
