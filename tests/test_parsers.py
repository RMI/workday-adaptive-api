from __future__ import annotations

import unittest

from workday_adaptive_api.parsers import (
    adaptive_export_to_dataframe,
    dimensions_to_dataframe,
    export_accounts_to_dataframe,
    generic_elements_to_dataframe,
)


class ParserTests(unittest.TestCase):
    def test_adaptive_export_to_dataframe_reads_cdata_csv(self) -> None:
        xml_text = """
        <root>
            <output><![CDATA[col1,col2
1,2
3,4]]></output>
        </root>
        """
        frame = adaptive_export_to_dataframe(xml_text)
        self.assertEqual(frame.shape, (2, 2))
        self.assertEqual(frame.iloc[0]["col1"], 1)

    def test_export_accounts_to_dataframe_flattens_accounts(self) -> None:
        xml_text = """
        <response>
            <output>
                <accounts>
                    <account id="1" code="1000" name="Cash"/>
                    <account id="2" code="2000" name="Revenue"/>
                </accounts>
            </output>
        </response>
        """
        frame = export_accounts_to_dataframe(xml_text)
        self.assertEqual(frame.shape, (2, 3))
        self.assertEqual(frame.iloc[1]["code"], "2000")

    def test_dimensions_to_dataframe_flattens_dimension_values(self) -> None:
        xml_text = """
        <response>
            <output>
                <dimensions>
                    <dimension id="10" name="Project">
                        <dimensionValue id="100" code="PRJ-1" displayName="Project 1"/>
                    </dimension>
                </dimensions>
            </output>
        </response>
        """
        frame = dimensions_to_dataframe(xml_text)
        self.assertEqual(frame.shape[0], 1)
        self.assertEqual(frame.iloc[0]["dimension_name"], "Project")
        self.assertEqual(frame.iloc[0]["value_code"], "PRJ-1")

    def test_empty_xml_sections_return_empty_dataframes(self) -> None:
        xml_text = "<response><output><levels></levels></output></response>"
        frame = generic_elements_to_dataframe(xml_text, ".//output//levels//level")
        self.assertTrue(frame.empty)


if __name__ == "__main__":
    unittest.main()
