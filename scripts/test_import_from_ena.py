"""
Test cases for import_from_ena script
"""
import unittest
from unittest.mock import patch, Mock, mock_open

import import_from_ena


class TestImportFromEna(unittest.TestCase):
    def test_determine_file_and_source(self):
        record = {
            'fastq_ftp': 'test'
        }
        self.assertEqual(import_from_ena.determine_file_and_source(record), ('ftp', 'fastq'))
        record = {}
        self.assertEqual(import_from_ena.determine_file_and_source(record), ('', ''))

    @patch('import_from_ena.requests')
    def test_get_ena_data(self, mock_requests):
        import_from_ena.get_ena_data()
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_requests.get.assert_called_with('https://www.ebi.ac.uk/ena/portal/api/search/'
                                             '?result=read_run&format=JSON&limit=0&dataPortal=faang&fields=all')

    @patch('import_from_ena.requests')
    def test_get_all_specimen_ids(self, mock_requests):
        tmp =mock_requests.get.return_value
        tmp.json.return_value = {
            'hits': {
                'hits': [
                    {
                        '_id': '_id',
                        '_source': '_source'
                    }
                ]
            }
        }
        results = import_from_ena.get_all_specimen_ids('wp-np3-e2', 'faang_build_3_')
        self.assertEqual(results, {'_id': '_source'})
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_requests.get.assert_called_with('http://wp-np3-e2:9200/faang_build_3_specimen/_search?size=100000')

    @patch('builtins.open', new_callable=mock_open, read_data="test\ttest")
    def test_get_known_errors(self, mock_file):
        result = import_from_ena.get_known_errors()
        mock_file.assert_called_with('ena_not_in_biosample.txt', 'r')
        self.assertEqual(result, {'test': {'test': 1}})

    def test_check_existsence(self):
        item = {
            'test': [],
            'test3': 'test3'
        }
        self.assertEqual(import_from_ena.check_existsence(item, 'test'), None)
        self.assertEqual(import_from_ena.check_existsence(item, 'test3'), 'test3')
        self.assertEqual(import_from_ena.check_existsence(item, 'test2'), None)
