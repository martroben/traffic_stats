# standard
import os
# local
import api_interface
import general

# Global variables
API_BASE_URL = "https://avaandmed.eesti.ee/api"

# Import secrets to environmental variables
env_file_path = ".env"
general.parse_input_file(path=env_file_path, set_environmental_variables=True)


########################
# Get API access token #
########################

authorization_endpoint = "/auth/key-login"

base64_api_key = api_interface.get_base64_api_key(
    api_key_id=os.getenv("AVAANDMED_API_KEY_ID"),
    api_key=os.getenv("AVAANDMED_API_KEY"))

access_token = api_interface.get_access_token(
    endpoint_url=API_BASE_URL + authorization_endpoint,
    base64_api_key=base64_api_key)
