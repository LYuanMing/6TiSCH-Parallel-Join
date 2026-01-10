import os
import subprocess
import sys
#============================ helpers =========================================

#============================ tests ===========================================

def test_runSim():
    wd = os.getcwd()
    if wd.endswith("tests"):
        os.chdir("../bin/")
    else:
        os.chdir("bin/")
    rc = subprocess.call(
        [sys.executable, 'runSim.py'],
        shell=True,
    )
    os.chdir(wd)
    assert rc==0
