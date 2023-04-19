# standard
import base64
import requests


def get_base64_api_key(api_key_id: str, api_key: str) -> bytes:
    """
    Converts API key and API key ID to the format required for API authorization.
    base64(api_key_id:api_key)
    :param api_key_id: API key ID from avaandmed.eesti.ee portal
    :param api_key: API key from avaandmed.eesti.ee portal
    :return: base64 (bytes) object with API key information
    """
    api_key_string = api_key_id + ":" + api_key
    api_key_bytes = api_key_string.encode("ascii")
    api_key_base64 = base64.b64encode(api_key_bytes)
    return api_key_base64


def request_access_token(api_url: str, base64_api_key: bytes) -> requests.Response:
    """
    Perform HTTP request for access token.
    :param api_url: API url
    :param base64_api_key: Base64 encoded combination of API key ID and API key
    :return: Request response object
    """
    authorization_endpoint = "/auth/key-login"
    endpoint_url = api_url.strip("/") + authorization_endpoint
    headers = {"X-API-KEY": base64_api_key}
    parameters = {}
    body = {}

    response = requests.post(
        headers=headers,
        url=endpoint_url,
        data=body,
        params=parameters)

    return response



