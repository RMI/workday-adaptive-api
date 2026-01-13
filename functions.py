import requests
from dotenv import load_dotenv
import base64
import pandas as pd
import xml.etree.ElementTree as ET
from io import StringIO

date = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')

load_dotenv()

def _parse_xml(xml_text: str) -> ET.Element:
    # Robust parser that ignores leading BOM/whitespace
    return ET.fromstring(xml_text.strip())

def adaptive_export_to_df(xml_text: str) -> pd.DataFrame:
    """
    Works for responses that put CSV inside either <data><![CDATA[...]]></data>
    or directly under <output><![CDATA[...]]></output>.
    Concatenates multiple CDATA blocks if present.
    """
    root = ET.fromstring(xml_text.strip())
    # find CDATA-bearing nodes
    candidates = root.findall(".//data") + root.findall(".//output")
    frames = []
    for node in candidates:
        cdata = (node.text or "").strip()
        if not cdata:
            continue
        frames.append(pd.read_csv(StringIO(cdata)))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def exportaccounts_xml_to_df(xml_text: str) -> pd.DataFrame:
    """
    Handles exportAccounts responses:
    - Flattens <account .../> elements under <accounts> into rows of attributes.
    Returns an empty DataFrame if no <account> nodes are present.
    """
    root = _parse_xml(xml_text)
    acct_nodes = root.findall(".//output//accounts//account")
    if not acct_nodes:
        return pd.DataFrame()
    rows = []
    for n in acct_nodes:
        rows.append(n.attrib)  # attributes include id, code, name, type, etc.
    return pd.DataFrame(rows)

def generic_elements_to_df(xml_text: str, elem_path: str) -> pd.DataFrame:
    """
    For other metadata exports (dimensions, levels, etc.), pass the path to the leaf element, e.g.:
        elem_path=".//output//dimensions//dimension"
        elem_path=".//output//levels//level"
    """
    root = _parse_xml(xml_text)
    elems = root.findall(elem_path)
    if not elems:
        return pd.DataFrame()
    return pd.DataFrame([e.attrib for e in elems])

def get_wd_access_token(url, client_id, client_secret, refresh_token):
    """Obtain a Workday access token using the refresh token flow.
    
    Args:
        url (str): The Workday token endpoint URL.
        client_id (str): The Workday API client ID.
        client_secret (str): The Workday API client secret.
        refresh_token (str): The refresh token for obtaining a new access token.
    
    Returns:
        str: The access token if the request is successful.
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    
    # Create basic auth header
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    payload = f'grant_type=refresh_token&refresh_token={refresh_token}'
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': f'Basic {auth_b64}'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    
    if response.status_code == 200:
        print("Successfully obtained Workday access token.")
        return response.json().get('access_token')
    else:
        raise Exception(f"Failed to get access token: {response.status_code} {response.text}")

def get_adaptive_access_token(wd_access_token, adaptive_access_token_url):
    """Obtain an Adaptive access token using a Workday access token.
    
    Args:
        wd_access_token (str): The Workday access token.
        adaptive_access_token_url (str): The Adaptive access token endpoint URL.
    
    Returns:
        str: The Adaptive access token if the request is successful.
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f"Bearer {wd_access_token}"
    }
    
    response = requests.request("GET", adaptive_access_token_url, headers=headers)
    
    if response.status_code == 200:
        response_data = response.json()
        public_api_token = response_data['data'][0].get('publicAPIToken')
        print("Successfully obtained Adaptive access token.")
        return public_api_token        
    else:
        raise Exception(f"Failed to get access token: {response.status_code} {response.text}")

def adaptive_smoke_test(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code):
    """Run a smoke test against the Adaptive API by sending an exportLevels request.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
    
    Returns:
        None
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API smoke test against {url}. Sending exportLevels request...")
    headers = {
        'Content-Type': 'application/xml'
    }
    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportLevels" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                </call>"""
    
    response = requests.request("POST", url, headers=headers, data=payload)
    
    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API smoke test successful.")
    else:
        print(f"Adaptive API smoke test failed: {response.status_code}: {response.text}")



def adp_exportVersions(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code):
    """Export versions from the Adaptive API.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
    
    Returns:
        None
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API version export against {url}. Sending exportVersions request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportVersions" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                </call>"""

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API version export successful.")
    else:
        print(f"Adaptive API version export failed: {response.status_code}: {response.text}")

def adp_exportSheets(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code):
    """Export sheets from the Adaptive API.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
    
    Returns:
        None
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API sheets export against {url}. Sending exportSheets request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportSheets" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
</call>"""

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API account export successful.")
    else:
        print(f"Adaptive API account export failed: {response.status_code}: {response.text}")



