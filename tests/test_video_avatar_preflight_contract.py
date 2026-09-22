from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]


class VideoAvatarPreflightContractTests(unittest.TestCase):
    def test_hardware_preflight_detects_gpu_cuda_ffmpeg_python_and_e_drive(self):
        text=(ROOT/"scripts"/"CHECK_VIDEO_AVATAR_HARDWARE.ps1").read_text(encoding="utf-8-sig")
        for token in (
            "nvidia-smi","memory.total","CUDA Version","nvcc","ffmpeg","Python 3.10",
            "Get-PSDrive -Name E","video-avatar-hardware.json","musetalk","liveportrait",
            "upstream_tested_floor_vram_gb=4","echomimic_v3","wan_animate_2",
        ):
            self.assertIn(token,text)
        self.assertIn('E:\\Krishna-The GOD',text)
        self.assertIn('storage="E-only"',text)
        self.assertIn('python-managed',text)
        self.assertIn('tools\\avatar-video\\envs\\musetalk\\Scripts\\python.exe',text)
        self.assertNotIn('C:\\Python310\\python.exe',text)
        self.assertNotIn("Invoke-WebRequest",text)
        self.assertNotIn("huggingface-cli download",text)


if __name__=="__main__":
    unittest.main()
