import unittest
import numpy as np
from engine import prepare_query, rrf, weighted, canonical

class QueryTests(unittest.TestCase):
    def test_case_and_expansion(self):
        self.assertEqual(prepare_query('NLP QA', set())[0], 'natural language processing question answering')
    def test_spelling_and_protected_phrase(self):
        q, phrases, changes = prepare_query('translatoin "rare phrase"', {'translation', 'rate', 'phase'})
        self.assertEqual(q, 'translation rare phrase')
        self.assertEqual(phrases, ['rare phrase'])
        self.assertEqual(len(changes), 1)
    def test_phrase_boundaries(self):
        self.assertNotIn(' question answer ', ' ' + canonical('question answering') + ' ')
        self.assertIn(' question answering ', ' ' + canonical('Question\nAnswering') + ' ')
    def test_fusion_rewards_agreement(self):
        sparse = np.array([10., 9., 0.])
        dense = np.array([.2, .9, .8])
        scores = rrf(sparse, dense)
        self.assertEqual(int(scores.argmax()), 1)
        self.assertAlmostEqual(scores[1], 1/62 + 1/61)
        self.assertAlmostEqual(scores[2], 1/62)
    def test_weighted_extremes(self):
        a, b = np.array([10., 0.]), np.array([0., 1.])
        self.assertEqual(int(weighted(a,b,1).argmax()), 0)
        self.assertEqual(int(weighted(a,b,0).argmax()), 1)
        self.assertTrue(np.isfinite(weighted(a*0,b*0)).all())

if __name__ == '__main__':
    unittest.main()
