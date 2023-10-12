# standard
import os
import io
import json
# external
import numpy as np
import pandas as pd
# local
import api_interface
import data_operations
import general
import graphing


####################
# Global variables #
####################

API_BASE_URL = "https://avaandmed.eesti.ee/api"


#############################################
# Import secrets to environmental variables #
#############################################

env_file_path = ".env"
_ = general.parse_input_file(
    path=env_file_path,
    set_environmental_variables=True)


########################
# Authorize API access #
########################

base64_api_key = api_interface.get_base64_api_key(
    api_key_id=os.getenv("AVAANDMED_API_KEY_ID"),
    api_key=os.getenv("AVAANDMED_API_KEY"))

access_token_response = api_interface.request_access_token(
    api_url=API_BASE_URL,
    base64_api_key=base64_api_key)

access_token_json = access_token_response.json()
access_token = access_token_json["data"]["accessToken"]

# Setup API interface object
api_session = api_interface.ApiSession(access_token)
api = api_interface.ApiInterface(
    api_url=API_BASE_URL,
    session=api_session)


###########################################
# Pull traffic accident data from the API #
###########################################

# Traffic accidents dataset id
# (https://avaandmed.eesti.ee/datasets/inimkannatanutega-liiklusonnetuste-andmed)
dataset_id = "d43cbb24-f58f-4928-b7ed-1fcec2ef355b"

# Get general dataset info
dataset_info_response = api.get_dataset_info(dataset_id=dataset_id)

# Select the largest available data file
# (Presumably the largest is also the latest)
# (Only processed files can be downloaded via API)
dataset_files = dataset_info_response.json()["data"]["files"]
dataset_files_processed = [file for file in dataset_files
                           if file["processingStatus"] == "completed"]

largest_file = {"size": 0}
for file in dataset_files_processed:
    if float(file["size"]) > largest_file["size"]:
        largest_file = {
            "id": file["id"],
            "name": file["name"],
            "size": float(file["size"])}

# Get actual data
file_response = api.get_file(dataset_id=dataset_id, file_id=str(largest_file["id"]))
# noinspection PyTypeChecker
# (Pycharm/Pandas type hint conflict)
data_raw = pd.read_csv(io.StringIO(file_response.text))


##############
# Clean data #
##############

# Translate column names
column_name_translations_path = "./column_name_translations.json"
with open(column_name_translations_path, encoding="utf-8") as translations_file:
    column_name_translations = json.loads(translations_file.read())

column_name_translations_ee_en = dict()
for column_name in column_name_translations:
    column_name_translations_ee_en[column_name["ee"]] = column_name["en"]

traffic_accidents = data_operations.rename_with_check(data_raw, column_name_translations_ee_en)

# Convert dates to datetime
traffic_accidents.loc[:, "time"] = pd.to_datetime(
    arg=traffic_accidents["time"],
    format="mixed",
    dayfirst=True)

# Drop rows with missing info
required_info_columns = [
    "involves_personal_light_electric_vehicle_driver",
    "involves_pedestrian",
    "involves_passenger",
    "involves_bus_driver",
    "involves_truck_driver",
    "involves_passenger_car_driver",
    "involves_cyclist",
    "involves_motor_vehicle_driver"]

required_info_missing = traffic_accidents[required_info_columns].isna().any(axis="columns")
traffic_accidents = traffic_accidents.loc[~required_info_missing, :]
n_rows_with_missing_info = sum(required_info_missing)

# Convert appropriate columns to boolean
traffic_accidents.loc[:, "within_built_up_area"] = (
    traffic_accidents["within_built_up_area"]
    .transform(lambda x: x.lower() == "jah"))
traffic_accidents = traffic_accidents.astype({"within_built_up_area": bool})

boolean_columns = [
    "within_built_up_area",
    "involves_personal_light_electric_vehicle_driver",
    "involves_pedestrian",
    "involves_passenger",
    "involves_off_road_driver",
    "involves_old_driver",
    "involves_bus_driver",
    "involves_truck_driver",
    "involves_public_transport_driver",
    "involves_passenger_car_driver",
    "involves_motorcycle_driver",
    "involves_moped_driver",
    "involves_cyclist",
    "involves_underage_person",
    "involves_person_not_using_safety_equipment",
    "involves_provisional_driving_license_driver",
    "involves_motor_vehicle_driver"]

traffic_accidents = (
    traffic_accidents
    .apply(lambda x: map(bool, x) if x.name in boolean_columns else x))

# Sort by time
traffic_accidents = traffic_accidents.sort_values(by="time")


#######################
# Naive accident data #
#######################

naive_data = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed_motor_vehicle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_motor_vehicle_driver"],
        n_harmed_bicycle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_cyclist"])
    )

naive_data_by_day = data_operations.aggregate_harm_by_day(naive_data)
naive = data_operations.add_cumulative(naive_data_by_day)

motor_vehicle_bicycle_total_ratio = (max(naive["n_harmed_motor_vehicle_cumulative"]) /
                                     max(naive["n_harmed_bicycle_cumulative"]))


#############################
# Naive accident data graph #
#############################

