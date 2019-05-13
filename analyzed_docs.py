import json

def analyzed_by_field(es, index, field, text):
    body = {
        "field": field,
        "text": text
    }
    resp = es.indices.analyze(index=index, body=body)

    rVal = [token['token'] for token in resp['tokens']]
    return rVal

def analyzed(es, index, analyzer, text):
    body = {
        "analyzer": analyzer,
        "text": text
    }
    resp = es.indices.analyze(index=index, body=body)

    rVal = [token['token'] for token in resp['tokens']]
    return rVal


def overview_text(es, text):
    return analyzed_by_field(es=es, index='tmdb', field='overview', text=text)

def overview_text_no_stop(es, text):
    return analyzed(es=es, index='tmdb', analyzer='english_coloc', text=text)

non_english_movies = ['79633', '17605', '74566',
                      '28745', '18906', '68047',
                      '54157', '53866', '38209',
                      '40627', '37777', '52630',
                      '45535', '14406', '6360',
                      '13748', '18756', '28417',
                      '51437', '59455', '11446',
                      '18419', '65081', '16242',
                      '144611','51883', '61008',
                      '44539', '40191', '45221',
                      '35554', '13386', '31359',
                      '37501', '40192', '38366',
                      '68503', '53975', '111757',
                      '52113', '56944', '22623',
                      '17631', '65611', '13727',
                      '626', '55424', '20693',
                      '26152', '35640', '30527',
                      '34703', '38091', '18825',
                      '40419', '71110', '4272',
                      '15331', '56014', '118802',
                      '22728', '75193', '97128',
                      '13710', '40055', '19268',
                      '19147', '37050', '76241',
                      '50025', '14558', '38870',
                      '77600']


def docs_from_json(es, index='tmdb', fname='tmdb57k.json'):
    """ Use specified ES analysis, but pull
        from tmdb.json"""

    movies = json.load(open(fname))

    for idx, (tmdb_id, movie) in enumerate(movies.items()):
        if 'overview' in movie and movie['overview'] is not None \
            and 'original_language' in movie \
            and movie['original_language'] == 'en':
            analyzed_terms = overview_text_no_stop(es=es,
                                                   text=movie['overview'])
            #analyzed = ' '.join(analyzed_terms)

            #three_grams = [analyzed[i:i+3]
            #               for i in range(len(analyzed)-1)]

            #yield TaggedDocument(analyzed_terms, [tmdb_id])
            if len(analyzed_terms) < 40:
                print("Skipping short movie %s" % (movie['title']))
                continue
            if tmdb_id in non_english_movies:
                print("Blacklist %s lang %s" % (tmdb_id, movie['original_language']))
                continue
            yield (tmdb_id, analyzed_terms)
        else:
            if 'original_language' in movie:
                print("Skipping %s lang %s" % (tmdb_id, movie['original_language']))

        if (idx % 100 == 0):
            print("Processed %s docs" % idx)


def save(docs, out_file='analyzed.json'):
    with open(out_file, 'w') as f:
        json.dump(docs, f)


def load(in_file='analyzed.json'):
    with open(in_file, 'r') as f:
        docs = json.load(f)
        for doc_id, doc in docs.items():
            yield (doc_id, doc)

if __name__ == "__main__":
    from elasticsearch import Elasticsearch
    es = Elasticsearch()
    data_file = 'analyzed.json'
    docs = {doc_id: doc
            for (doc_id, doc)
            in docs_from_json(es)}
    save(docs, out_file=data_file)
