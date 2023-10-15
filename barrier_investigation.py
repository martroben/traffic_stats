# standard
import json
# external
import pandas as pd
# local
import data_operations


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

# Drop columns with missing info
required_info_missing_gps = traffic_accidents[required_columns_gps].isna().any(axis="columns")
traffic_accidents_gps = traffic_accidents.loc[~required_info_missing_gps, :]

# Convert required columns to float
for col in required_columns_gps:
    traffic_accidents_gps.loc[:, col] = (
        traffic_accidents_gps[col]
        .str.replace(",", ".")
        .astype(float))

# Filter accidents in the area of interest
accidents_within_area_gps = (
    traffic_accidents_gps
    # Filter accidents within the area
    .query(
        f"gps_x >= {gps_x_min} & gps_x <= {gps_x_max} & gps_y >= {gps_y_min} & gps_y <= {gps_y_max}"))


# Filter by route and kilometer marker
route_number = 15
street_name = "TALLINN - RAPLA - TÜRI"
start_km = 18
end_km = 21

required_columns_route = ["route_km_marker"]

# Drop columns with missing info
required_info_missing_route = traffic_accidents[required_columns_route].isna().any(axis="columns")
traffic_accidents_route = traffic_accidents.loc[~required_info_missing_route, :]

# Convert required columns to float
for col in required_columns_route:
    traffic_accidents_route.loc[:, col] = (
        traffic_accidents_route[col]
        .str.replace(",", ".")
        .astype(float))

# Filter accidents in the area of interest
accidents_within_area_route = (
    traffic_accidents_route
    # Filter accidents within the area
    .query(
        f"(route_number == {route_number} | street_name == '{street_name}') & "
        f"route_km_marker >= {start_km} & route_km_marker <= {end_km}"))

# Combine data filtered by different methods
accidents_within_area = (
    pd.concat([accidents_within_area_gps, accidents_within_area_route])
    .drop_duplicates(["case_number", "time"])
    .query("route_number != 11154")
    .query("not (route_number == 11153 & route_km_marker > 0.1)"))


################################
# Have to convert columns route_number and route_km_marker to float for both

print("tere")
