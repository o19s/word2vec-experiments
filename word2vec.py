from gensim.test.utils import common_texts
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import numpy as np
from elasticsearch import Elasticsearch
import json
import os.path



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
    # Very naive split
    rhs = np.array([])
    lhs = np.array([])
    min_size = 0.3 * vecs.shape[0]
    while lhs.shape[0] < min_size or rhs.shape[0] < min_size:
        rand_vect = (np.random.rand(vecs.shape[1])-0.5) * np.max(vecs)
        dots = np.dot(vecs, rand_vect)
        rhs = vecs[dots > 0]
        lhs = vecs[dots <= 0]
    return rand_vect, lhs, rhs

class Split():
    def __init__(self, vecs, depth=10):
        self.lhs = self.rhs = None
        self.vecs = vecs
        if vecs.shape[0] < 50:
            return

        rand_vect, rhs, lhs = random_projection(vecs)
        self.rand_vect = rand_vect

        if depth > 0:
            if lhs.shape[0] > 0:
                self.lhs = Split(lhs, depth=depth-1)
            if rhs.shape[0] > 0:
                self.rhs = Split(rhs, depth=depth-1)


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


def train(docs):
    tag_docs = [TaggedDocument(terms, doc_id) for doc_id, terms in docs.items()]
    print("training on %s docs" % len(tag_docs))
    model = Doc2Vec(tag_docs, vector_size=32, window=50, min_count=2, workers=4)
    return model


def prepare_model(es):
    from analyzed_docs import load, save, docs_from_json

    model_file = 'tmdbdoc2vec.model'

    if os.path.isfile(model_file):
        model = Doc2Vec.load(model_file)
        return model

    data_file = 'analyzed.json'
    if os.path.isfile(data_file):
        print("Attempting to Load Preanalyzed Data")
        docs = {doc_id: doc
                for (doc_id, doc)
                in load(in_file=data_file)}
    else:
        docs = {doc_id: doc
                for (doc_id, doc)
                in docs_from_json(es)}
        save(docs, out_file=data_file)


    print("Training")
    model = train(docs)
    model.save(model_file)

    return model




if __name__ == "__main__":
    from sys import argv
    from analyzed_docs import overview_text
    es = Elasticsearch()
    model = prepare_model(es)
    print(model.similar_by_word(overview_text(es, argv[1])[0]))




    #model = Doc2Vec.load('tmdbdoc2vec.model')
    for i in range(0,10):
        rp_tree = Split(model.docvecs.doctag_syn0, depth=20)
        rambo = model.docvecs['7555']
        star_wars = model.docvecs['11']
        clone_wars = model.docvecs['12180']
        empire_strikes_back = model.docvecs['1891']
        return_of_the_jedi = model.docvecs['1892']

        #print(rp_tree.eval_path(rambo))
        print("Star Wars  %s" % rp_tree.eval_path(star_wars))
        print("Empire SB  %s" % rp_tree.eval_path(empire_strikes_back))
        print("Return Jd  %s" % rp_tree.eval_path(return_of_the_jedi))
        print("Clone Wars %s" % rp_tree.eval_path(clone_wars))
        print("----")
        print("Rambo      %s" % rp_tree.eval_path(rambo))
        print()
        print()

    #vecs = rp_tree.eval(rambo)
    #import pdb; pdb.set_trace()
    #for vec in vecs:
    #    print(model.wv.similar_by_vector(vec)[0])

    #star_trek_text = analyzed_text(es=es,index='tmdb', field='overview', text='star trek')

    #star_trek_vec = model.infer_vector(star_trek_text)
    #simdocs = model.docvecs.most_similar(star_trek_vec, topn=5)
    #for doc in simdocs:
    #    print(doc)



