# SPDX-License-Identifier: Apache-2.0
import unittest
from run_uvm_slice import classify_run


class RunClassificationTests(unittest.TestCase):
    def setUp(self):
        self.log='UVM_PLATFORM_PASS transactions=208 checks=230 seed=7\nUVM_ERROR : 0\nUVM_FATAL : 0\n'

    def test_pass(self): self.assertTrue(classify_run(0,self.log,7)[0])
    def test_nonzero_exit(self): self.assertFalse(classify_run(1,self.log,7)[0])
    def test_wrong_seed(self): self.assertFalse(classify_run(0,self.log,42)[0])
    def test_missing_summary(self): self.assertFalse(classify_run(0,self.log.replace('UVM_FATAL : 0',''),7)[0])
    def test_runtime_error(self): self.assertFalse(classify_run(0,self.log.replace('UVM_ERROR : 0','UVM_ERROR : 1'),7)[0])
    def test_hidden_error_event(self): self.assertFalse(classify_run(0,'UVM_ERROR file @ 1 [GOLDEN] mismatch\n'+self.log,7)[0])
    def test_no_traffic(self): self.assertFalse(classify_run(0,self.log.replace('transactions=208','transactions=0'),7)[0])


if __name__=='__main__': unittest.main(verbosity=2)
