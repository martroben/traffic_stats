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
