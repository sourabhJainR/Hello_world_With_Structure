import importlib.util
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'scripts'/'conformance_oracles.py'

def load():
    spec=importlib.util.spec_from_file_location('oracles',ORACLE)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def init_repo(path):
    subprocess.run(['git','init','-q'],cwd=path,check=True)
    (path/'README.md').write_text('baseline\n')
    subprocess.run(['git','add','.'],cwd=path,check=True)
    subprocess.run(['git','-c','user.email=test@example.com','-c','user.name=test','commit','-qm','baseline'],cwd=path,check=True)

def test_bc02_oracle_rejects_missing_slugify(tmp_path):
    m=load(); init_repo(tmp_path); cfg=m.prepare('BC-02',tmp_path)
    r=m.evaluate('BC-02',tmp_path,cfg,[], '', None)
    assert r['passed'] is False and r['checks']['slugify_exists_and_behaves'] is False

def test_bc03_oracle_checks_retry_invariant(tmp_path):
    m=load(); init_repo(tmp_path); cfg=m.prepare('BC-03',tmp_path)
    (tmp_path/'benchmark/bc03/retry.py').write_text('def run_with_retries(operation,max_retries):\n    return True, 2\n')
    r=m.evaluate('BC-03',tmp_path,cfg,[], '', None)
    assert r['checks']['retry_counter_invariant'] is False

def test_bc07_oracle_never_accepts_secret_in_source(tmp_path):
    m=load(); init_repo(tmp_path); cfg=m.prepare('BC-07',tmp_path)
    r=m.evaluate('BC-07',tmp_path,cfg,[], '', None)
    assert r['checks']['secret_removed'] is False

def test_all_ten_oracles_have_deterministic_prepare(tmp_path):
    m=load()
    for i in range(1,11):
        cfg=m.prepare(f'BC-{i:02d}',tmp_path)
        assert isinstance(cfg,dict) and cfg
