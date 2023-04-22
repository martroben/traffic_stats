# standard
import os
import io
import json

import pandas
# external
import pandas as pd
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# local
import api_interface
import data_operations
import general


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

traffic_accidents = traffic_accidents.sort_values(by="time")


#######################
# Naive accident data #
#######################

harm_by_day = traffic_accidents\
    .assign(
        day=lambda df: df["time"].map(lambda x: x.floor("d")),
        n_harmed_motor_vehicle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_motor_vehicle_driver"],
        n_harmed_bicycle=lambda df: (df["n_diseased"] + df["n_injured"]) * df["involves_cyclist"])\
    .groupby("day", as_index=False)[["day", "n_harmed_motor_vehicle", "n_harmed_bicycle"]]\
    .agg({
        "day": "first",
        "n_harmed_motor_vehicle": "sum",
        "n_harmed_bicycle": "sum"})\
    .assign(
        n_harmed_motor_vehicle_cumulative=lambda df: df["n_harmed_motor_vehicle"].cumsum(),
        n_harmed_bicycle_cumulative=lambda df: df["n_harmed_bicycle"].cumsum())


############# fix column names

figure = make_subplots(
    rows=3, cols=1, row_heights=[40, 2, 2],
    shared_xaxes=True,
    vertical_spacing=0.05)

motor_vehicle_total_graph = go.Bar(
    name="people hurt in motor vehicle accidents",
    x=harm_by_day["day"],
    y=harm_by_day["harmed_vehicle"],
    marker={"color": "#526a83", "line_color": "#526a83"})

bicycle_total_graph = go.Bar(
    name="people hurt in bicycle accidents",
    x=harm_by_day["day"],
    y=harm_by_day["harmed_bicycle"],
    marker={"color": "#a06177", "line_color": "#a06177"})

motor_vehicle_cumulative_graph = go.Scatter(
    x=harm_by_day["day"],
    y=harm_by_day["harmed_vehicle_cumulative"],
    marker={"color": "#526a83", "line_color": "#526a83"},
    fill="tozeroy",
    showlegend=False)

bicycle_cumulative_graph = go.Scatter(
    x=harm_by_day["day"],
    y=harm_by_day["harmed_bicycle_cumulative"],
    marker={"color": "#a06177", "line_color": "#a06177"},
    fill="tozeroy",
    showlegend=False)


figure.add_trace(motor_vehicle_cumulative_graph, row=1, col=1)
figure.add_trace(bicycle_cumulative_graph, row=1, col=1)
figure.add_trace(motor_vehicle_total_graph, row=2, col=1)
figure.add_trace(bicycle_total_graph, row=3, col=1)
figure.update_layout(
    bargap=0,
    # autosize=False,
    # width=1000,
    # height=500,
    plot_bgcolor="white",
    yaxis1_range=[0, 2e+4],
    yaxis2_range=[0, 30],
    yaxis3_range=[0, 30],
    yaxis1_tickfont_size=10,
    yaxis2_tickfont_size=8,
    yaxis3_tickfont_size=8)

figure.update_yaxes(gridcolor="lightgrey")
figure.show()


# People harmed by bicycle:
#



columns_of_interest = [
    "Toimumisaeg",
    "Isikuid",
    "Hukkunuid",
    "Vigastatuid",
    "Sõidukeid",
    "Kergliikurijuhi osalusel",
    "Jalakäija osalusel",
    "Kaassõitja osalusel",
    "Maastikusõiduki juhi osalusel",
    "Bussijuhi osalusel",
    "Veoautojuhi osalusel",
    "Ühissõidukijuhi osalusel",
    "Sõiduautojuhi osalusel",
    "Mootorratturi osalusel",
    "Mopeedijuhi osalusel",
    "Jalgratturi osalusel",
    "Mootorsõidukijuhi osalusel",
    "Lubatud sõidukiirus (PPA)"]

data = data_all.loc[:, columns_of_interest]





data_all["Lubatud sõidukiirus (PPA)"].unique()
data_all.query("`Lubatud sõidukiirus (PPA)` == 901")
no_speed_limit = data_all.query("`Lubatud sõidukiirus (PPA)`.isna()", engine="python")