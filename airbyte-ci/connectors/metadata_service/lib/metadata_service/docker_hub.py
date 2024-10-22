#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import os
import time
from typing import Optional

import requests
from security import safe_requests


def get_docker_hub_auth_token() -> str:
    docker_username = os.environ.get("DOCKER_HUB_USERNAME")
    docker_password = os.environ.get("DOCKER_HUB_PASSWORD")

    if not (docker_username and docker_password):
        raise ValueError("Please set the DOCKER_HUB_USERNAME and DOCKER_HUB_PASSWORD environment variables.")

    auth_url = "https://hub.docker.com/v2/users/login/"
    auth_data = {"username": docker_username, "password": docker_password}
    response = requests.post(auth_url, json=auth_data)

    if response.status_code != 200:
        raise ValueError("Failed to authenticate with Docker Hub. Please check your credentials.")

    token = response.json().get("token")
    return token


def is_image_on_docker_hub(image_name: str, version: str, digest: Optional[str] = None, retries: int = 0, wait_sec: int = 30) -> bool:
    """Check if a given image and version exists on Docker Hub.

    Args:
        image_name (str): The name of the image to check.
        version (str): The version of the image to check.
        digest (str, optional): The digest of the image to check. Defaults to None.
        retries (int, optional): The number of times to retry the request. Defaults to 0.
        wait_sec (int, optional): The number of seconds to wait between retries. Defaults to 30.
    Returns:
        bool: True if the image and version exists on Docker Hub, False otherwise.
    """

    token = get_docker_hub_auth_token()
    headers = {"Authorization": f"JWT {token}"}
    tag_url = f"https://registry.hub.docker.com/v2/repositories/{image_name}/tags/{version}"

    # Allow for retries as the DockerHub API is not always reliable with returning the latest publish.
    for _ in range(retries + 1):
        response = safe_requests.get(tag_url, headers=headers)
        if response.ok:
            break
        time.sleep(wait_sec)

    if not response.ok:
        response.raise_for_status()
        return False

    # If a digest is provided, check that it matches the digest of the image on Docker Hub.
    if digest is not None:
        return f"sha256:{digest}" == response.json()["digest"]
    return True
