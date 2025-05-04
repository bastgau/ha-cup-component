"""The above class represents Cup API Client with methods for authentication, retrieving summary data, managing blocking status, and logging requests."""

import asyncio
import logging
import re
from datetime import datetime
from socket import gaierror as GaiError
from typing import Any

import requests
from aiohttp import ClientError, ContentTypeError

from .exceptions import (
    ClientConnectorException,
    ContentTypeException,
    handle_status,
)


class API:
    """Cup API Client."""

    _last_calls: dict[str, datetime] = {}

    _logger: logging.Logger | None
    _session: Any = None
    _prefix: str = "/api/v3/json"

    cache_metrics: dict[str, Any] = {}
    cache_images: dict[str, Any] = {}
    cache_last_checked: datetime | None = None

    url: str = ""

    def __init__(  # noqa: D417
        self,
        session,
        url: str,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize Cup API Client object with an API URL and an optional logger.

        Args:
          url (str): Represents the URL of API endpoint.
          logger (Logger | None): Expects an object of type `Logger` or `None` which will be used to display debug message.

        """

        self.url = url
        self._logger = logger
        self._session = session

    def _get_logger(self) -> logging.Logger:
        """Return a logger if it exists, otherwise it creates a new logger.

        Returns:
          result (Logger): The logger provided during object initialization, otherwise a new logger is created.

        """

        if self._logger is None:
            return logging.getLogger()

        return self._logger

    async def _call(
        self,
        route: str,
        method: str,
        action: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send HTTP requests with specified method, route, and data.

        Args:
            route (str): Represents the specific endpoint that you want to call.
            method (str): Represents the HTTP method to be used. It can be one of the following: "post", "delete", or "get".
            action (str): Represents the action name requested.
            data (dict[str, Any] | None): Used to pass a dictionary containing data to be sent in the request when making a POST request.

        Returns:
          result (dict[str, Any]): A dictionary is being returned with keys "code", "reason", and "data".

        """

        url: str = self._clean_url(f"{self.url}{self._prefix}{route}")

        headers: dict[str, str] = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        self._get_logger().debug("Request (%s): %s %s", action, method.upper(), url)

        request: requests.Response

        try:
            async with asyncio.timeout(10):
                if method.lower() == "post":
                    request = await self._session.post(url, json=data, headers=headers)
                elif method.lower() == "put":
                    request = await self._session.put(url, json=data, headers=headers)
                elif method.lower() == "delete":
                    request = await self._session.delete(url, headers=headers)
                elif method.lower() == "get":
                    request = await self._session.get(url, headers=headers)
                else:
                    raise RuntimeError("Method is not supported/implemented.")

        except (TimeoutError, ClientError, GaiError) as err:
            raise ClientConnectorException from err

        result_data: dict[str, Any] = {}

        self._get_logger().debug("Status Code: %d", request.status)
        handle_status(request.status)

        if request.status < 400 and request.text != "":
            try:
                if request.status != 204:
                    result_data = await request.json()

            except ContentTypeError as err:
                raise ContentTypeException from err

        return {
            "code": request.status,
            "reason": request.reason,
            "data": result_data,
        }

    async def call_get_all_data(self) -> dict[str, Any]:
        """Retrieve metrics from Cup Server

        Returns:
          result (dict[str, Any]): A dictionary with the keys "code", "reason", and "data".

        """

        url: str = ""

        result: dict[str, Any] = await self._call(
            url,
            action="get_all_data",
            method="GET",
        )

        self.cache_last_checked = datetime.fromisoformat(
            result["data"]["last_updated"].replace("Z", "+00:00")
        )

        self._calculate_images(result["data"])
        self._calculate_metrics()

        return {
            "code": result["code"],
            "reason": result["reason"],
            "data": result["data"],
        }

    def _clean_url(self, url: str):
        """
        the method Removes extra slashes in a URL while ignoring those immediately following "://".

        Args:
            url (str): The URL from which extra slashes need to be removed.

        Returns:
            str: The corrected URL with unwanted double slashes replaced by a single slash.
        """

        pattern = r"(?<!:)/{2,}"
        corrected_url = re.sub(pattern, "/", url)
        return corrected_url

    def _calculate_images(self, data: dict[str, Any]) -> None:
        """..."""

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
        """..."""

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
            new_metrics["monitored_images"]
            - new_metrics["up_to_date"]
            - new_metrics["unknown"]
        )

        self.cache_metrics = new_metrics
