# standard
import os
import requests
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
# Get API access token #
########################

base64_api_key = api_interface.get_base64_api_key(
    api_key_id=os.getenv("AVAANDMED_API_KEY_ID"),
    api_key=os.getenv("AVAANDMED_API_KEY"))

access_token_response = api_interface.request_access_token(
    api_url=API_BASE_URL,
    base64_api_key=base64_api_key)

access_token_json = access_token_response.json()
access_token = access_token_json["data"]["accessToken"]


##########################
# Pull data from the API #
##########################

# Traffic accidents dataset id
# (https://avaandmed.eesti.ee/datasets/inimkannatanutega-liiklusonnetuste-andmed)
dataset_id = "d43cbb24-f58f-4928-b7ed-1fcec2ef355b"

# Get general dataset info
dataset_info_response = api_interface.request_dataset_info(
    api_url=API_BASE_URL,
    dataset_id=dataset_id,
    token=access_token)

dataset_files = dataset_info_response.json()["data"]["files"]

# Select the largest available data file (presumably the largest is also the latest)
largest_dataset_file = {"size": 0}
for file in dataset_files:
    if float(file["size"]) > largest_dataset_file["size"]:
        largest_dataset_file = {
            "id": file["id"],
            "name": file["name"],
            "size": float(file["size"])}


# Get actual data


# /datasets/{id}/files/{fileId}

