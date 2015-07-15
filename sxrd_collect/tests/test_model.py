__author__ = 'DAC_User'

import unittest

from models import SxrdModel


class SxrdModelTest(unittest.TestCase):
    def setUp(self):
        self.model = SxrdModel()

    def tearDown(self):
        pass

    def test_create_map(self):
        self.model.add_sample_point('S1', 1.0, 1.0, 0.5)
        self.assertEqual(len(self.model.sample_points), 1)

        self.model.create_map(0,
                              -0.01, 0.01, 0.005,
                              -0.01, 0.01, 0.005)

        self.assertEqual(len(self.model.sample_points), 26)
        self.assertEqual(self.model.sample_points[1].x, 0.99)

        self.model.clear_sample_points()
        self.model.add_sample_point('S1', 0, 0, 0)
        self.model.add_sample_point('S2', 1.0, 2.0, 0.3)

        self.model.create_map(1,
                              -0.01, 0.01, 0.005,
                              0, 0, 0.005)

        self.assertEqual(len(self.model.sample_points), 7)

        self.model.clear_sample_points()
        self.model.add_sample_point('S1', 0, 0, 0)
        self.model.add_sample_point('S2', 1.0, 2.0, 0.3)
        self.model.create_map(1,
                              0, 0, 0.005,
                              -0.01, 0.01, 0.005)

        self.assertEqual(len(self.model.sample_points), 7)
