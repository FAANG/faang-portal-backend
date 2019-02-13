from elasticsearch import Elasticsearch

UNIVERSITIES = {
    "ROSLIN": "Roslin Institute (Edinburgh, UK)",
    "INRA": "French National Institute for Agricultural Research",
    "WUR": "Wageningen University and Research",
    "UCD": "University of California, Davis (USA)",
    "USU": "Utah State University (USA)",
    "DEDJTR": "Department of Economic Development, Jobs, Transport and Resources (Bundoora, Australia)",
    "FBN": "Leibniz Institute for Farm Animal Biology (Dummerstorf, Germany)",
    "TAMU": "Texas A&M University",
    "UIC": "University of Illinois at Chicago (USA)",
    "ESTEAM": "ESTeam Paris SUD (France)",
    "ISU": "Iowa State University",
    "KU": "Konkuk University (Seoul, Korea)",
    "NUID": "University College Dublin (Dublin, Ireland)",
    "NMBU": "Norwegian University of Life Sciences (Norway)",
    "UIUC": "University of Illinois at Urbana–Champaign (USA)",
    "UD": "University of Delaware (USA)",
    "UDL": "University of Lleida (Catalonia, Spain)",
    "ULE": "University of León (León, Spain)",
    "USDA": "The United States Department of Agriculture",
}


def create_sample_protocol():
    es = Elasticsearch(['wp-np3-e2', 'wp-np3-e3'])
    results = es.search(index="specimen", size=100000)
    entries = {}
    for result in results["hits"]["hits"]:
        if "specimenFromOrganism" in result["_source"] and 'specimenCollectionProtocol' in \
                result['_source']['specimenFromOrganism']:
            key = result['_source']['specimenFromOrganism']['specimenCollectionProtocol']['filename']
            url = result['_source']['specimenFromOrganism']['specimenCollectionProtocol']['url']
            try:
                protocol_type = result['_source']['specimenFromOrganism']['specimenCollectionProtocol']['url'].split("/")[5]
            except:
                protocol_type = ""
            parsed = key.split("_")
            if parsed[0] in UNIVERSITIES:
                name = UNIVERSITIES[parsed[0]]
                protocol_name = " ".join(parsed[2:-1])
                date = parsed[-1].split(".")[0]
                entries.setdefault(key, {"specimen": [], "universityName": "", "protocolDate": "",
                                         "protocolName": "", "key": "", "url": "", "protocolType": ""})
                specimen = dict()
                specimen["id"] = result["_id"]
                specimen["organismPartCellType"] = result["_source"]["cellType"]["text"]
                specimen["organism"] = result["_source"]["organism"]["organism"]["text"]
                specimen["breed"] = result["_source"]["organism"]["breed"]["text"]
                specimen["derivedFrom"] = result["_source"]["derivedFrom"]

                entries[key]["specimen"].append(specimen)
                entries[key]['universityName'] = name
                entries[key]['protocolDate'] = date[0:4]
                entries[key]["protocolName"] = protocol_name
                entries[key]["key"] = key
                if protocol_type in ["analysis", "assays", "samples"]:
                    entries[key]["protocolType"] = protocol_type
                entries[key]["url"] = url
    for item in entries:
        es.index(index='protocol_samples', doc_type="_doc", id=item, body=entries[item])


def create_experiment_protocol():
    return_results = {}
    es = Elasticsearch(['wp-np3-e2', 'wp-np3-e3'])
    results = es.search(index="experiment", size=100000)

    def expand_object(data, assay='', target='', accession='', storage='', processing=''):
        for key in data:
            if isinstance(data[key], dict):
                if 'filename' in data[key]:
                    if data[key]['filename'] != '' and data[key]['filename'] is not None:
                        if assay == '' and target == '' and accession == '' and storage == '' and processing == '':
                            data_key = "{}-{}-{}".format(key, data['assayType'], data['experimentTarget'])
                            # remove all spaces to form a key
                            data_key = "".join(data_key.split())
                            data_experiment = dict()
                            data_experiment['accession'] = data['accession']
                            data_experiment['sampleStorage'] = data['sampleStorage']
                            data_experiment['sampleStorageProcessing'] = data['sampleStorageProcessing']
                            return_results.setdefault(data_key, {'name': key,
                                                                 'experimentTarget': data['experimentTarget'],
                                                                 'assayType': data['assayType'],
                                                                 'key': data_key,
                                                                 'url': data[key]['url'],
                                                                 'filename': data[key]['filename'],
                                                                 'experiments': []})
                            return_results[data_key]['experiments'].append(data_experiment)
                        else:
                            data_key = "{}-{}-{}".format(key, assay, target)
                            data_key = "".join(data_key.split())
                            data_experiment = dict()
                            data_experiment['accession'] = accession
                            data_experiment['sampleStorage'] = storage
                            data_experiment['sampleStorageProcessing'] = processing
                            return_results.setdefault(data_key, {'name': key,
                                                                 'experimentTarget': target,
                                                                 'assayType': assay,
                                                                 'key': data_key,
                                                                 'url': data[key]['url'],
                                                                 'filename': data[key]['filename'],
                                                                 'experiments': []})
                            return_results[data_key]['experiments'].append(data_experiment)
                else:
                    expand_object(data[key], data['assayType'], data['experimentTarget'], data['accession'],
                                  data['sampleStorage'], data['sampleStorageProcessing'])

    for item in results['hits']['hits']:
        expand_object(item['_source'])
    for item in return_results:
        es.index(index='protocol_files', doc_type="_doc", id=item, body=return_results[item])


if __name__ == "__main__":
    create_sample_protocol()
    create_experiment_protocol()