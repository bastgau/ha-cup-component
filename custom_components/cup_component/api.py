"""Cup API client for retrieving summary data, managing image refresh, and handling HTTP communication with the Cup server."""

import asyncio
from datetime import datetime
import logging
import re
from socket import gaierror
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ContentTypeError

from .exceptions import (
    ClientConnectorError,
    ContentApiTypeError,
    handle_status,
)

# Mapping from API version_update_type values to internal names
_VERSION_UPDATE_TYPE_MAPPING: dict[str, str] = {
    "major": "major_updates",
    "minor": "minor_updates",
    "other": "other_updates",
    "patch": "patch_updates",
    "unknown": "unknown",
    "up_to_date": "up_to_date",
}


class CupApi:
    """Cup API Client."""

    _logger: logging.Logger | None
    _session: ClientSession
    _prefix: str = "/api/v3"

    def __init__(
        self,
        session: ClientSession,
        url: str,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize Cup API Client object with an API URL and an optional logger.

        Args:
            session (ClientSession): The aiohttp client session used to perform HTTP requests.
            url (str): Represents the URL of API endpoint.
            logger (logging.Logger | None): Expects an object of type `logging.Logger` or `None` which will be used to display debug message.

        """

        self.url: str = url
        self._logger = logger
        self._session = session

        self.cache_metrics: dict[str, Any] = {}
        self.cache_images: dict[str, list[Any]] = {}
        self.cache_last_checked: datetime | None = None

    def _get_logger(self) -> logging.Logger:
        """Return a logger if it exists, otherwise it creates a new logger.

        Returns:
            logging.Logger: The logger provided during object initialization, otherwise a new logger is created.

        """

        if self._logger is None:
            return logging.getLogger()

        return self._logger

    async def _call(
        self,
        route: str,
        method: str,
        data: dict[str, Any] | None = None,
        req_timeout: int = 10,
        parse_response: bool = True,
    ) -> dict[str, Any]:
        """Send HTTP requests with specified method, route, and data.

        Args:
            route (str): Represents the specific endpoint that you want to call.
            method (str): Represents the HTTP method to be used. It can be one of the following: "post", "delete", "get", etc.
            data (dict[str, Any] | None): Used to pass a dictionary containing data to be sent in the request when making a POST request.
            req_timeout (int): The duration controlling the request timeout.
            parse_response (bool): Whether to parse the JSON response body. Set to False when no response body is expected.

        Returns:
            dict[str, Any]: A dictionary is being returned with keys "code", "reason", and "data".

        """

        url: str = self._clean_url(f"{self.url}{self._prefix}{route}")

        headers: dict[str, str] = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        self._get_logger().debug("Request (%s): %s %s", route, method.upper(), url)

        try:
            request: ClientResponse = await self._dispatch_request(url, method, data, headers, req_timeout)
        except (TimeoutError, ClientError, gaierror) as err:
            raise ClientConnectorError from err

        result_data: dict[str, Any] = {}

        self._get_logger().debug("Status Code: %d", request.status)
        handle_status(request.status)

        if request.status < 400 and request.content_length != 0 and request.content_length is not None:
            try:
                if request.status != 204 and parse_response:
                    result_data = await request.json()

            except ContentTypeError as err:
                raise ContentApiTypeError from err

        return {
            "code": request.status,
            "reason": request.reason,
            "data": result_data,
        }

    async def _dispatch_request(
        self,
        url: str,
        method: str,
        data: dict[str, Any] | None,
        headers: dict[str, str],
        req_timeout: int,
    ) -> ClientResponse:
        """Dispatch an HTTP request using the appropriate aiohttp method.

        Args:
            url (str): The full URL to send the request to.
            method (str): The HTTP method to use (get, post, put, delete).
            data (dict[str, Any] | None): Optional payload for POST or PUT requests.
            headers (dict[str, str]): HTTP headers to include in the request.
            req_timeout (int): Timeout duration in seconds.

        Returns:
            ClientResponse: The aiohttp response object.

        Raises:
            RuntimeError: If the HTTP method is not supported.

        """

        method = method.lower()

        async with asyncio.timeout(req_timeout):
            if method == "post":
                return await self._session.post(url, json=data, headers=headers)
            if method == "put":
                return await self._session.put(url, json=data, headers=headers)
            if method == "delete":
                return await self._session.delete(url, headers=headers)
            if method == "get":
                return await self._session.get(url, headers=headers)

            msg: str = "Method is not supported/implemented."
            raise RuntimeError(msg)

    async def refresh(self) -> dict[str, Any]:
        """Refresh image information from Cup Server.

        Returns:
            dict[str, Any]: A dictionary with the keys "code", "reason", and "data".

        """

        url: str = "/refresh"

        result: dict[str, Any] = await self._call(url, method="GET", parse_response=False)

        return {
            "code": result["code"],
            "reason": result["reason"],
            "data": result["data"],
        }

    async def call_get_all_data(self) -> dict[str, Any]:
        """Retrieve metrics from Cup Server.

        Returns:
            dict[str, Any]: A dictionary with the keys "code", "reason", and "data".

        Raises:
            ContentApiTypeError: If the 'last_updated' field is missing from the API response.

        """

        url: str = "/json"

        result: dict[str, Any] = await self._call(url, method="GET")

        last_updated = result["data"].get("last_updated")

        if last_updated is None:
            msg: str = "Missing 'last_updated' field in API response."
            raise ContentApiTypeError(msg)

        self.cache_last_checked = datetime.fromisoformat(last_updated)

        try:
            self._calculate_images(result["data"])
        except KeyError:  # ai: ignore
            if self._logger is not None:
                self._logger.exception("Incorrect output format for _calculate_images().")

        try:
            self._calculate_metrics()
        except KeyError:  # ai: ignore
            if self._logger is not None:
                self._logger.exception("Incorrect output format for _calculate_metrics().")

        return {
            "code": result["code"],
            "reason": result["reason"],
            "data": result["data"],
        }

    def _clean_url(self, url: str) -> str:
        """Remove extra slashes in a URL while ignoring those immediately following "://".

        Args:
            url (str): The URL from which extra slashes need to be removed.

        Returns:
            str: The corrected URL with unwanted double slashes replaced by a single slash.

        """

        pattern = r"(?<!:)/{2,}"
        return re.sub(pattern, "/", url)

    def _calculate_images(self, data: dict[str, Any]) -> None:
        """Parse image data from the API response and group images by update type.

        Iterates over the list of images returned by the Cup API and categorises each
        image into one of the following buckets: major_updates, minor_updates,
        patch_updates, other_updates, unknown, or up_to_date. The result is stored
        in the instance attribute ``cache_images``.

        Args:
            data (dict[str, Any]): The raw payload returned by the Cup API, expected
                to contain an ``images`` key holding a list of image objects.

        Returns:
            None.

        """

        new_images: dict[str, list[Any]] = {
            "major_updates": [],
            "minor_updates": [],
            "other_updates": [],
            "patch_updates": [],
            "unknown": [],
            "up_to_date": [],
        }

        for image in data["images"]:
            if image["result"]["has_update"] is None:
                new_images["unknown"].append(image)
                continue

            if image["result"]["has_update"] is False:
                new_images["up_to_date"].append(image)
                continue

            if "version_update_type" in image["result"]["info"]:
                key: str = image["result"]["info"]["version_update_type"]
                new_images[_VERSION_UPDATE_TYPE_MAPPING[key]].append(image)  # KeyError thrown later
                continue

            new_images["other_updates"].append(image)

        self.cache_images = new_images

    def _calculate_metrics(self) -> None:
        """Compute summary counters from the categorised image cache.

        Reads ``cache_images`` (populated by ``_calculate_images``) and builds a
        flat dictionary of integer counters for each update category. Two derived
        metrics are also computed:

        - ``monitored_images``: total number of images across all categories.
        - ``updates_available``: number of images that have an update pending,
          excluding images in the ``up_to_date`` and ``unknown`` categories.

        The result is stored in the instance attribute ``cache_metrics``.

        Returns:
            None.

        """

        new_metrics: dict[str, int] = {
            "major_updates": 0,
            "minor_updates": 0,
            "other_updates": 0,
            "patch_updates": 0,
            "unknown": 0,
            "up_to_date": 0,
        }

        for version_update_type, images in self.cache_images.items():
            new_metrics[version_update_type] = len(images)

        new_metrics["monitored_images"] = sum(new_metrics.values())

        new_metrics["updates_available"] = (
            new_metrics["monitored_images"] - new_metrics["up_to_date"] - new_metrics["unknown"]
        )

        self.cache_metrics = new_metrics
