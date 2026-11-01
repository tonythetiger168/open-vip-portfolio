# SPDX-License-Identifier: Apache-2.0
"""Synthetic policy tests only; their 100% inputs are NOT measured coverage."""
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from check_export import assess, compatible, IDENTITY, METRICS


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'synthetic.db').write_bytes(b'SYNTHETIC POLICY FIXTURE NOT TOOL COVERAGE')
        ident = {k: 'synthetic-'+k for k in IDENTITY}
        points = {k: ['p'] for k in METRICS}
        points['fsm'] = ['state:IDLE','arc:IDLE->IDLE']
        points['toggle'] = ['rise:bit0','fall:bit0']
        self.baseline = {'identity':ident,'points':points,
                         'functional_requirements': {'p':{'requirement':'TEST_ONLY','legal':True}}}
        self.report = {'identity':ident.copy(),'build_kind':'rtl','blocked_dependencies':[],
                       'run_status':'passed','timed_out':False,'pending_transactions':0,
                       'uvm_errors':0,'uvm_fatals':0,'illegal_bin_hits':0,
                       'assertion_failures':0,'scoreboard_errors':0,'transactions':1,
                       'exporter_id':'synthetic-only', 'raw_db': {'path':'synthetic.db','sha256':hashlib.sha256((self.root/'synthetic.db').read_bytes()).hexdigest()},
                       'metrics':{k:{'status':'measured','raw_points':v[:],'hit_points':v[:],'exclusions':[]} for k,v in points.items()}}
        self.report['metrics']['sva']['assertions']={'p':{'attempts':1,'antecedent_hits':1,'nonvacuous_passes':1,'cover_witnesses':1,'failures':0}}

    def run_assess(self):
        return assess(self.report,self.baseline,{},self.root)

    def test_synthetic_valid_policy(self):
        self.assertTrue(all(x['closed'] for x in self.run_assess().values()))

    def test_all_identity_dimensions_reject_merge(self):
        for key in IDENTITY:
            other=copy.deepcopy(self.report['identity']); other[key]='different'
            with self.subTest(key=key), self.assertRaises(ValueError):
                compatible(self.report['identity'],other)

    def test_unsupported_cannot_be_excluded(self):
        self.report['metrics']['fsm']['status']='unsupported'
        with self.assertRaises(ValueError): self.run_assess()

    def test_unapproved_exclusion(self):
        self.report['metrics']['line']['exclusions']=[{'point':'p','approval_id':'self-approved'}]
        with self.assertRaises(ValueError): self.run_assess()

    def test_approved_exclusion_preserves_raw_denominator(self):
        self.baseline['points']['line'].append('unreachable')
        self.report['metrics']['line']['raw_points'].append('unreachable')
        self.report['metrics']['line']['exclusions']=[{'point':'unreachable','approval_id':'REVIEW_TEST'}]
        approvals={'REVIEW_TEST':{'identity':self.report['identity'],'metric':'line','point':'unreachable',
                                 'approved_by':'SYNTHETIC REVIEWER','evidence':'synthetic policy test'}}
        r=assess(self.report,self.baseline,approvals,self.root)['line']
        self.assertEqual((r['raw_total'],r['approved_excluded'],r['effective_total']),(2,1,1))

    def test_vacuous_sva(self):
        self.report['metrics']['sva']['assertions']['p']['antecedent_hits']=0
        with self.assertRaises(ValueError): self.run_assess()

    def test_assertion_failure(self):
        self.report['metrics']['sva']['assertions']['p']['failures']=1
        with self.assertRaises(ValueError): self.run_assess()

    def test_missing_db(self):
        (self.root/'synthetic.db').unlink()
        with self.assertRaises(ValueError): self.run_assess()

    def test_missing_fsm_arc(self):
        self.report['metrics']['fsm']['raw_points']=['state:IDLE']
        self.report['metrics']['fsm']['hit_points']=['state:IDLE']
        self.baseline['points']['fsm']=['state:IDLE']
        with self.assertRaises(ValueError): self.run_assess()

    def test_illegal_functional_bin(self):
        self.baseline['functional_requirements']['p']['legal']=False
        with self.assertRaises(ValueError): self.run_assess()

    def test_missing_rtl_dependency(self):
        self.report['blocked_dependencies']=['DMA_RTL']
        with self.assertRaises(ValueError): self.run_assess()

    def test_hole(self):
        self.report['metrics']['branch']['hit_points']=[]
        with self.assertRaises(ValueError): self.run_assess()

    def test_timeout_despite_all_hits(self):
        self.report['timed_out']=True
        with self.assertRaises(ValueError): self.run_assess()

    def test_undrained_ledger(self):
        self.report['pending_transactions']=1
        with self.assertRaises(ValueError): self.run_assess()

    def test_uvm_error_despite_zero_scoreboard_errors(self):
        self.report['uvm_errors']=1
        with self.assertRaises(ValueError): self.run_assess()

    def test_missing_uvm_summary(self):
        del self.report['uvm_fatals']
        with self.assertRaises(ValueError): self.run_assess()

    def test_one_way_toggle(self):
        self.baseline['points']['toggle']=['rise:bit0']
        self.report['metrics']['toggle']['raw_points']=['rise:bit0']
        self.report['metrics']['toggle']['hit_points']=['rise:bit0']
        with self.assertRaises(ValueError): self.run_assess()

    def test_duplicate_baseline(self):
        self.baseline['points']['line'].append('p')
        with self.assertRaises(ValueError): self.run_assess()

    def test_illegal_bin_hit(self):
        self.report['illegal_bin_hits']=1
        with self.assertRaises(ValueError): self.run_assess()


if __name__ == '__main__':
    unittest.main(verbosity=2)
