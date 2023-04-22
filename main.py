# standard
import os
import io
# external
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# local
import api_interface
import general


####################
# Global variables #
####################

API_BASE_URL = "https://avaandmed.eesti.ee/api"


#############################################
# Import secrets to environmental variables #
#############################################

env_file_path = ".env"
general.parse_input_file(
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
# Pycharm/Pandas type hint conflict
data_raw = pd.read_csv(io.StringIO(file_response.text))


##############
# Clean data #
##############

# Convert dates to datetime
traffic_accidents = data_raw
traffic_accidents.loc[:, "Toimumisaeg"] = pd.to_datetime(
    arg=traffic_accidents["Toimumisaeg"],
    format="mixed",
    dayfirst=True)

traffic_accidents = traffic_accidents.sort_values(by="Toimumisaeg")


#######################
# Naive accident data #
#######################

##################### Find way to end on same day

motor_vehicle_accidents = traffic_accidents\
    .query("`Mootorsõidukijuhi osalusel` == 1")\
    .assign(
        day=lambda df: df["Toimumisaeg"].map(lambda x: x.floor("d")),
        total_harmed=lambda df: df["Hukkunuid"] + df["Vigastatuid"])\
    .groupby("day", as_index=False)[["day", "total_harmed"]]\
    .agg({"day": "first", "total_harmed": "sum"})\
    .assign(cumulative_harmed = lambda df: df["total_harmed"].cumsum())

bicycle_accidents = traffic_accidents\
    .query("`Jalgratturi osalusel` == 1")\
    .assign(
        day=lambda df: df["Toimumisaeg"].map(lambda x: x.floor("d")),
        total_harmed=lambda df: df["Hukkunuid"] + df["Vigastatuid"])\
    .groupby("day", as_index=False)[["day", "total_harmed"]]\
    .agg({"day": "first", "total_harmed": "sum"})\
    .assign(cumulative_harmed = lambda df: df["total_harmed"].cumsum())

figure = make_subplots(
    rows=3, cols=1, row_heights=[40, 2, 2],
    shared_xaxes=True,
    vertical_spacing=0.05)

motor_vehicle_total_graph = go.Bar(
    name="people hurt in motor vehicle accidents",
    x=motor_vehicle_accidents["day"],
    y=motor_vehicle_accidents["total_harmed"],
    marker={"color": "#526a83", "line_color": "#526a83"})

bicycle_total_graph = go.Bar(
    name="people hurt in bicycle accidents",
    x=bicycle_accidents["day"],
    y=bicycle_accidents["total_harmed"],
    marker={"color": "#a06177", "line_color": "#a06177"})

motor_vehicle_cumulative_graph = go.Scatter(
    x=motor_vehicle_accidents["day"],
    y=motor_vehicle_accidents["cumulative_harmed"],
    fill="tozeroy")

bicycle_cumulative_graph = go.Scatter(
    x=bicycle_accidents["day"],
    y=bicycle_accidents["cumulative_harmed"],
    fill="tozeroy")


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