graphing.daily_results(
    data=naive,
    motor_vehicle_title="total deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="total deaths + injuries in <b>bicycle</b> accidents")


################
# Victims data #
################

victims_bicycle = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("(involves_cyclist & not involves_motor_vehicle_driver) & "
           "(n_harmed > 1 | involves_personal_light_electric_vehicle_driver | involves_pedestrian)")
    # Reduce harmed persons by 1 where causing driver is likely among them to get victims
    .assign(n_harmed=lambda df: np.where(df["n_harmed"] > 1, df["n_harmed"] - 1, df["n_harmed"]))
    )

victims_motor_vehicle = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("involves_motor_vehicle_driver & "
           "(n_harmed > 1 | involves_personal_light_electric_vehicle_driver | involves_pedestrian | "
           "involves_passenger | involves_motorcycle_driver | involves_moped_driver | involves_cyclist)")
    # Reduce harmed persons by 1 where causing driver is likely among them to get victims
    .assign(n_harmed=lambda df: np.where(df["n_harmed"] > 1, df["n_harmed"] - 1, df["n_harmed"]))
    )

victims_bicycle_by_day = data_operations.aggregate_harm_by_day(victims_bicycle)
victims_motor_vehicle_by_day = data_operations.aggregate_harm_by_day(victims_motor_vehicle)

victims_joined = data_operations.join_by_day(
    df_bicycle=victims_bicycle_by_day,
    df_motor_vehicle=victims_motor_vehicle_by_day)

victims = data_operations.add_cumulative(victims_joined)

motor_vehicle_bicycle_victim_ratio = (max(victims["n_harmed_motor_vehicle_cumulative"]) /
                                      max(victims["n_harmed_bicycle_cumulative"]))


######################
# Victims data graph #
######################

graphing.daily_results(
    data=victims,
    motor_vehicle_title="victim deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="victim deaths + injuries in <b>bicycle</b> accidents")


######################################################
# Accidents where bicycle use if a valid alternative #
######################################################

# Hypothesis 1: it's always the cyclist's fault
harmed_bicycle_h1 = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("involves_cyclist")
    )

harmed_motor_vehicle_h1 = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("involves_motor_vehicle_driver & "
           "not involves_truck_driver & "
           "not involves_bus_driver & "
           "not involves_cyclist &"
           "(within_built_up_area | speed_limit <= 50)")
    )

injured_per_accident_h1_motor_vehicle = sum(harmed_motor_vehicle_h1["n_injured"]) / len(harmed_motor_vehicle_h1)
injured_per_accident_h1_bicycle = sum(harmed_bicycle_h1["n_injured"]) / len(harmed_bicycle_h1)
diseased_per_accident_h1_motor_vehicle = sum(harmed_motor_vehicle_h1["n_diseased"]) / len(harmed_motor_vehicle_h1)
diseased_per_accident_h1_bicycle = sum(harmed_bicycle_h1["n_diseased"]) / len(harmed_bicycle_h1)

harmed_bicycle_h1_by_day = data_operations.aggregate_harm_by_day(harmed_bicycle_h1)
harmed_motor_vehicle_h1_by_day = data_operations.aggregate_harm_by_day(harmed_motor_vehicle_h1)

harmed_h1_joined = data_operations.join_by_day(
    df_bicycle=harmed_bicycle_h1_by_day,
    df_motor_vehicle=harmed_motor_vehicle_h1_by_day)

harmed_h1 = data_operations.add_cumulative(harmed_h1_joined)

# Hypothesis 2: it's always the motor vehicle driver's fault
harmed_bicycle_h2 = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("involves_cyclist & "
           "not involves_motor_vehicle_driver")
    )

harmed_motor_vehicle_h2 = (
    traffic_accidents
    .assign(
        # Summarize harm statistics
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    # Filter relevant accidents
    .query("involves_motor_vehicle_driver & "
           "not involves_truck_driver & "
           "not involves_bus_driver & "
           "(within_built_up_area | speed_limit <= 50)")
    )

injured_per_accident_h2_motor_vehicle = sum(harmed_motor_vehicle_h2["n_injured"]) / len(harmed_motor_vehicle_h2)
injured_per_accident_h2_bicycle = sum(harmed_bicycle_h2["n_injured"]) / len(harmed_bicycle_h2)
diseased_per_accident_h2_motor_vehicle = sum(harmed_motor_vehicle_h2["n_diseased"]) / len(harmed_motor_vehicle_h2)
diseased_per_accident_h2_bicycle = sum(harmed_bicycle_h2["n_diseased"]) / len(harmed_bicycle_h2)

harmed_bicycle_h2_by_day = data_operations.aggregate_harm_by_day(harmed_bicycle_h2)
harmed_motor_vehicle_h2_by_day = data_operations.aggregate_harm_by_day(harmed_motor_vehicle_h2)

harmed_h2_joined = data_operations.join_by_day(
    df_bicycle=harmed_bicycle_h2_by_day,
    df_motor_vehicle=harmed_motor_vehicle_h2_by_day)

harmed_h2 = data_operations.add_cumulative(harmed_h2_joined)


############################################################
# Graph accidents where bicycle use if a valid alternative #
############################################################

graphing.daily_results(
    data=harmed_h1,
    motor_vehicle_title="deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="deaths + injuries in <b>bicycle</b> accidents")

graphing.daily_results(
    data=harmed_h2,
    motor_vehicle_title="deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="deaths + injuries in <b>bicycle</b> accidents")