def adp_exportAccounts(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code):
    """Export accounts from the Adaptive API.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
    
    Returns:
        None
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API accounts export against {url}. Sending exportAccounts request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportAccounts" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                </call>"""

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API account export successful.")
    else:
        print(f"Adaptive API account export failed: {response.status_code}: {response.text}")
    
    data = exportaccounts_xml_to_df(response.text)
    data.to_excel("adaptive_accounts_export.xlsx", index=False)

    return data

def adp_exportDimensions(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code, version_name="Live Forecast", dimensionIDs=""):
    """Export dimensions from the Adaptive API.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
        version_name (str): The version name to export dimensions for. Defaults to "Live Forecast".
        dimensionIDs (str): Comma-separated list of dimension IDs to export. Defaults to "" (all dimensions).
    
    Returns:
        pandas.DataFrame: A DataFrame containing the exported dimensions.
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API dimensions export against {url}. Sending exportDimensions request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportDimensions" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                    <include versionName="{version_name}" attributes="true" dimensionIDs="{dimensionIDs}" dimensionValues="true" displayNameEnabled="true"/>

                </call>"""
    

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API dimensions export successful.")
    else:
        print(f"Adaptive API dimensions export failed: {response.status_code}: {response.text}")
    data = dimensions_xml_to_long_df(response.text)
    data.to_excel("adaptive_dimensions_export.xlsx", index=False)

    return data

def adp_projectIDs(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code, version_name="Live Forecast", dimensionIDs=""):
    """Export project IDs from the Adaptive API.
    
    Args:
        adaptive_access_token (str): The Adaptive access token.
        adaptive_public_api_endpoint (str): The Adaptive public API endpoint URL.
        adaptive_instance_code (str): The Adaptive instance code.
        version_name (str): The version name to export project IDs for. Defaults to "Live Forecast".
        dimensionIDs (str): Comma-separated list of dimension IDs to export. Defaults to "" (all dimensions).
    
    Returns:
        pandas.DataFrame: A DataFrame containing the exported project IDs.
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API dimensions export against {url}. Sending exportDimensions request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportDimensions" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                    <include versionName="{version_name}" attributes="true" dimensionIDs="{dimensionIDs}" dimensionValues="true" displayNameEnabled="true"/>

                </call>"""
    
    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive API dimensions export successful.")
    else:
        print(f"Adaptive API dimensions export failed: {response.status_code}: {response.text}")
    data = dimensions_xml_to_long_df(response.text)
    print(data.head())
    return data

def adp_exportData(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code, version_name="Live Forecast",
                   account_code = "", start_date="08/2025", end_date="09/2025", dimension_name="WD Project"):
    """Exports data from the Adaptive API and saves it as an Excel file.
    
    Args:
        adaptive_access_token (str): Access token for authenticating with the Adaptive API.
        adaptive_public_api_endpoint (str): Endpoint URL for the Adaptive API.
        adaptive_instance_code (str): Instance code for the Adaptive API.
        version_name (str, optional): Version name of the data to export. Defaults to "Live Forecast".
        account_code (str, optional): Account code used for naming the output Excel file. Defaults to "".
        start_date (str, optional): Start date for the data export in MM/YYYY format. Defaults to "08/2025".
        end_date (str, optional): End date for the data export in MM/YYYY format. Defaults to "09/2025".
        dimension_name (str, optional): Name of the dimension to export. Defaults to "WD Project".
    
    Returns:
        pandas.DataFrame: A DataFrame containing the exported data.
    
    Raises:
        Exception: If the request fails or returns a non-200 status code.
    """
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API data export against {url}. Sending exportData request...")
    headers = {
        'Content-Type': 'application/xml'
    }
    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportData" callerName="PYTHON">
                <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                <version name="{version_name}" isDefault="false"/>
                <format useInternalCodes="true" includeUnmappedItems="false" displayNameEnabled="true" includeDisplayNames="true"/>
                <filters>
                <accounts>
                    <account code="{account_code}" includeDescendants="true" isAssumption="false"/>
                </accounts>

                <timeSpan start="{start_date}" end="{end_date}"/>
                </filters>
                <dimensions>
                <dimension name="{dimension_name}"/>
                <dimension name="Project ID"/>
                </dimensions>

                <rules>
                </rules>
                </call>"""
    
    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API data export successful.")
    else:
        print(f"Adaptive API data export failed: {response.status_code}: {response.text}")

    data = adaptive_export_to_df(response.text)
    data.to_excel("adaptive_data_export_" + account_code + ".xlsx", index=False)
    return data


def adp_exportModelSheet(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code,sheet_name="",
                        version_name="Live Forecast",
                   account_code = "", start_date="08/2025", end_date="09/2025", level_code="RMI Consolidated Parent"):
    """Exports modeled sheet data from the Adaptive API and saves it as an Excel file.
            Args:
                adaptive_access_token (str): Access token for authenticating with the Adaptive API.
                adaptive_public_api_endpoint (str): Endpoint URL for the Adaptive API.
                adaptive_instance_code (str): Instance code for the Adaptive API.
                sheet_name (str, optional): Name of the modeled sheet to export. Defaults to "".
                version_name (str, optional): Version name of the data to export. Defaults to "Live Forecast".
                account_code (str, optional): Account code used for naming the output Excel file. Defaults to "".
                start_date (str, optional): Start date for the data export in MM/YYYY format. Defaults to "08/2025".
                end_date (str, optional): End date for the data export in MM/YYYY format. Defaults to "09/2025".
                level_code (str, optional): Level code for filtering the data. Defaults to "RMI Consolidated Parent".
            Returns:
                None
            Side Effects:
                - Sends a POST request to the Adaptive API to export modeled sheet data.
                - Prints the API response and status.
                - Saves the exported data as an Excel file named "adaptive_data_export_<account_code>.xlsx".
            Raises:
                None explicitly, but prints error messages if the API request fails."""
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API modeled sheet data export against {url}. Sending exportModelSheet request...")
    headers = {
        'Content-Type': 'application/xml'
    }
    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
        <call method="exportConfigurableModelData" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                    <version name="{version_name}"/>
        <modeled-sheet name="" isGlobal="false" displayNameEnabled="true" includeDisplayNames="true" includeAllColumns="false" isGetAllRows="true" useNumericIDs="false"/>
        <filters>
            <timeSpan start="{start_date}" end="{end_date}"/>
        </filters>
        </call>"""
    
    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API data export successful.")
    else:
        print(f"Adaptive API data export failed: {response.status_code}: {response.text}")

    data = adaptive_export_to_df(response.text)
    print(f"Adaptive API data exported to adaptive_data_export_{account_code}.xlsx")
    return data




