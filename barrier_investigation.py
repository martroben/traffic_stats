# standard
import json
import os
import re
# external
import numpy as np
import pandas as pd
# local
import api_interface
import data_operations
import general
import graphing


#######################################
# Pull traffic accident data from csv #
#######################################

csv_path = "lo_2011_2023.csv"
with open(csv_path) as csv_file:
    data_raw = pd.read_csv(csv_file, delimiter=";")


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

# Drop columns with missing km marker info
required_info_missing = traffic_accidents["route_km_marker"].isna()
traffic_accidents = traffic_accidents.loc[~required_info_missing, :]

route_number = 15
street_name = "TALLINN - RAPLA - TÜRI"
start_km = 18
end_km = 21

accidents_barrier_area = (
    traffic_accidents
    # Convert , to . in km marker values
    .apply(lambda x: map(re.sub, [","] * len(traffic_accidents), "." * len(traffic_accidents), x) if x.name == "route_km_marker" else x)
    # Convert km marker values to float
    .apply(lambda x: map(float, x) if x.name == "route_km_marker" else x)
    # Filter accidents within the area
    .query(
        f"(route_number == {route_number} | street_name == '{street_name}') & "
        f"route_km_marker >= {start_km} & route_km_marker <= {end_km}"))
