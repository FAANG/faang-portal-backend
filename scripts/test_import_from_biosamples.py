"""
Test cases for import_from_biosamples
"""
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import import_from_biosamples


class TestImportFromBiosamples(unittest.TestCase):
    def test_get_existing_etags(self):
        return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'etag': 1,
                            'biosampleId': 1
                        }
                    },
                    {
                        '_source': {
                            'etag': 2,
                            'biosampleId': 2
                        }
                    }
                ]
            }
        }
        with patch('import_from_biosamples.requests') as mock_requests:
            tmp = mock_requests.get.return_value
            tmp.json.return_value = return_value
            results = import_from_biosamples.get_existing_etags('wp-np3-e2:9200', 'faang_build_3_')
            mock_requests.get.assert_called_with(
                'http://wp-np3-e2:9200/faang_build_3_specimen/_search?_source=biosampleId,'
                'etag&sort=biosampleId&size=100000')
            self.assertEqual(results, {1: 1, 2: 2})

    def test_fetch_records_by_project_via_etag(self):
        pass

    def test_fetch_records_by_project(self):
        pass

    def test_fetch_single_record(self):
        with patch('import_from_biosamples.requests') as mock_requests:
            tmp = mock_requests.get.return_value
            tmp.json.return_value = dict()
            with patch('import_from_biosamples.ETAGS_CACHE') as mock_etags_cache:
                mock_etags_cache.__getitem__.return_value = dict()
                results = import_from_biosamples.fetch_single_record(1)
            mock_requests.get.assert_called_with(
                'https://www.ebi.ac.uk/biosamples/samples/1.json?curationdomain=self.FAANG_DCC_curation')
            self.assertEqual(results, {'etag': {}})

    def test_check_is_faang(self):
        item_true = {
            'characteristics': {
                'project': [
                    {
                        'text': 'FAANG'
                    }
                ]
            }
        }
        item_false = {
            'characteristics': {
                'project': [
                    {
                    }
                ]
            }
        }
        self.assertEqual(import_from_biosamples.check_is_faang(item_true), True)
        self.assertEqual(import_from_biosamples.check_is_faang(item_false), False)

    def test_deal_with_decimal_degrees(self):
        item = {
            'characteristics': {
                'Material': [
                    {'text': 'organism'}
                ]
            }
        }
        self.assertEqual(import_from_biosamples.deal_with_decimal_degrees(item), item)

        item['characteristics']['birth location latitude'] = [{'unit': 'decimal degrees'}]
        item['characteristics']['birth location longitude'] = [{'unit': 'decimal degrees'}]
        self.assertEqual(import_from_biosamples.deal_with_decimal_degrees(item), item)

        item['characteristics']['birth location latitude'] = [{'unit': 'decimal degree'}]
        item['characteristics']['birth location longitude'] = [{'unit': 'decimal degree'}]
        item['accession'] = 1
        with patch('import_from_biosamples.requests') as mock_requests:
            import_from_biosamples.deal_with_decimal_degrees(item)
            mock_requests.get.assert_called_with('https://www.ebi.ac.uk/biosamples/samples/'
                                                 '1.json?curationdomain=self.FAANG_DCC_curation')

        item['characteristics']['Material'][0]['text'] = 'specimen'
        self.assertEqual(import_from_biosamples.deal_with_decimal_degrees(item), item)

    def test_process_organisms(self):
        pass

    def test_process_specimens(self):
        pass

    def test_process_cell_specimens(self):
        pass

    def test_process_cell_cultures(self):
        pass

    def test_process_pool_specimen(self):
        pass

    def test_process_cell_lines(self):
        pass

    def test_check_existence(self):
        pass

    def test_populate_basic_biosample_info(self):
        pass

    def test_extract_custom_field(self):
        pass

    def test_get_health_status(self):
        pass

    def test_parse_relationship(self):
        pass

    def test_get_alternative_id(self):
        pass

    def test_add_organism_info_for_specimen(self):
        pass

    def test_parse_date(self):
        pass

    def test_insert_into_es(self):
        pass

    def test_clean_elasticsearch(self):
        pass