def dimensions_xml_to_long_df(xml_text: str) -> pd.DataFrame:
    """
    Parses <dimensions><dimension ...><dimensionValue .../></dimension>...</dimensions>
    into one row per dimensionValue, carrying dimension attributes on each row.
    """
    root = ET.fromstring(xml_text.strip())
    rows = []
    # handle both <output><dimensions>... and top-level <dimensions>...
    for dim in root.findall(".//dimensions/dimension"):
        d = dim.attrib
        for val in dim.findall("./dimensionValue"):
            v = val.attrib  
            rows.append({
                "dimension_id": d.get("id"),
                "dimension_name": d.get("name"),
                "dimension_shortName": d.get("shortName"),
                "dimension_listDimension": d.get("listDimension"),
                "dimension_useOnLevels": d.get("useOnLevels"),
                "value_id": v.get("id"),
                "value_name": v.get("name"),
                "value_shortName": v.get("shortName"),
                "value_description": v.get("description"),
                "value_code": v.get("code"),              
                "value_displayName": v.get("displayName"),
            })
    return pd.DataFrame(rows)


def adp_exportLevels(adaptive_access_token, adaptive_public_api_endpoint, adaptive_instance_code):
    url = adaptive_public_api_endpoint
    print(f"Running Adaptive API levels export against {url}. Sending exportLevels request...")
    headers = {
        'Content-Type': 'application/xml'
    }

    payload = f"""<?xml version='1.0' encoding='UTF-8'?>
                <call method="exportLevels" callerName="PYTHON">
                    <credentials token="{adaptive_access_token}" instanceCode="{adaptive_instance_code}"/>
                </call>"""

    response = requests.request("POST", url, headers=headers, data=payload)

    # if 200 then print response
    if response.status_code == 200:
        print("Adaptive Response: ", response.text)
        print("Adaptive API levels export successful.")
    else:
        print(f"Adaptive API levels export failed: {response.status_code}: {response.text}")

    data = generic_elements_to_df(response.text, elem_path=".//output//levels//level")

    return data



## ------------------ WORKDAY API FUNCTIONS --------------------



def get_raas_data(
    wd_access_token: str,
    request_url: str,
    params: dict | None = None,
    timeout: int = 300,
):
    """
    Generic Workday RaaS fetcher.

    :param wd_access_token: Workday API access token
    :param request_url: Base RaaS Web Service JSON URL
    :param params: Dict of query string parameters for the report
    :param timeout: Request timeout in seconds
    :return: JSON response
    """
    headers = {
        "Authorization": f"Bearer {wd_access_token}",
        "Accept": "application/json",
    }

    response = requests.get(
        request_url,
        headers=headers,
        params=params,
        timeout=timeout,
    )

    if response.ok:
        return response.json()

    raise Exception(
        f"RaaS request failed: {response.status_code} {response.text}"
    )



