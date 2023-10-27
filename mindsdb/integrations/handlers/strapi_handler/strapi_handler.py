from mindsdb.integrations.handlers.strapi_handler.strapi_tables import StrapiTable
from mindsdb.integrations.libs.api_handler import APIHandler
from mindsdb.integrations.libs.response import HandlerStatusResponse as StatusResponse
from mindsdb_sql import parse_sql
from mindsdb.utilities import log
import requests
from mindsdb.integrations.libs.const import HANDLER_CONNECTION_ARG_TYPE as ARG_TYPE
from collections import OrderedDict
import pandas as pd
import json


class StrapiHandler(APIHandler):
    def __init__(self, name: str, **kwargs) -> None:
        """initializer method

        Args:
            name (str): handler name
        """
        super().__init__(name)

        self.connection = None
        self.is_connected = False
        args = kwargs.get('connection_data', {})
        if 'host' in args and 'port' in args:
            self._base_url = f"http://{args['host']}:{args['port']}"
        if 'api_token' in args:
            self._api_token = args['api_token']
        if 'pluralApiIds' in args:
            self._pluralApiIds = args['pluralApiIds']
        # Registers tables for each collections in strapi
        for pluralApiId in self._pluralApiIds:
            self._register_table(table_name=pluralApiId, table_class=StrapiTable(handler=self, name=pluralApiId))

    def check_connection(self) -> StatusResponse:
        """checking the connection

        Returns:
            StatusResponse: whether the connection is still up
        """
        response = StatusResponse(False)
        try:
            self.connect()
            response.success = True
        except Exception as e:
            log.logger.error(f'Error connecting to Strapi API: {e}!')
            response.error_message = e

        self.is_connected = response.success
        return response

    def connect(self) -> StatusResponse:
        """making the connectino object
        """
        if self.is_connected and self.connection:
            return self.connection

        try:
            headers = {"Authorization": f"Bearer {self._api_token}"}
            response = requests.get(f"{self._base_url}", headers=headers)
            if response.status_code == 200:
                self.connection = response
                self.is_connected = True
                return StatusResponse(True)
            else:
                raise Exception(f"Error connecting to Strapi API: {response.status_code} - {response.text}")
        except Exception as e:
            log.logger.error(f'Error connecting to Strapi API: {e}!')
            return StatusResponse(False, error_message=e)

    def native_query(self, query: str) -> StatusResponse:
        """Receive and process a raw query.

        Parameters
        ----------
        query : str
            query in a native format

        Returns
        -------
        StatusResponse
            Request status
        """
        ast = parse_sql(query, dialect="mindsdb")
        return self.query(ast)

    def call_strapi_api(self, method: str, endpoint: str, params: dict = {}, json_data: dict = {}) -> pd.DataFrame:
        headers = {"Authorization": f"Bearer {self._api_token}"}
        url = f"{self._base_url}{endpoint}"

        if method.upper() in ('GET', 'POST', 'PUT', 'DELETE'):
            headers['Content-Type'] = 'application/json'

            if method.upper() in ('POST', 'PUT', 'DELETE'):
                response = requests.request(method, url, headers=headers, params=params, data=json_data)
            else:
                response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                # Create an empty DataFrame
                df = pd.DataFrame()
                if isinstance(data.get('data', None), list):
                    for item in data['data']:
                        # Add 'id' and 'attributes' to the DataFrame
                        row_data = {'id': item['id'], **item['attributes']}
                        df = df._append(row_data, ignore_index=True)
                    return df
                elif isinstance(data.get('data', None), dict):
                    # Add 'id' and 'attributes' to the DataFrame
                    row_data = {'id': data['data']['id'], **data['data']['attributes']}
                    df = df._append(row_data, ignore_index=True)
                    return df
            else:
                raise Exception(f"Error connecting to Strapi API: {response.status_code} - {response.text}")

        return pd.DataFrame()


connection_args = OrderedDict(
    api_token={
        "type": ARG_TYPE.PWD,
        "description": "Strapi API key to use for authentication.",
        "required": True,
        "label": "Api token",
    },
    host={
        "type": ARG_TYPE.URL,
        "description": "Strapi API host to connect to.",
        "required": True,
        "label": "Host",
    },
    port={
        "type": ARG_TYPE.INT,
        "description": "Strapi API port to connect to.",
        "required": True,
        "label": "Port",
    },
    pluralApiIds={
        "type": list,
        "description": "Plural API id to use for querying.",
        "required": True,
        "label": "Plural API id",
    },
)

connection_args_example = OrderedDict(
    host="localhost",
    port=1337,
    api_token="277c4d669060c2c66b140aaa8a38e00b824182dd1634af7c9718344807e662c5cd77d3bfbfa756332d7b044b7ee12e26fc96f800b2d030a9bb0afda422bbf20d2ce6962fc313e32a2ca9cc19f2d89d51a4ca7f64576717c0c2ea28d7908b3be6f8b345f1f351498b7382fb5469a61a42a96ece4c72b21b0e3485ea7addd5189c",
    pluralApiIds=["posts", "portfolios"],
)
