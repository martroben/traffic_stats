# standard
import base64
# external
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
    Make an HTTP request for access token.
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


# def request_dataset_info(api_url: str, dataset_id: str, token: str) -> requests.Response:
#     """
#     Make an HTTP request to get general info of a dataset by dataset id
#     :param api_url: API url
#     :param dataset_id: Dataset id (from dataset page in avaandmed.eesti.ee)
#     :param token: API token from authorization endpoint
#     :return: Request response object
#     """
#
#     dataset_info_endpoint = "/datasets/" + dataset_id
#     headers = {
#         "Authorization": "bearer" + token}
#
#     dataset_info_response = requests.get(
#         url=api_url.strip("/") + dataset_info_endpoint,
#         headers=headers)
#
#     return dataset_info_response


class ApiSession(requests.Session):
    """A session object that includes the Api authorization header."""
    def __init__(self, token: str):
        super().__init__()
        headers = {"Authorization": f"bearer {token}"}
        self.headers.update(headers)


class ApiInterface:
    """Interface for Halo requests."""

    def __init__(self, api_url: str, session: ApiSession):
        self.api_url = api_url.strip("/")
        self.session = session

    def request(self, method: str, endpoint_url: str, params: dict = None,
                json: (list | dict) = None) -> requests.Response:
        """
        Method to perform the actual API requests.
        :param method: Request method (e.g. get, post...)
        :param endpoint_url: Full API endpoint url
        :param params: Request parameters (for GET requests)
        :param json: Dict for json content (for POST requests)
        :return: Response object or None if request fails
        """
        response = self.session.request(
            method=method,
            url=endpoint_url,
            params=params,
            json=json)

        return response

    def get_dataset_info(self, dataset_id: str) -> requests.Response:
        """
        Make an HTTP request to get general info of a dataset.
        :param dataset_id: Dataset id (from dataset page in avaandmed.eesti.ee)
        :return: Request response object
        """
        dataset_info_endpoint = f"{self.api_url}/datasets/{dataset_id}"
        dataset_info_response = self.request(
            method="GET",
            endpoint_url=dataset_info_endpoint)
        return dataset_info_response

    def get_file(self, dataset_id: str, file_id: str) -> requests.Response:
        file_endpoint = f"{self.api_url}/datasets/{dataset_id}/files/{file_id}/download"
        file_response = self.request(
            method="POST",
            endpoint_url=file_endpoint)
        file_response.encoding = "utf8"
        return file_response
