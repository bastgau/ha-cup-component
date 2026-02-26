"""Cup API client for retrieving summary data, managing image refresh, and handling HTTP communication with the Cup server."""

import asyncio
from datetime import datetime
import logging
from logging import Logger
import re
from socket import gaierror
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession, ContentTypeError

from .exceptions import (
    ClientConnectorError,
    ContentApiTypeError,
    handle_status,
)


class CupApi:
    """Cup API Client."""

    _logger: Logger | None
    _session: ClientSession
    _prefix: str = "/api/v3"

    def __init__(
        self,
        session: ClientSession,
        url: str,
        logger: Logger | None = None,
    ) -> None:
        """Initialize Cup API Client object with an API URL and an optional logger.

        Args:
            session (ClientSession): The aiohttp client session used to perform HTTP requests.
            url (str): Represents the URL of API endpoint.
            logger (Logger | None): Expects an object of type `Logger` or `None` which will be used to display debug message.

        """

        self.url: str = url
        self._logger = logger
        self._session = session

        self.cache_metrics: dict[str, Any] = {}
        self.cache_images: dict[str, list[Any]] = {}
        self.cache_last_checked: datetime | None = None

    def _get_logger(self) -> Logger:
        """Return a logger if it exists, otherwise it creates a new logger.

        Returns:
            Logger: The logger provided during object initialization, otherwise a new logger is created.

        """

        if self._logger is None:
            return logging.getLogger()

        return self._logger

    async def _call(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        route: str,
        method: str,
        action: str | None = None,
        data: dict[str, Any] | None = None,
        req_timeout: int = 10,
    ) -> dict[str, Any]:
        """Send HTTP requests with specified method, route, and data.

        Args:
            route (str): Represents the specific endpoint that you want to call.
            method (str): Represents the HTTP method to be used. It can be one of the following: "post", "delete", "get", etc.
            action (str | None): Represents the action name requested.
            data (dict[str, Any] | None): Used to pass a dictionary containing data to be sent in the request when making a POST request.
            req_timeout (int): The duration controlling the request timeout.

        Returns:
            dict[str, Any]: A dictionary is being returned with keys "code", "reason", and "data".

        """

        url: str = self._clean_url(f"{self.url}{self._prefix}{route}")

        headers: dict[str, str] = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        self._get_logger().debug("Request (%s): %s %s", action, method.upper(), url)

        request: ClientResponse

        try:
            method = method.lower()

            async with asyncio.timeout(req_timeout):
                if method == "post":
                    request = await self._session.post(url, json=data, headers=headers)
                elif method == "put":
                    request = await self._session.put(url, json=data, headers=headers)
                elif method == "delete":
                    request = await self._session.delete(url, headers=headers)
                elif method == "get":
                    request = await self._session.get(url, headers=headers)
                else:
                    msg: str = "Method is not supported/implemented."
                    raise RuntimeError(msg)

        except (TimeoutError, ClientError, gaierror) as err:
            raise ClientConnectorError from err

        result_data: dict[str, Any] = {}

        self._get_logger().debug("Status Code: %d", request.status)
        handle_status(request.status)

        if request.status < 400 and request.content_length != 0 and request.content_length is not None:
            try:
                if request.status != 204 and action != "refresh":
                    result_data = await request.json()

            except ContentTypeError as err:
                raise ContentApiTypeError from err

        return {
            "code": request.status,
            "reason": request.reason,
            "data": result_data,
        }

    async def refresh(self) -> dict[str, Any]:
        """Refresh image information from Cup Server.

        Returns:
            dict[str, Any]: A dictionary with the keys "code", "reason", and "data".

        """

        url: str = "/refresh"

        result: dict[str, Any] = await self._call(url, action="refresh", method="GET")

        return {
            "code": result["code"],
            "reason": result["reason"],
            "data": result["data"],
        }

    async def call_get_all_data(self) -> dict[str, Any]:
        """Retrieve metrics from Cup Server.

        Returns:
            dict[str, Any]: A dictionary with the keys "code", "reason", and "data".

        """

        url: str = "/json"

        result: dict[str, Any] = await self._call(
            url,
            action="get_all_data",
            method="GET",
        )

        self.cache_last_checked = datetime.fromisoformat(result["data"]["last_updated"])

        self._calculate_images(result["data"])
        self._calculate_metrics()

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

        mapping: dict[str, str] = {
            "major": "major_updates",
            "minor": "minor_updates",
            "other": "other_updates",
            "patch": "patch_updates",
            "unknown": "unknown",
            "up_to_date": "up_to_date",
        }

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
                new_images[mapping[key]].append(image)
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
