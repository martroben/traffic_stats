# standard
import datetime
import json
# external
import pandas as pd
# local
import data_operations


#######################################
# Pull traffic accident data from csv #
#######################################

# File from https://avaandmed.eesti.ee/datasets/inimkannatanutega-liiklusonnetuste-andmed
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

# Convert appropriate columns to float
float_columns = ["route_km_marker", "gps_x", "gps_y"]
missing_value_placeholder = -1.0

for col in float_columns:
    missing_values = traffic_accidents[col].isna()
    traffic_accidents.loc[missing_values, col] = missing_value_placeholder

    traffic_accidents.loc[:, col] = (
        traffic_accidents[col]
        .str.replace(",", ".")
        .astype(float))


##############################
# Filter by area of interest #
##############################

# Use filtering by GPS coordinates and also by route name and kilometer marker

# Filter by gps coordinates
gps_x_min = 6565550
gps_x_max = 6567850
gps_y_min = 542660
gps_y_max = 544382

required_columns_gps = ["gps_x", "gps_y"]
traffic_accidents_gps = traffic_accidents

# Filter accidents in the area of interest
accidents_within_area_gps = (
    traffic_accidents_gps
    .query(
        f"gps_x >= {gps_x_min} & gps_x <= {gps_x_max} & "
        f"gps_y >= {gps_y_min} & gps_y <= {gps_y_max}"))

# Additional filtering to remove false matched within the coordinates
accidents_within_area_gps = (
    accidents_within_area_gps
    .query(
        "route_number != 11154 & "
        "(route_number != 11153 | route_km_marker < 0.1)"))


# Filter by route and kilometer marker
route_number = 15
street_name = "TALLINN - RAPLA - TÜRI"
start_km = 18
end_km = 21

required_columns_route = ["route_km_marker"]
traffic_accidents_route = traffic_accidents

# Filter accidents in the area of interest
accidents_within_area_route = (
    traffic_accidents_route
    .query(
        f"(route_number == {route_number} | street_name == '{street_name}') & "
        f"route_km_marker >= {start_km} & route_km_marker <= {end_km}"))

# Combine data filtered by different methods
accidents_within_area = (
    pd.concat([accidents_within_area_gps, accidents_within_area_route])
    .drop_duplicates(["case_number", "time"]))


#####################
# Filter final data #
#####################

export_columns = [
    "time",
    "barrier_built",
    "route_number",
    "route_km_marker",
    "n_participants",
    "n_vehicles",
    "n_diseased",
    "n_injured",
    "accident_classification_2"]

# Assuming the barrier was build during summer 2019
barrier_build_ymd = "2019/06/01"
accidents_within_area.insert(1, "barrier_built", accidents_within_area["time"] > datetime.datetime.strptime(barrier_build_ymd, "%Y/%m/%d"))

export_data = (
    accidents_within_area
    .loc[:, export_columns]
    .sort_values("time"))
