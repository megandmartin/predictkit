#!/usr/bin/env python3
"""Verify this checkout's local starter archive and run a disposable offline copy."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def verify(archive):
    checks=[]
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        assert len(names)==len(set(names)), 'Duplicate entries'
        for name in names:
            path=PurePosixPath(name)
            assert path.parts[0]=='PredictKit' and not path.is_absolute() and '..' not in path.parts
            assert not any(x in ('.local','.tools','.git','node_modules','target','__pycache__') for x in path.parts)
        manifest=json.loads(z.read('PredictKit/PACKAGE_MANIFEST.json'))
        files=manifest['files']
        assert set(names)=={'PredictKit/'+x for x in files}|{'PredictKit/PACKAGE_MANIFEST.json'}
        for name,record in files.items():
            data=z.read('PredictKit/'+name)
            assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'], name
            assert (ROOT/name).read_bytes()==data, 'Checkout differs: '+name
        checks.append({'name':'exact inventory, source bytes and SHA256 manifest','passed':True,'source_files':len(files)})
        with tempfile.TemporaryDirectory(prefix='predictkit-source-check-') as temporary:
            z.extractall(temporary)
            project=Path(temporary)/'PredictKit'
            for name,command in [('doctor',[sys.executable,'predictkit.py','doctor']),('capabilities',[sys.executable,'predictkit.py','capabilities','frontend']),('rehearsal',[sys.executable,'predictkit.py','rehearse','--out',str(Path(temporary)/'runs')])]:
                result=subprocess.run(command,cwd=project,text=True,capture_output=True,timeout=90)
                assert result.returncode==0, name+': '+result.stderr
                output=json.loads(result.stdout)
                if name=='doctor':assert output['rehearsal_ready']
                elif name=='capabilities':assert output['capability']['id']=='frontend'
                else:assert output['integrity_passed'] and output['artifacts_checked']==11
                checks.append({'name':'fresh extraction '+name,'passed':True})
    return {'kind':'source-package-check','archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
            'archive_bytes':Path(archive).stat().st_size,'checks':checks,
            'boundary':'Offline source/rehearsal check only. No model, wallet, public deployment or participant proof.'}

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.local/releases/PredictKit-Local-Starter.zip'
    print(json.dumps(verify(path),indent=2))
