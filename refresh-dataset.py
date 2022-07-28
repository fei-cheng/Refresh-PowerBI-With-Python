import json
import os
import time

import msal
import requests
from dotenv import load_dotenv


def refresh_dataset_by_user_account(workspace_id, dataset_id):
    # get parameters from env variables
    load_dotenv()

    username = os.environ["USERNAME"]
    password = os.environ["PASSWORD"]
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes?$top=1"

    data = {
        "grant_type": "password",
        "scope": "openid",
        "resource": "https://analysis.windows.net/powerbi/api",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }
    response = requests.post(
        "https://login.microsoftonline.com/common/oauth2/token", data=data
    )
    assert response.status_code == 200, "Fail to retrieve token: {}".format(
        response.text
    )

    response = response.json()

    if "access_token" in response:
        access_token = response["access_token"]
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        api_call = requests.get(url=url, headers=header)

        result = api_call.json()["value"][0]

        # Check latest Power BI dataset refresh status
        if result["status"] == "Completed":
            # Send Power BI dataset refresh request
            print("Send Power BI dataset refresh request")
            requests.post(url=url, headers=header)


def refresh_dataset_by_service_principal(workspace_id, dataset_id):
    # get parameters from env variables
    load_dotenv()

    tenant_name = os.environ["TENANT_NAME"]
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]

    scope = ["https://analysis.windows.net/powerbi/api/.default"]
    authority_url = f"https://login.microsoftonline.com/{tenant_name}"

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority_url,
        client_credential=client_secret,
    )
    access_token = app.acquire_token_for_client(scopes=scope)["access_token"]

    header = {"Authorization": f"Bearer {access_token}"}
    refresh_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes?$top=1"
    r = requests.post(url=refresh_url, headers=header)
    if r.status_code == 202:  # 202 means refresh request accepted
        print("Succeeded to send Power BI dataset refresh request")
    else:
        raise PowerBiRefreshException(
            f"Failed to send Power BI dataset refresh request. Reason: {r.reason}"
        )

    # sleep several minutes, then check the refresh status
    # if the refresh is still in progress, then sleep longer time before next time check
    # timeout if the refresh is not finished in (3+5+7+9+11) minutes
    for checkpoint in [3, 5, 7, 9, 11]:
        time.sleep(checkpoint * 60)
        r = requests.get(url=refresh_url, headers=header)
        if r.status_code == 200:
            status = json.loads(r.content)["value"][0]["status"]
            if status == "Failed":
                raise PowerBiRefreshException(
                    f"Failed to refresh dataset, please go to Power BI to check detailed error message"
                )
            elif status == "Completed":
                print(f"Completed to refresh dataset")
                return


class PowerBiRefreshException(Exception):
    """
    This Exception indicates that a powerbi dataset refresh has been failed or timeouted.
    """

    pass
