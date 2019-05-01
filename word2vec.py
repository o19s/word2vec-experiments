from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import numpy as np
from elasticsearch import Elasticsearch
import os.path
from rp import random_projection
#logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


class Split():
    def __init__(self, vecs, depth=10):
        self.lhs = self.rhs = None
        self.vecs = vecs
        if vecs.shape[0] < 50:
            return

        rand_vect, lhs, rhs = random_projection(vecs)
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


def train(docs, vector_size, window, negative,
         min_count, epochs):
    tag_docs = [TaggedDocument(terms, [doc_id])
                for doc_id, terms
                in docs.items()]
    print("training on %s docs" % len(tag_docs))
    # vector 32, window 30, min count 2
    model = Doc2Vec(tag_docs, vector_size=vector_size, window=window, min_count=min_count, workers=10, epochs=epochs, negative=negative)
    return model


def prepare_model(es, window=10, epochs=5,
                  vector_size=300, negative=0, min_count=1):
    from analyzed_docs import load, save, docs_from_json

    model_file = 'tmdbdoc2vec.model'

    #if os.path.isfile(model_file):
    #    model = Doc2Vec.load(model_file)
    #    return model

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
    model = train(docs, window=window,
                  vector_size=vector_size,
                  epochs=epochs,
                  negative=negative, min_count=min_count)
    print("Saving")
    model.save(model_file)

    return model


def compare_terms(model, es):
    print("Creating 10 projections")
    rand_vects = []
    for i in range(0,5):
        rand_proj, lhs, rhs = random_projection(model.wv.syn0)
        rand_vects.append(rand_proj)

    while True:
        text1 = input()
        analyzed_text1 = overview_text_no_stop(es, text1)[0]
        vect1 = model.wv.get_vector(analyzed_text1)
        neg_vect1 = np.negative(vect1)
        print(model.most_similar(analyzed_text1))
        print(model.similar_by_vector(neg_vect1))


        text2 = input()
        analyzed_text2 = overview_text_no_stop(es, text2)[0]
        vect2 = model.wv.get_vector(analyzed_text2)
        print(model.similarity(analyzed_text1, analyzed_text2))
        same = 0
        for rand_vect in rand_vects:
            dot_prod1 = np.dot(vect1,rand_vect)
            dot_prod2 = np.dot(vect2,rand_vect)
            #print("%s*%s=%s" % (vect1,rand_vect,dot_prod1))
            #print("%s*%s=%s" % (vect2,rand_vect,dot_prod2))
            if dot_prod1 > 0 and dot_prod2 > 0:
                same += 1
            elif dot_prod1 < 0 and dot_prod2 < 0:
                same += 1
        print("RP Sim %s" % (same / len(rand_vects)))
        #print(rp_tree.eval_path(vect))


class RPTree:
    def __init__(self, vects, depth):
        self.rand_projs = []
        for i in range(0,depth):
            hyperplane, lhs, rhs = random_projection(vects)
            self.rand_projs.append(hyperplane)

    def eval(self, vect):
        result = ''
        for hyperplane in self.rand_projs:
            dot_prod = np.dot(vect,hyperplane)
            if dot_prod > 0:
                result += '1'
            else:
                result += '0'
        return result


if __name__ == "__main__":
    from analyzed_docs import overview_text, overview_text_no_stop
    es = Elasticsearch()
    model = prepare_model(es)
    #compare_terms(model,es)


    #for i in range(0,10):
    #    rp_trees.append(Split(model.wv.syn0, depth=20))
    rambo = model.docvecs['7555']
    star_wars = model.docvecs['11']
    clone_wars = model.docvecs['12180']
    empire_strikes_back = model.docvecs['1891']
    return_of_the_jedi = model.docvecs['1892']

    import pdb; pdb.set_trace()

    for _ in range(0,20):

        rp_trees = [RPTree(model.docvecs.doctag_syn0, depth=16) for _ in range(0,5)]
        same1 = 0
        same2 = 0
        for tree in rp_trees:
            d1 = tree.eval(star_wars)
            d2 = tree.eval(empire_strikes_back)
            d3 = tree.eval(rambo)

            off = 0
            for i in range(0,len(d1)):
                if d1[i] != d2[i]:
                    off += 1
            if off <= 1:
                same1 += 1

            off = 0
            for i in range(0,len(d1)):
                if d1[i] != d3[i]:
                    off += 1
            if off <= 1:
                same2 += 1

            print(d1)
            print(d2)
            print(d3)

        print("RPForest SW Sim: %s" % (same1 / len(rp_trees)))
        print("RPForest RB Sim: %s" % (same2 / len(rp_trees)))


        #rp_tree = Split(model.docvecs.doctag_syn0, depth=20)
        #print(rp_tree.eval_path(rambo))
        #print("Star Wars  %s" % rp_tree.eval_path(star_wars))
        #print("Empire SB  %s" % rp_tree.eval_path(empire_strikes_back))
        #print("Return Jd  %s" % rp_tree.eval_path(return_of_the_jedi))
        #print("Clone Wars %s" % rp_tree.eval_path(clone_wars))
        #print("----")
        #print("Rambo      %s" % rp_tree.eval_path(rambo))
        #print()
        #print()

    #vecs = rp_tree.eval(rambo)
    #import pdb; pdb.set_trace()
    #for vec in vecs:
    #    print(model.wv.similar_by_vector(vec)[0])

    #star_trek_text = analyzed_text(es=es,index='tmdb', field='overview', text='star trek')

    #star_trek_vec = model.infer_vector(star_trek_text)
    #simdocs = model.docvecs.most_similar(star_trek_vec, topn=5)
    #for doc in simdocs:
    #    print(doc)



