import json

def analyzed_text(es, index, field, text):
    body = {
        "field": field,
        "text": text
    }
    resp = es.indices.analyze(index=index, body=body)

    rVal = [token['token'] for token in resp['tokens']]
    return rVal

def overview_text(es, text):
    return analyzed_text(es=es, index='tmdb', field='overview', text=text)


def docs_from_json(es, index='tmdb', fname='tmdb57k.json'):
    """ Use specified ES analysis, but pull
        from tmdb.json"""

    movies = json.load(open(fname))

    for idx, (tmdb_id, movie) in enumerate(movies.items()):
        if 'overview' in movie and movie['overview'] is not None:
            analyzed_terms = analyzed_text(es=es, index=index,
                                           field='overview',
                                           text=movie['overview'])
            #analyzed = ' '.join(analyzed_terms)

            #three_grams = [analyzed[i:i+3]
            #               for i in range(len(analyzed)-1)]
            yield (tmdb_id, analyzed_terms)
            #yield TaggedDocument(analyzed_terms, [tmdb_id])

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
