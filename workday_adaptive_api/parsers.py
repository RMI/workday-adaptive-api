from __future__ import annotations

from io import StringIO
import xml.etree.ElementTree as ET

import pandas as pd


def parse_xml(xml_text: str) -> ET.Element:
    """Parse XML while tolerating leading whitespace."""
    return ET.fromstring(xml_text.strip())


def adaptive_export_to_dataframe(xml_text: str) -> pd.DataFrame:
    """
    Parse Adaptive responses that embed CSV in CDATA blocks.

    Supports payloads that place CSV inside either <data> or <output> nodes.
    """
    root = parse_xml(xml_text)
    candidates = root.findall(".//data") + root.findall(".//output")
    frames: list[pd.DataFrame] = []

    for node in candidates:
        cdata = (node.text or "").strip()
        if not cdata:
            continue
        frames.append(pd.read_csv(StringIO(cdata)))

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def export_accounts_to_dataframe(xml_text: str) -> pd.DataFrame:
    """Flatten <account .../> nodes from an exportAccounts response."""
    root = parse_xml(xml_text)
    account_nodes = root.findall(".//output//accounts//account")
    if not account_nodes:
        return pd.DataFrame()
    return pd.DataFrame([node.attrib for node in account_nodes])


def generic_elements_to_dataframe(xml_text: str, element_path: str) -> pd.DataFrame:
    """Flatten arbitrary XML elements selected by an ElementTree path."""
    root = parse_xml(xml_text)
    elements = root.findall(element_path)
    if not elements:
        return pd.DataFrame()
    return pd.DataFrame([element.attrib for element in elements])


def dimensions_to_dataframe(xml_text: str) -> pd.DataFrame:
    """
    Flatten dimensions XML into one row per dimensionValue.

    Dimension attributes are copied onto each value row. Values nested under
    another value are included, with ``value_parent_id`` set to the parent's id.
    """
    root = parse_xml(xml_text)
    rows: list[dict[str, str | None]] = []

    for dimension in root.findall(".//dimensions/dimension"):
        dimension_attrs = dimension.attrib
        pending = [(value, None) for value in dimension.findall("./dimensionValue")]
        index = 0
        while index < len(pending):
            value, parent_id = pending[index]
            index += 1
            value_attrs = value.attrib
            pending.extend(
                (child, value_attrs.get("id"))
                for child in value.findall("./dimensionValue")
            )
            rows.append(
                {
                    "dimension_id": dimension_attrs.get("id"),
                    "dimension_name": dimension_attrs.get("name"),
                    "dimension_short_name": dimension_attrs.get("shortName"),
                    "dimension_list_dimension": dimension_attrs.get("listDimension"),
                    "dimension_use_on_levels": dimension_attrs.get("useOnLevels"),
                    "value_id": value_attrs.get("id"),
                    "value_parent_id": parent_id,
                    "value_name": value_attrs.get("name"),
                    "value_short_name": value_attrs.get("shortName"),
                    "value_description": value_attrs.get("description"),
                    "value_code": value_attrs.get("code"),
                    "value_display_name": value_attrs.get("displayName"),
                }
            )

    return pd.DataFrame(rows)
