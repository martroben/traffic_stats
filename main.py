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


######################################
# Pull traffic accident from the API #
######################################

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

# Set boolean values for appropriate columns
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

####################### check involves_motor_vehicle, but no motor vehicle involved

#######################
# Naive accident data #
#######################

naive_data_by_day = (
    traffic_accidents
    .assign(
        day=lambda df: df["time"].map(lambda x: x.floor("d")),
        n_harmed_motor_vehicle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_motor_vehicle_driver"],
        n_harmed_bicycle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_cyclist"])
    .groupby("day", as_index=False)[["day", "n_harmed_motor_vehicle", "n_harmed_bicycle"]]
    .agg({
        "day": "first",
        "n_harmed_motor_vehicle": "sum",
        "n_harmed_bicycle": "sum"})
    .assign(
        n_harmed_motor_vehicle_cumulative=lambda df: df["n_harmed_motor_vehicle"].cumsum(),
        n_harmed_bicycle_cumulative=lambda df: df["n_harmed_bicycle"].cumsum()))

motor_vehicle_bicycle_total_ratio = (max(naive_data_by_day["n_harmed_motor_vehicle_cumulative"]) /
                                     max(naive_data_by_day["n_harmed_bicycle_cumulative"]))


#############################
# Naive accident data graph #
#############################

graphing.daily_results(
    data=naive_data_by_day,
    motor_vehicle_title="total deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="total deaths + injuries in <b>bicycle</b> accidents")


################
# Victims data #
################

victims_bicycle_by_day = (
    traffic_accidents
    .assign(
        day=lambda df: df["time"].map(lambda x: x.floor("d")),
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    .query("(involves_cyclist & not involves_motor_vehicle_driver) & "
           "(n_harmed > 1 | involves_personal_light_electric_vehicle_driver | involves_pedestrian)")
    .assign(n_harmed=lambda df: np.where(df["n_harmed"] > 1, df["n_harmed"] - 1, df["n_harmed"]))
    .groupby("day", as_index=False)[["day", "n_harmed"]]
    .agg(dict(
        day="first",
        n_harmed="sum")))

victims_motor_vehicle_by_day = (
    traffic_accidents
    .assign(
        day=lambda df: df["time"].map(lambda x: x.floor("d")),
        n_harmed=lambda df: (df["n_diseased"] + df["n_injured"]))
    .query("involves_motor_vehicle_driver & "
           "(n_harmed > 1 | involves_personal_light_electric_vehicle_driver | involves_pedestrian | "
           "involves_passenger | involves_motorcycle_driver | involves_moped_driver | involves_cyclist)")
    .assign(n_harmed=lambda df: np.where(df["n_harmed"] > 1, df["n_harmed"] - 1, df["n_harmed"]))
    .groupby("day", as_index=False)[["day", "n_harmed"]]
    .agg(dict(
        day="first",
        n_harmed="sum")))

victims_by_day = (
    victims_motor_vehicle_by_day
    .rename(columns=dict(n_harmed="n_harmed_motor_vehicle"))
    .join(
        other=victims_bicycle_by_day
        .rename(columns=dict(n_harmed="n_harmed_bicycle"))
        .set_index("day"),
        on="day",
        how="outer")
    .fillna(0)
    .sort_values(by="day")
    .assign(
        n_harmed_motor_vehicle_cumulative=lambda df: df["n_harmed_motor_vehicle"].cumsum(),
        n_harmed_bicycle_cumulative=lambda df: df["n_harmed_bicycle"].cumsum()))

motor_vehicle_bicycle_victim_ratio = (max(victims_by_day["n_harmed_motor_vehicle_cumulative"]) /
                                      max(victims_by_day["n_harmed_bicycle_cumulative"]))


######################
# Victims data graph #
######################

graphing.daily_results(
    data=victims_by_day,
    motor_vehicle_title="victim deaths + injuries in <b>motor vehicle</b> accidents",
    bicycle_title="victim deaths + injuries in <b>bicycle</b> accidents")






data_all["Lubatud sõidukiirus (PPA)"].unique()
data_all.query("`Lubatud sõidukiirus (PPA)` == 901")
no_speed_limit = data_all.query("`Lubatud sõidukiirus (PPA)`.isna()", engine="python")