from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine
import pandas as pd


def split_to_parquet(df: pd.DataFrame, directory: Path, target_size_mb: int = 50):
    """Save dataframe to parquet splitting into parts within a specified directory"""
    
    # Create missing parent directories and don't fail if the directory already exists.
    directory.mkdir(parents=True, exist_ok=True)

    # Split into parts managable for github
    table = pa.Table.from_pandas(df, preserve_index=False)
    rows_per_file = max(1, int(len(df) * target_size_mb * 1024**2 / table.nbytes))
    for i, start in enumerate(range(0, len(df), rows_per_file)):
        pq.write_table(
            table.slice(start, rows_per_file),
            directory / f"part_{i:04d}.parquet",
            compression="snappy"
        )


def combine_and_read_parquet(directory: Path) -> pd.DataFrame:
    """Recombine seperated parquet files into dataframe"""
    files = sorted(directory.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files found in {directory}")
    return pd.concat(
        [pd.read_parquet(file) for file in files],
        ignore_index=True
    )



def load_to_postgres(
    df: pd.DataFrame,
    connection_string: str,
    table_name: str,
    schema: str = "public",
    chunksize: int = 5000
):
    engine = create_engine(connection_string)

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists="replace",
            index=True,
            chunksize=chunksize,
            method="multi"
        )
    finally:
        engine.dispose()













# Chat GPT questions indicated this would likely be a better implementation for fast load using coping as opposed to decomposeing it into many insert statments. 
# This approach however I belive should only be included once i have sured up understanding better of the specifics of how/if its works. 
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
import csv
def load_to_postgres_GPT_fast(
    source,
    connection_string: str,
    table_name: str,
    schema: str = "public",
    chunksize: int = 5000
):
    engine = create_engine(connection_string)

    try:
        # Option 1: Source is Directory containing Parquet files -> COPY   (Signficantly faster for large files)
        if isinstance(source, (str, Path)) and Path(source).is_dir():

            with engine.begin() as conn:
                raw_conn = conn.connection.driver_connection

                with raw_conn.cursor() as cursor:
                    for file in sorted(Path(source).glob("*.parquet")):
                        df = pd.read_parquet(file)

                        buffer = df.to_csv(
                            index=False,
                            header=False,
                            na_rep="\\N",
                            quoting=csv.QUOTE_MINIMAL
                        )

                        from io import StringIO
                        cursor.copy_expert(
                            f'COPY "{schema}"."{table_name}" FROM STDIN WITH (FORMAT CSV, NULL \'\\N\')',
                            StringIO(buffer)
                        )

        # Option 2: source is DataFrame -> standard INSERT
        elif isinstance(source, pd.DataFrame):

            source.to_sql(
                name=table_name,
                con=engine,
                schema=schema,
                if_exists="append",
                index=False,
                chunksize=chunksize,
                method="multi"
            )

        else:
            raise TypeError("Source must be a pandas DataFrame or Parquet directory")

    finally:
        engine.dispose()
