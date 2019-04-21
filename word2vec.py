from gensim.test.utils import common_texts
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import numpy as np
from elasticsearch import Elasticsearch

def analyzed_text(es, index, field, text):
    body = {
        "field": field,
        "text": text
    }
    resp = es.indices.analyze(index=index, body=body)

    rVal = [token['token'] for token in resp['tokens']]
    return rVal


def TaggedDocsFromJson(es, index='tmdb', fname='tmdb57k.json'):
    """ Use specified ES analysis, but pull
        from tmdb.json"""

    import json
    movies = json.load(open(fname))

    for idx, (tmdb_id, movie) in enumerate(movies.items()):
        if 'overview' in movie and movie['overview'] is not None:
            overview_terms = analyzed_text(es=es, index=index,
                                           field='overview',
                                           text=movie['overview'])
        if (idx % 100 == 0):
            print("Processed %s docs" % idx)
        yield TaggedDocument(overview_terms, [tmdb_id])





def TaggedEsDocs(es, index='tmdb'):
    """ Scroll through ES index to produce TaggedDocs for
        Doc2Vec"""
    match_all = \
    {
        "query": {
            "match_all": {}
        }
    }
    res = es.search(index=index, scroll='2m',
                    size=1000, body=match_all)

    scroll_id = res['_scroll_id']
    scroll_size = res['hits']['total']

    while scroll_size > 0:
        print("Scrolling...")

        for doc in res['hits']['hits']:
            if 'overview' in doc['_source'] and doc['_source']['overview'] is not None:
                overview_terms = analyzed_text(es=es, index=index, field='overview', text=doc['_source']['overview'])
                yield TaggedDocument(overview_terms, [doc['_id']])
        res = es.scroll(scroll_id=scroll_id, scroll='2m')
        scroll_id = res['_scroll_id']
        scroll_size = len(res['hits']['hits'])


def random_projection(vecs):
    # Random projections
    # Create a random hyperplane into wordvecs,
    # then split into rhs (> 0) and lhs (<= 0)
    print(vecs.shape)
    # Very naive split
    rhs = np.array([])
    lhs = np.array([])
    while lhs.shape[0] == 0 or rhs.shape[0] == 0:
        rand_vect = (np.random.rand(vecs.shape[1])-0.5) * np.max(vecs)
        dots = np.dot(vecs, rand_vect)
        rhs = vecs[dots > 0]
        lhs = vecs[dots <= 0]
    return rand_vect, lhs, rhs

class Split():
    def __init__(self, vecs, depth=10):
        self.lhs = self.rhs = None
        if vecs.shape[0] < 5:
            self.vecs = vecs
            return

        rand_vect, rhs, lhs = random_projection(vecs)
        self.rand_vect = rand_vect

        if depth > 0:
            if lhs.shape[0] > 0:
                self.lhs = Split(lhs, depth=depth-1)
            if rhs.shape[0] > 0:
                self.rhs = Split(rhs, depth=depth-1)
        if self.is_leaf():
            self.vecs = vecs


    def is_leaf(self):
        return (self.rhs == None and self.lhs == None)

    def eval_path(self, vec):
        if self.is_leaf():
            return ''
        dot = np.dot(vec, self.rand_vect)
        if dot > 0:
            return '1' + self.rhs.eval_path(vec)
        else:
            return '0' + self.lhs.eval_path(vec)

    def eval(self, vec):
        if self.is_leaf():
            return self.vecs
        dot = np.dot(vec, self.rand_vect)
        if dot > 0:
            return self.rhs.eval(vec)
        else:
            return self.lhs.eval(vec)



if __name__ == "__main__":
    es=Elasticsearch()
    #documents = [doc for doc in TaggedDocsFromJson(es=es)]
    #model = Doc2Vec(documents, vector_size=25, window=2, min_count=1, workers=4)
    #model.save("tmdbdoc2vec.model")
    model = Doc2Vec.load('tmdbdoc2vec.model')
    rp_tree = Split(model.wv.syn0)
    rambo = model.docvecs['7555']
    star_wars = model.docvecs['11']
    clone_wars = model.docvecs['12180']

    #print(rp_tree.eval_path(rambo))
    print(rp_tree.eval_path(star_wars))
    print(rp_tree.eval_path(clone_wars))

    #vecs = rp_tree.eval(rambo)
    #import pdb; pdb.set_trace()
    #for vec in vecs:
    #    print(model.wv.similar_by_vector(vec)[0])

    #star_trek_text = analyzed_text(es=es,index='tmdb', field='overview', text='star trek')

    #star_trek_vec = model.infer_vector(star_trek_text)
    #simdocs = model.docvecs.most_similar(star_trek_vec, topn=5)
    #for doc in simdocs:
    #    print(doc)



