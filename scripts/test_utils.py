"""
Test cases for utils module
"""

import unittest
from elasticsearch import Elasticsearch
from unittest.mock import Mock
from unittest.mock import patch
import io

import utils
import constants


class TestUtils(unittest.TestCase):
    def test_create_logging_instance(self):
        logger = utils.create_logging_instance('test')
        self.assertEqual(logger.name, 'test')

    def test_get_number_of_published_papers(self):
        data = [
            {
                "_source": {
                    "paperPublished": "true"
                }
            },
            {
                "_source": {
                    "paperPublished": "true"
                }
            },
            {
                "_source": {
                    "paperPublished": "false"
                }
            },
            {
                "_source": {
                    "paperPublished": "false"
                }
            },
        ]
        self.assertEqual(utils.get_number_of_published_papers(data)['yes'], 2)
        self.assertEqual(utils.get_number_of_published_papers(data)['no'], 2)

    def test_get_standard(self):
        data = [
            {
                "_source": {
                    "standardMet": "FAANG"
                }
            },
            {
                "_source": {
                    "standardMet": "FAANG"
                }
            },
            {
                "_source": {
                    "standardMet": "Legacy"
                }
            },
            {
                "_source": {
                    "standardMet": "Legacy"
                }
            },
        ]
        self.assertEqual(utils.get_standard(data)['FAANG'], 2)
        self.assertEqual(utils.get_standard(data)['Legacy'], 2)

    def test_create_summary_document_for_es(self):
        data = {
            "One": 1,
            "Two": 2
        }
        self.assertEqual(utils.create_summary_document_for_es(data)[0]['name'], 'One')
        self.assertEqual(utils.create_summary_document_for_es(data)[0]['value'], 1)
        self.assertEqual(utils.create_summary_document_for_es(data)[1]['name'], 'Two')
        self.assertEqual(utils.create_summary_document_for_es(data)[1]['value'], 2)

    def test_create_summary_document_for_breeds(self):
        data = {
            "One": {
                "Two": 2
            }
        }
        self.assertEqual(utils.create_summary_document_for_breeds(data)[0]['speciesName'], 'One')
        self.assertEqual(utils.create_summary_document_for_breeds(data)[0]['speciesValue'][0]['breedsName'], 'Two')
        self.assertEqual(utils.create_summary_document_for_breeds(data)[0]['speciesValue'][0]['breedsValue'], 2)