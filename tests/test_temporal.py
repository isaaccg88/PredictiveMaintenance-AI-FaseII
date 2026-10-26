import unittest
import numpy as np
from src.simulation import generate,chronological_split,HORIZON,FEATURES
from src.train import score,threshold_search

class TemporalValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df=generate(seed=202608,steps=2160,machines=60)
        cls.parts=chronological_split(cls.df)

    def test_fleet_and_horizon(self):
        self.assertEqual(len(self.df),60*2160)
        self.assertEqual(self.df.machine_id.nunique(),60)
        self.assertEqual(self.df.failure_next_72h.isna().sum(),60*HORIZON)
        self.assertEqual(len(FEATURES),12)

    def test_target_no_future_leakage(self):
        m=self.df[self.df.machine_id=="PM-003"].reset_index(drop=True)
        ev=m.failure_event.to_numpy()
        for t in [0,20,51,400,1200,2100]:
            expected=int(ev[t+1:t+13].max())
            self.assertEqual(int(m.iloc[t].failure_next_72h),expected)

    def test_temporal_purge_and_holdout(self):
        train=self.parts["train"];val=self.parts["validation"]
        test=self.parts["test_temporal"];holdout=self.parts["test_unseen_machines"]
        self.assertTrue(train.timestamp.max()<val.timestamp.min())
        self.assertTrue(val.timestamp.max()<test.timestamp.min())
        self.assertFalse(set(train.machine_id)&set(holdout.machine_id))
        self.assertEqual(holdout.machine_id.nunique(),12)
        for k,v in self.parts.items():
            self.assertTrue((v.status=="operating").all())
            self.assertTrue(v.failure_next_72h.notna().all())

    def test_threshold_is_validation_only(self):
        y=np.array([0,0,0,1,1,1],dtype=int)
        p=np.array([.1,.2,.6,.7,.8,.9])
        metric,grid,feasible=threshold_search(y,p)
        self.assertEqual(len(grid),81)
        self.assertGreaterEqual(metric["precision"],.2)

    def test_confusion_binary(self):
        m=score([0,0,1,1],[.1,.8,.9,.2],.5)
        self.assertEqual((m["tn"],m["fp"],m["fn"],m["tp"]),(1,1,1,1))

if __name__=="__main__":
    unittest.main()
