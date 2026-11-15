"""Prepare the local media tools before the installer changes agent configuration.

Each ready directory is a versioned dependency snapshot. Verification output goes
beside those snapshots, so checking an active runtime does not replace its files.
This module does not install system tools, edit a shell profile, or use paid APIs.
"""
from __future__ import annotations

from array import array
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Iterator
from urllib.request import Request, urlopen
import uuid
import wave


SCHEMA = 1
RECIPE = "explain-media-runtime-1"
MODEL_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
INPUTS = {
    "video/package.json": "examples/explain-video/package.json",
    "video/package-lock.json": "examples/explain-video/package-lock.json",
    "requirements.lock.txt": "examples/explain-video/requirements.lock.txt",
    "model-checksums.json": "examples/explain-video/model-checksums.json",
    "diagrams/package.json": "skills/explain/scripts/diagrams/package.json",
    "diagrams/package-lock.json": "skills/explain/scripts/diagrams/package-lock.json",
    "diagrams/render.mjs": "skills/explain/scripts/diagrams/render.mjs",
    "diagrams/worker.mjs": "skills/explain/scripts/diagrams/worker.mjs",
}

NARRATE_SMOKE = r'''from pathlib import Path
import os, shutil, sys, tempfile
import espeakng_loader
import numpy as np
import soundfile as sf

# The native phonemizer needs a short data path on macOS.
with tempfile.TemporaryDirectory(prefix='explain-tts-') as temporary:
    data = Path(temporary) / 'espeak-ng-data'
    shutil.copytree(espeakng_loader.get_data_path(), data)
    os.environ['ESPEAK_DATA_PATH'] = str(data)
    os.environ['PHONEMIZER_ESPEAK_DATA_PATH'] = str(data)
    os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = espeakng_loader.get_library_path()
    from kokoro_onnx import Kokoro
    from kokoro_onnx.config import EspeakConfig
    models, destination = Path(sys.argv[1]), Path(sys.argv[2])
    engine = Kokoro(str(models / 'kokoro-v1.0.onnx'),
                    str(models / 'voices-v1.0.bin'),
                    espeak_config=EspeakConfig(data_path=str(data)))
    samples, rate = engine.create('This sentence confirms local narration.',
                                  voice='af_heart', speed=1.02, lang='en-us')
    samples = np.asarray(samples)
    if rate != 24000 or samples.ndim != 1 or not np.isfinite(samples).all():
        raise RuntimeError('Kokoro returned invalid audio.')
    sf.write(destination, samples, rate, subtype='PCM_16')
'''

REMOTION_ENTRY = r'''import React from 'react';
import {registerRoot, Composition, AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
const Clip = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{backgroundColor:'#102035', color:'white', fontFamily:'sans-serif',
      alignItems:'center', justifyContent:'center', fontSize:24}}>
    <div style={{transform:`translateX(${frame - 12}px)`}}>Explain is ready</div>
    <Audio src={staticFile('narration.wav')}/>
  </AbsoluteFill>;
};
registerRoot(() => <Composition id="ExplainRuntimeSmoke" component={Clip}
  width={320} height={180} fps={24} durationInFrames={24}/>);
'''

RENDER_SMOKE = r'''import {bundle} from '@remotion/bundler';
import {ensureBrowser, selectComposition, renderMedia} from '@remotion/renderer';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const output = path.resolve(process.argv[2]);
const browser = await ensureBrowser({chromeMode:'headless-shell', logLevel:'warn',
  ...(process.argv[3] ? {browserExecutable:process.argv[3]} : {})});
if (!browser.path) throw new Error('Remotion did not supply a browser.');
const serveUrl = await bundle({entryPoint:path.join(here,'runtime-smoke.jsx'),
  publicDir:path.join(output,'public'), outDir:path.join(output,'bundle'), enableCaching:false});
const composition = await selectComposition({serveUrl, id:'ExplainRuntimeSmoke',
  browserExecutable:browser.path, chromeMode:'headless-shell', logLevel:'warn'});
await renderMedia({composition, serveUrl, outputLocation:path.join(output,'sample.mp4'),
  codec:'h264', audioCodec:'aac', pixelFormat:'yuv420p', concurrency:1, crf:28,
  browserExecutable:browser.path, chromeMode:'headless-shell', logLevel:'warn'});
await writeFile(path.join(output,'browser.json'), JSON.stringify(browser));
'''

GENERATED = {
    "narrate-smoke.py": NARRATE_SMOKE,
    "video/runtime-smoke.jsx": REMOTION_ENTRY,
    "video/render-smoke.mjs": RENDER_SMOKE,
}


