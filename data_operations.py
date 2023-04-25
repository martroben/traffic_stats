import logging
import pandas


def rename_with_check(data_frame: pandas.DataFrame, translations: dict) -> pandas.DataFrame:
    untranslated_columns = [column for column in data_frame.columns if column not in translations]
    if untranslated_columns:
        untranslated_columns_string = ", ".join(untranslated_columns)
        logging.warning(f"No translations found for the following data frame columns: {untranslated_columns_string}")

    unmatched_translations = [column for column in translations.keys() if column not in data_frame.columns]
    if unmatched_translations:
        unmatched_translations_string = ", ".join(unmatched_translations)
        logging.warning(f"No matching columns found for the following translations: {unmatched_translations_string}")

    return data_frame.rename(columns=translations)


def aggregate_harm_by_day(df: pandas.DataFrame):
    # input column names
    time = "time"
    day = "day"
    # keep columns with indicator in column name
    keep_indicator = "n_harmed"
    keep_columns = [col_name for col_name in df.columns if keep_indicator in col_name]
    aggregate_kwargs = {f"{day}": "first", **{col_name: "sum" for col_name in keep_columns}}

    aggregated_df = (
        df
        .assign(
            # Round time to full days
            day=lambda table: table[time].map(lambda x: x.floor("d")))
        # Aggregate by day
        .groupby(day, as_index=False)[[day] + keep_columns]
        .agg(aggregate_kwargs)
        )
    return aggregated_df


def join_by_day(df_bicycle: pandas.DataFrame, df_motor_vehicle: pandas.DataFrame):
    # input column names
    n_harmed_motor_vehicle = "n_harmed_motor_vehicle"
    n_harmed_bicycle = "n_harmed_bicycle"
    day = "day"

    df_joined = (
        df_motor_vehicle
        .rename(columns=dict(n_harmed=n_harmed_motor_vehicle))
        # Join data frames by day
        .join(
            other=df_bicycle
            .rename(columns=dict(n_harmed=n_harmed_bicycle))
            .set_index(day),
            on=day,
            how="outer")
        .fillna(0)
        .sort_values(by=day)
    )
    return df_joined


def add_cumulative(df: pandas.DataFrame):
    # input column names
    n_harmed_motor_vehicle = "n_harmed_motor_vehicle"
    n_harmed_bicycle = "n_harmed_bicycle"

    assign_kwargs = {
        f"{n_harmed_motor_vehicle}_cumulative": lambda table: table[n_harmed_motor_vehicle].cumsum(),
        f"{n_harmed_bicycle}_cumulative": lambda table: table[n_harmed_bicycle].cumsum()
    }
    df_cumulative = df.assign(**assign_kwargs)
    return df_cumulative
