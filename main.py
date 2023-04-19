# standard
import os
from io import StringIO
# external
import pandas as pd
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
data = pd.read_csv(StringIO(file_response.text))


