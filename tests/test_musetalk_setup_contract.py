from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MuseTalkSetupContractTests(unittest.TestCase):
    def test_gtx1050ti_setup_is_e_drive_cuda118_and_weight_verified(self):
        text=(ROOT/"scripts"/"SETUP_MUSETALK_GTX1050TI.ps1").read_text(encoding="utf-8-sig")
        for token in (
            'E:\\Krishna-The GOD',
            '[string]$PythonVersion = "3.10.11"',
            'uv-x86_64-pc-windows-msvc.zip',
            'UV_PYTHON_INSTALL_DIR',
            'UV_CACHE_DIR',
            'UV_PYTHON_BIN_DIR',
            'torch==2.0.1',
            'torchvision==0.15.2',
            'torchaudio==2.0.2',
            'https://download.pytorch.org/whl/cu118',
            'mmcv==2.0.1',
            'https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html',
            'mmdet==3.1.0',
            'mmpose==1.1.0',
            'TMElyralab/MuseTalk',
            'stabilityai/sd-vae-ft-mse',
            'openai/whisper-tiny',
            'yzd-v/DWPose',
            'ByteDance/LatentSync',
            'ManyOtherFunctions/face-parse-bisent',
            'musetalk-runtime.json',
            'use_float16',
        ):
            self.assertIn(token,text)
        self.assertIn('PYTHONNOUSERSITE',text)
        self.assertIn('PYTHONUSERBASE',text)
        self.assertIn('HF_HOME',text)
        self.assertIn('HF_HUB_CACHE',text)
        self.assertIn('PIP_CACHE_DIR',text)
        self.assertIn('TORCH_HOME',text)
        self.assertIn('CUDA_CACHE_PATH',text)
        self.assertIn('MPLCONFIGDIR',text)
        self.assertIn('NUMBA_CACHE_DIR',text)
        self.assertIn('KRISHNA E-drive storage guard failed',text)
        self.assertIn('c_drive_guard_passed=$true',text)
        self.assertNotIn('Start-Process -FilePath $installer',text)
        self.assertNotIn('TargetDir=$pythonRoot',text)
        self.assertIn('torch.cuda.is_available()',text)
        self.assertIn('Assert-EPath',text)
        self.assertIn('Get-FileHash -Algorithm SHA256',text)
        self.assertNotIn('python.org/ftp/python',text)
        self.assertNotIn('TargetDir=',text)
        self.assertNotIn('InstallAllUsers=',text)

if __name__=="__main__":
    unittest.main()
