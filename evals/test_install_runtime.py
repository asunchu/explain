"""Check model integrity, media validation, and fail-before-ready behavior offline."""
from array import array
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_runtime", ROOT / "scripts/install_runtime.py")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)

    def record(self, data):
        return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def test_verified_cache_is_copied_without_network_or_a_shared_symlink(self):
        cache = self.base / "cache"
        cache.mkdir()
        cached = cache / "kokoro-v1.0.onnx"
        cached.write_bytes(b"verified model")
        destination = self.base / "runtime/models" / cached.name
        with patch.object(runtime, "urlopen", side_effect=AssertionError("Unexpected network")):
            result = runtime._prepare_model(destination, self.record(cached.read_bytes()), cache)
        self.assertEqual(destination.read_bytes(), b"verified model")
        self.assertEqual(result["sha256"], self.record(b"verified model")["sha256"])
        self.assertFalse(destination.is_symlink())
        cached.write_bytes(b"changed cache")
        self.assertEqual(destination.read_bytes(), b"verified model")

    def test_failed_download_keeps_the_previous_destination_and_removes_temporary_files(self):
        destination = self.base / "models/voices-v1.0.bin"
        destination.parent.mkdir()
        destination.write_bytes(b"preserve previous file")
        with patch.object(runtime, "urlopen", return_value=io.BytesIO(b"bad bytes")):
            with self.assertRaisesRegex(runtime.RuntimeInstallError, "byte count or SHA-256"):
                runtime._prepare_model(destination, self.record(b"expected model"), None)
        self.assertEqual(destination.read_bytes(), b"preserve previous file")
        self.assertEqual(list(destination.parent.iterdir()), [destination])

    def test_successful_download_becomes_visible_only_after_checksum_validation(self):
        destination = self.base / "models/voices-v1.0.bin"
        data = b"expected model"
        with patch.object(runtime, "urlopen", return_value=io.BytesIO(data)) as download:
            result = runtime._prepare_model(destination, self.record(data), None)
        self.assertEqual(destination.read_bytes(), data)
        self.assertEqual(result["source"], runtime.MODEL_RELEASE + destination.name)
        self.assertTrue(download.call_args.args[0].full_url.startswith(runtime.MODEL_RELEASE))
        self.assertEqual(list(destination.parent.iterdir()), [destination])

    def test_oversized_model_download_is_rejected(self):
        destination = self.base / "models/voices-v1.0.bin"
        with patch.object(runtime, "urlopen", return_value=io.BytesIO(b"too many bytes")):
            with self.assertRaisesRegex(runtime.RuntimeInstallError, "too large"):
                runtime._prepare_model(destination, self.record(b"short"), None)
        self.assertFalse(destination.exists())
        self.assertEqual(list(destination.parent.iterdir()), [])

    def write_wav(self, name, value):
        path = self.base / name
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            output.writeframes(array("h", [value] * 24000).tobytes())
        return path

    def test_wav_inspection_distinguishes_valid_audio_from_silence(self):
        report = runtime._inspect_wav(self.write_wav("audible.wav", 1000))
        self.assertEqual(report["sampleRate"], 24000)
        self.assertEqual(report["durationSeconds"], 1)
        self.assertFalse(report["listeningAudition"])
        self.assertGreater(report["rms"], 0)
        with self.assertRaisesRegex(runtime.RuntimeInstallError, "silent"):
            runtime._inspect_wav(self.write_wav("silent.wav", 0))

    def test_video_without_aac_narration_fails_before_decode(self):
        probe = {"streams": [{"codec_type": "video", "codec_name": "h264",
                              "width": 320, "height": 180}], "format": {"duration": "1.0"}}
        tools = {"paths": {"ffprobe": "ffprobe", "ffmpeg": "ffmpeg"}}
        with patch.object(runtime, "_run", return_value=json.dumps(probe)) as command:
            with self.assertRaisesRegex(runtime.RuntimeInstallError, "AAC narration"):
                runtime._inspect_video(self.base / "sample.mp4", tools, {})
        self.assertEqual(command.call_count, 1)

    def test_ready_marker_cannot_hide_a_missing_runtime_file(self):
        folder = self.base / "runtime"
        folder.mkdir()
        hashes = {"video/package-lock.json": self.record(b"lock")["sha256"]}
        (folder / "ready.json").write_text(json.dumps(
            {"schema": runtime.SCHEMA, "id": "pinned", "hashes": hashes}))
        with self.assertRaisesRegex(runtime.RuntimeInstallError, "missing or has changed"):
            runtime._validate_ready(folder, "pinned", hashes, {}, {})

    def test_manifest_content_changes_the_runtime_identity(self):
        repo = self.base / "repo"
        for relative in runtime.INPUTS.values():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("pinned input")
        tools = {"platform": {"system": "test", "machine": "test"}, "versions": {}}
        before, _ = runtime._identity(repo, tools)
        (repo / runtime.INPUTS["video/package-lock.json"]).write_text("changed lock")
        after, _ = runtime._identity(repo, tools)
        self.assertNotEqual(before, after)

    def test_install_failure_never_writes_a_ready_marker(self):
        tools = {"paths": {"npm": "npm", "python": "python"},
                 "platform": {"system": "test", "machine": "test"}, "versions": {}}
        with patch.object(runtime, "_host_tools", return_value=tools), \
                patch.object(runtime, "_run", side_effect=runtime.RuntimeInstallError("npm failed")):
            with self.assertRaisesRegex(runtime.RuntimeInstallError, "npm failed"):
                runtime.prepare_runtime(ROOT, self.base / "runtimes")
        self.assertEqual(list((self.base / "runtimes").rglob("ready.json")), [])


if __name__ == "__main__":
    unittest.main()