class RuntimeInstallError(RuntimeError):
    """A prerequisite, download, install, or actual media check failed."""


def _progress(message: str) -> None:
    print("Runtime: " + message, flush=True)


def _run(arguments: list[str], *, cwd: Path | None = None,
         env: dict[str, str] | None = None, timeout: int = 900) -> str:
    try:
        result = subprocess.run(arguments, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeInstallError(f"Could not run {arguments[0]}: {error}") from error
    if result.returncode:
        detail = (result.stdout + "\n" + result.stderr).strip()[-12000:]
        raise RuntimeInstallError(
            f"Command failed ({result.returncode}): {arguments!r}\n{detail}")
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".ready-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _host_tools() -> dict:
    if os.name != "posix":
        raise RuntimeInstallError("The media installer currently supports macOS and Linux.")
    paths = {}
    for name in ("node", "npm", "ffmpeg", "ffprobe"):
        executable = shutil.which(name)
        if not executable:
            raise RuntimeInstallError(f"Install {name} and put it on PATH before installing Explain.")
        # Do not resolve npm's launcher symlink: npm finds its own adjacent files.
        paths[name] = str(Path(executable).absolute())
    versions = {
        "node": _run([paths["node"], "--version"], timeout=20),
        "npm": _run([paths["npm"], "--version"], timeout=20),
        "ffmpeg": _run([paths["ffmpeg"], "-version"], timeout=20).splitlines()[0],
        "ffprobe": _run([paths["ffprobe"], "-version"], timeout=20).splitlines()[0],
    }
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.\d+.*", versions["node"])
    if not match or (int(match.group(1)), int(match.group(2))) < (22, 20):
        raise RuntimeInstallError("Install Node.js 22.20 or newer before installing Explain.")
    candidates = [shutil.which("python3.11"), sys.executable,
                  *(shutil.which(f"python3.{minor}") for minor in (12, 13)),
                  shutil.which("python3")]
    for candidate in dict.fromkeys(value for value in candidates if value):
        try:
            information = json.loads(_run([candidate, "-I", "-c",
                "import json,sys; print(json.dumps({'version':list(sys.version_info[:3]),"
                "'executable':sys.executable}))"], timeout=20))
        except (RuntimeInstallError, ValueError, KeyError):
            continue
        major, minor, _ = information["version"]
        if major == 3 and 11 <= minor <= 13:
            paths["python"] = information["executable"]
            versions["python"] = ".".join(map(str, information["version"]))
            break
    else:
        raise RuntimeInstallError("Install Python 3.11 before installing Explain's media tools.")
    return {"paths": paths, "versions": versions,
            "platform": {"system": platform.system(), "machine": platform.machine()}}


def _identity(repo: Path, tools: dict) -> tuple[str, dict]:
    hashes = {}
    for destination, relative in INPUTS.items():
        source = repo / relative
        if not source.is_file():
            raise RuntimeInstallError(f"The installer source is missing {source}.")
        hashes[destination] = _sha256(source)
    hashes.update({name: hashlib.sha256(value.encode()).hexdigest()
                   for name, value in GENERATED.items()})
    identity = {"recipe": RECIPE, "hashes": hashes, "platform": tools["platform"],
                "versions": tools["versions"]}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return digest[:24], hashes


def _expected_models(path: Path) -> dict:
    expected = _json(path)
    if set(expected) != {"kokoro-v1.0.onnx", "voices-v1.0.bin"}:
        raise RuntimeInstallError("The model checksum manifest must name both Kokoro model files.")
    for name, record in expected.items():
        if (not isinstance(record, dict) or not isinstance(record.get("bytes"), int)
                or isinstance(record.get("bytes"), bool) or record["bytes"] <= 0
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", "")))):
            raise RuntimeInstallError(f"The checksum manifest is invalid for {name}.")
    return expected


def _verified_file(path: Path, expected: dict) -> bool:
    return (path.is_file() and path.stat().st_size == expected["bytes"]
            and _sha256(path) == expected["sha256"])


def _prepare_model(destination: Path, expected: dict, cache: Path | None) -> dict:
    """Copy or download to a temporary file; expose only verified bytes."""
    if _verified_file(destination, expected):
        return {**expected, "source": "existing verified runtime file"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix="." + destination.name + "-",
                                                 dir=destination.parent)
    temporary = Path(temporary_name)
    os.close(descriptor)
    source = MODEL_RELEASE + destination.name
    try:
        cached = cache / destination.name if cache is not None else None
        if cached is not None and _verified_file(cached, expected):
            shutil.copyfile(cached, temporary)
            source = str(cached)
        else:
            if cached is not None and cached.exists():
                _progress(f"Ignoring a model cache file with a mismatched checksum: {cached.name}.")
            _progress(f"Downloading {destination.name} from the official Kokoro release.")
            request = Request(source, headers={"User-Agent": "Explain-local-runtime/1"})
            with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                received = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > expected["bytes"]:
                        raise RuntimeInstallError(f"The download is too large: {destination.name}.")
                    output.write(chunk)
        if not _verified_file(temporary, expected):
            raise RuntimeInstallError(f"Model byte count or SHA-256 failed: {destination.name}.")
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    except (OSError, ValueError) as error:
        raise RuntimeInstallError(f"Could not prepare {destination.name}: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return {**expected, "source": source}


def _requirements(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if not match:
            raise RuntimeInstallError("Use exact package versions in requirements.lock.txt.")
        result[match.group(1)] = match.group(2)
    if not result:
        raise RuntimeInstallError("The Python requirements lock is empty.")
    return result


def _installed_versions(runtime: Path, tools: dict, env: dict[str, str]) -> dict:
    installed = {"host": tools["versions"], "javascript": {}, "python": {}}
    for name in ("video", "diagrams"):
        expected = _json(runtime / name / "package.json").get("dependencies", {})
        script = ("const fs=require('node:fs'),path=require('node:path');"
                  "const names=JSON.parse(process.argv[1]);const result={};"
                  "for(const n of names){result[n]=JSON.parse(fs.readFileSync("
                  "path.join(process.cwd(),'node_modules',n,'package.json'),'utf8')).version;}"
                  "console.log(JSON.stringify(result));")
        actual = json.loads(_run([tools["paths"]["node"], "-e", script,
                                  json.dumps(list(expected))], cwd=runtime / name, env=env))
        if actual != expected:
            raise RuntimeInstallError(f"Installed JavaScript versions differ from {name}/package.json.")
        _run([tools["paths"]["npm"], "ls", "--all", "--json"],
             cwd=runtime / name, env=env)
        installed["javascript"][name] = actual
    expected = _requirements(runtime / "requirements.lock.txt")
    python = str(runtime / ".venv/bin/python")
    actual = json.loads(_run([python, "-I", "-c",
        "import importlib.metadata,json,sys; "
        "print(json.dumps({name:importlib.metadata.version(name) for name in json.loads(sys.argv[1])}))",
        json.dumps(list(expected))], env=env))
    if actual != expected:
        raise RuntimeInstallError("Installed Python versions differ from requirements.lock.txt.")
    _run([python, "-I", "-m", "pip", "--isolated", "check"], env=env)
    installed["python"] = actual
    return installed


def _inspect_wav(path: Path) -> dict:
    try:
        with wave.open(str(path), "rb") as audio:
            rate, channels, width, frames = (audio.getframerate(), audio.getnchannels(),
                                             audio.getsampwidth(), audio.getnframes())
            raw = audio.readframes(frames)
    except (OSError, wave.Error) as error:
        raise RuntimeInstallError(f"Could not inspect generated narration: {error}") from error
    if rate != 24000 or channels != 1 or width != 2 or frames < rate // 2:
        raise RuntimeInstallError("The narration must contain at least half a second of 24 kHz mono PCM audio.")
    if len(raw) != frames * channels * width:
        raise RuntimeInstallError("The generated narration is truncated.")
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max(abs(value) for value in samples) / 32768
    rms = math.sqrt(sum((value / 32768) ** 2 for value in samples) / len(samples))
    if rms < 0.0001 or peak > 1:
        raise RuntimeInstallError("The generated narration is silent or invalid.")
    return {"path": str(path), "sampleRate": rate, "channels": channels,
            "durationSeconds": frames / rate, "peak": peak, "rms": rms,
            "sha256": _sha256(path), "listeningAudition": False}


def _inspect_video(path: Path, tools: dict, env: dict[str, str]) -> dict:
    probe = json.loads(_run([tools["paths"]["ffprobe"], "-v", "error", "-show_streams",
                             "-show_format", "-of", "json", str(path)], env=env))
    videos = [item for item in probe.get("streams", []) if item.get("codec_type") == "video"]
    audios = [item for item in probe.get("streams", []) if item.get("codec_type") == "audio"]
    duration = float(probe.get("format", {}).get("duration", 0))
    if (len(videos) != 1 or videos[0].get("codec_name") != "h264"
            or videos[0].get("width") != 320 or videos[0].get("height") != 180
            or len(audios) != 1 or audios[0].get("codec_name") != "aac"
            or not 0.95 <= duration <= 1.15):
        raise RuntimeInstallError("The Remotion smoke export must contain one second of H.264 video and AAC narration.")
    decoded_audio = path.with_suffix(".decoded-audio.wav")
    _run([tools["paths"]["ffmpeg"], "-v", "error", "-xerror", "-nostdin", "-i", str(path),
          "-map", "0:v:0", "-an", "-f", "null", "-", "-map", "0:a:0", "-vn",
          "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(decoded_audio)], env=env)
    narration = _inspect_wav(decoded_audio)
    return {"path": str(path), "videoCodec": "h264", "audioCodec": "aac",
            "width": 320, "height": 180, "durationSeconds": duration,
            "decodedWithoutErrors": True, "narrationAudio": narration, "sha256": _sha256(path)}


def _run_smokes(runtime: Path, base: Path, tools: dict, env: dict[str, str],
                browser: str | None = None) -> dict:
    verification = base / ".verification" / (runtime.name + "-" + uuid.uuid4().hex[:12])
    (verification / "public").mkdir(parents=True)
    _progress("Rendering a diagram with Pele's restricted worker.")
    source, svg = verification / "diagram.mmd", verification / "diagram.svg"
    source.write_text("flowchart LR\n  A[Input] --> B[Output]\n", encoding="utf-8")
    _run([tools["paths"]["node"], str(runtime / "diagrams/render.mjs"),
          str(source), str(svg)], cwd=runtime / "diagrams", env=env, timeout=30)
    rendered = svg.read_text(encoding="utf-8")
    if "<svg" not in rendered or "Input" not in rendered or "Output" not in rendered:
        raise RuntimeInstallError("The Pele smoke check did not produce the expected diagram.")
    _progress("Synthesizing a sentence locally with Kokoro.")
    audio = verification / "public/narration.wav"
    _run([str(runtime / ".venv/bin/python"), "-I", str(runtime / "narrate-smoke.py"),
          str(runtime / "models"), str(audio)], cwd=runtime, env=env, timeout=300)
    narration = _inspect_wav(audio)
    _progress("Rendering one second of H.264/AAC with Remotion and Chrome Headless Shell.")
    arguments = [tools["paths"]["node"], str(runtime / "video/render-smoke.mjs"), str(verification)]
    if browser:
        arguments.append(browser)
    _run(arguments, cwd=runtime / "video", env=env, timeout=900)
    browser_path = Path(_json(verification / "browser.json")["path"]).resolve()
    if not browser_path.is_file() or not browser_path.is_relative_to(runtime.resolve()):
        raise RuntimeInstallError("Remotion's downloaded browser is missing from the versioned runtime.")
    _progress("Inspecting the media streams and decoding the complete smoke export.")
    video = _inspect_video(verification / "sample.mp4", tools, env)
    result = {"checkedAt": datetime.now(timezone.utc).isoformat(), "passed": True,
              "directory": str(verification),
              "diagram": {"path": str(svg), "sha256": _sha256(svg)},
              "narration": narration, "video": video, "browser": str(browser_path),
              "speechApiCostUsd": 0,
              "scope": "Actual local diagram, speech synthesis, media export, and technical decode; no listening audition."}
    _atomic_json(verification / "verification.json", result)
    return result


def _environment(base: Path) -> dict[str, str]:
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "npm_config_cache": str(base / ".npm-cache"),
                "npm_config_update_notifier": "false", "npm_config_audit": "false",
                "npm_config_fund": "false"})
    return env


@contextmanager
def _installation_lock(base: Path, identifier: str) -> Iterator[None]:
    import fcntl
    directory = base / ".locks"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (identifier + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _validate_ready(runtime: Path, identifier: str, hashes: dict,
                    tools: dict, env: dict[str, str]) -> tuple[dict, dict]:
    marker = _json(runtime / "ready.json")
    if marker.get("schema") != SCHEMA or marker.get("id") != identifier or marker.get("hashes") != hashes:
        raise RuntimeInstallError("The runtime marker does not match the pinned installer inputs.")
    for relative, expected in hashes.items():
        path = runtime / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeInstallError(f"The ready runtime is missing or has changed {relative}.")
    for name, expected in _expected_models(runtime / "model-checksums.json").items():
        if not _verified_file(runtime / "models" / name, expected):
            raise RuntimeInstallError(f"The ready runtime is missing a verified model: {name}.")
    browser = Path(marker.get("browser", ""))
    if not browser.is_file() or not browser.resolve().is_relative_to(runtime.resolve()):
        raise RuntimeInstallError("The ready runtime is missing its Chrome Headless Shell executable.")
    versions = _installed_versions(runtime, tools, env)
    smoke = _run_smokes(runtime, runtime.parent, tools, env, str(browser))
    return versions, smoke


def _result(runtime: Path, identifier: str, hashes: dict, versions: dict,
            smoke: dict, reused: bool) -> dict:
    return {"id": identifier, "root": str(runtime), "path": str(runtime),
            "video": str(runtime / "video"), "diagrams": str(runtime / "diagrams"),
            "venv": str(runtime / ".venv"), "python": str(runtime / ".venv/bin/python"),
            "models": str(runtime / "models"), "browser": smoke["browser"],
            "marker": str(runtime / "ready.json"), "versions": versions,
            "hashes": hashes, "smoke": smoke, "reused": reused}


def prepare_runtime(repo: Path, runtime_base: Path, model_cache: Path | None = None) -> dict:
    """Install and verify the pinned media runtime without changing agent defaults.

    A failed preparation raises RuntimeInstallError and leaves no ready marker.
    The caller must complete this function before changing any active defaults.
    Node.js 22.20+, Python 3.11-3.13, FFmpeg, and ffprobe must already be on PATH.
    """
    repo, base = Path(repo).resolve(), Path(runtime_base).expanduser().resolve()
    cache = Path(model_cache).expanduser().resolve() if model_cache is not None else None
    _progress("Checking Node.js, Python, FFmpeg, and ffprobe.")
    tools = _host_tools()
    identifier, hashes = _identity(repo, tools)
    _requirements(repo / INPUTS["requirements.lock.txt"])
    expected_models = _expected_models(repo / INPUTS["model-checksums.json"])
    base.mkdir(parents=True, exist_ok=True)
    env = _environment(base)
    with _installation_lock(base, identifier):
        canonical = base / identifier
        candidates = [canonical, *sorted(base.glob(identifier + "-repair-*"), reverse=True)]
        for candidate in candidates:
            if candidate.is_symlink():
                continue
            if not (candidate / "ready.json").exists():
                continue
            _progress(f"Rechecking the existing runtime {candidate.name}.")
            try:
                versions, smoke = _validate_ready(candidate, identifier, hashes, tools, env)
            except (RuntimeInstallError, OSError, ValueError, KeyError, TypeError) as error:
                _progress(f"Preserving an unusable runtime: {candidate.name}: {error}")
                continue
            _progress("The existing runtime passed fresh media checks.")
            return _result(candidate, identifier, hashes, versions, smoke, True)
        # Keep ready or foreign directories intact. Create the venv at its final
        # path because moving a venv breaks executable paths in pip launchers.
        runtime = canonical
        if canonical.exists() or canonical.is_symlink():
            runtime = base / (identifier + "-repair-" + uuid.uuid4().hex[:12])
        runtime.mkdir(mode=0o700, parents=True, exist_ok=False)
        for relative, source in INPUTS.items():
            destination = runtime / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / source, destination)
        for relative, source in GENERATED.items():
            destination = runtime / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(source, encoding="utf-8")
        _progress("Installing locked Remotion and React packages with npm ci.")
        _run([tools["paths"]["npm"], "ci", "--no-audit", "--no-fund"],
             cwd=runtime / "video", env=env)
        _progress("Installing locked Pele packages with lifecycle scripts disabled.")
        _run([tools["paths"]["npm"], "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
             cwd=runtime / "diagrams", env=env)
        _progress("Creating the versioned Python environment.")
        _run([tools["paths"]["python"], "-I", "-m", "venv", "--copies", str(runtime / ".venv")], env=env)
        _progress("Installing the pinned local narration packages.")
        _run([str(runtime / ".venv/bin/python"), "-I", "-m", "pip", "--isolated",
              "--disable-pip-version-check", "--cache-dir", str(base / ".pip-cache"),
              "install", "--no-input", "--requirement", str(runtime / "requirements.lock.txt")], env=env)
        _progress("Checking the Kokoro model byte counts and SHA-256 hashes.")
        models = {name: _prepare_model(runtime / "models" / name, record, cache)
                  for name, record in expected_models.items()}
        _progress("Checking installed JavaScript and Python package versions.")
        versions = _installed_versions(runtime, tools, env)
        smoke = _run_smokes(runtime, base, tools, env)
        marker = {"schema": SCHEMA, "recipe": RECIPE, "id": identifier,
                  "hashes": hashes, "versions": versions, "models": models,
                  "browser": smoke["browser"], "smoke": smoke,
                  "readyAt": datetime.now(timezone.utc).isoformat()}
        _atomic_json(runtime / "ready.json", marker)
        _progress(f"The media runtime is ready: {runtime}.")
        return _result(runtime, identifier, hashes, versions, smoke, False)
