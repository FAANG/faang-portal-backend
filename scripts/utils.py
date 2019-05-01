"""
Different function that could be used in any faang backend script
"""
import logging
import pprint


def create_logging_instance(name, level=logging.DEBUG):
    """
    This function will create logger instance that will log information to {name}.log file
    Log example: 29-Mar-19 11:54:33 - DEBUG - This is a debug message
    :param name: name of the logger and file
    :param level: level of the logging
    :return: logger instance
    """
    # Create a custom logger
    logger = logging.getLogger(name)

    # Create handlers
    f_handler = logging.FileHandler('{}.log'.format(name))
    f_handler.setLevel(level)

    # Create formatters and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - line %(lineno)s - %(message)s',
                                 datefmt='%y-%b-%d %H:%M:%S')
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)
    return logger


logger = create_logging_instance('utils', level=logging.INFO)
logging.getLogger('elasticsearch').setLevel(logging.WARNING)


def insert_into_es(es, es_index_prefix, doc_type, doc_id, body):
    """
    index data into ES
    :param es: elasticsearch python library instance
    :param es_index_prefix: combined with doc_type to determine which index to write into
    :param doc_type: combined with es_index_prefix to determine which index to write into
    :param doc_id: the id of the document to be indexed
    :param body: the data of the document to be indexed
    :return:
    """
    try:
        existing_flag = es.exists(index=f'{es_index_prefix}_{doc_type}', doc_type="_doc", id=doc_id)
        if existing_flag:
            es.delete(index=f'{es_index_prefix}_{doc_type}', doc_type="_doc", id=doc_id)
        es.create(index=f'{es_index_prefix}_{doc_type}', doc_type="_doc", id=doc_id, body=body)
    except Exception as e:
        # TODO logging error
        logger.error(f"Error when try to insert into index {es_index_prefix}_{doc_type}: " + str(e.args))
        pprint.pprint(body)


def get_number_of_published_papers(data):
    """
    This function will return number of ids that have associated published papers
    :param data:
    :return: dict with yes and no as keys and number of documents for each category
    """
    paper_published_data = {
        'yes': 0,
        'no': 0
    }
    for item in data:
        if 'paperPublished' in item['_source'] and item['_source']['paperPublished'] == 'true':
            paper_published_data['yes'] += 1
        else:
            paper_published_data['no'] += 1
    return paper_published_data


def get_standard(data):
    """
    This function will return number of documents for each existing standard
    :param data: data to parse
    :return: dict with standards names as keys and number of documents with each standard as values
    """
    standard_data = dict()
    for item in data:
        standard_data.setdefault(item['_source']['standardMet'], 0)
        standard_data[item['_source']['standardMet']] += 1
    return standard_data


def create_summary_document_for_es(data):
    """
    This function will create document structure appropriate for es
    :param data: data to parse
    :return: part of document to be inserted into es
    """
    results = list()
    for k, v in data.items():
        results.append({
            "name": k,
            "value": v
        })
    return results


def create_summary_document_for_breeds(data):
    """
    This function will create document structure for breeds summary that are appropriate for es
    :param data: data to parse
    :return: part of document to be inserted into es
    """
    results = list()
    for k, v in data.items():
        tmp_list = list()
        for tmp_k, tmp_v in v.items():
            tmp_list.append({
                'breedsName': tmp_k,
                'breedsValue': tmp_v
            })
        results.append({
            "speciesName": k,
            "speciesValue": tmp_list
        })
    return results


def determine_file_and_source(record):
    file_type = ''
    source_type = ''
    for data_source in DATA_SOURCES:
        for my_type in DATA_TYPES:
            key_to_check = f"{data_source}_{my_type}"
            if key_to_check in record and record[key_to_check] != '':
                file_type = my_type
                source_type = data_source
                return file_type, source_type
    return file_type, source_type


DATA_SOURCES = ['fastq', 'sra', 'cram_index']
DATA_TYPES = ['ftp', 'galaxy', 'aspera']


def check_existsence(data_to_check, field_to_check):
    if field_to_check in data_to_check:
        if len(data_to_check[field_to_check]) == 0:
            return None
        else:
            return data_to_check[field_to_check]
    else:
        return None


def remove_underscore_from_end_prefix(es_index_prefix: str)->str:
    if es_index_prefix.endswith("_"):
        str_len = len(es_index_prefix)
        es_index_prefix = es_index_prefix[0:str_len - 1]
    return es_index_prefix
