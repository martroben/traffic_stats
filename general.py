# standard
import json
import os
import re


def parse_input_file_line(line: str, parse_value: bool = True) -> (str, (dict | list | str)):
    """
    Parse line from input file.
    Returns None, if it's a comment line (starting with #).
    Tries to parse value: dict if value is json, list if it's values separated by commas, string otherwise.
    :param line: Line from readlines
    :param parse_value: True/False whether values should be automatically parsed
    :return: None if comment line,
    else variable name + dict if json, list if comma separated values, string if single value.
    """
    if re.search(r"^\s*#", line) or not re.search(r"=", line):
        return
    else:
        name = line.split("=")[0].strip()
        value = line.split("=")[1].strip()
    if parse_value:
        try:
            value = json.loads(value)
        except json.decoder.JSONDecodeError:
            value = [list_item.strip() for list_item in value.split(",")]
            value = value[0] if len(value) == 1 else value      # return str if only a single value, else list
    return name, value


def parse_input_file(path: str, parse_values: bool = True,
                     set_environmental_variables: bool = False) -> (None, dict):
    """
    Parse values from .env or .ini file.
    Optionally set values straight to environment without returning.
    :param path: Path to file that is to be imported.
    :param parse_values: True/False - attempt to parse parameter value to list / dict.
    :param set_environmental_variables: True/False - set imported variables directly to environment without returning.
    :return: A dict on imported values or None, if set straight to environmental variables.
    """
    parsed_values = dict()
    with open(path) as input_file:
        for line in input_file.readlines():
            parsed_line = parse_input_file_line(line, parse_values)
            if parsed_line is not None:
                parsed_values[parsed_line[0]] = parsed_line[1]
    if set_environmental_variables:
        # Make sure values are strings (env variables only accept strings)
        env_variables = {key: str(value) for key, value in parsed_values.items()}
        os.environ.update(**env_variables)
    return parsed_values
