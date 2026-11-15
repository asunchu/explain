"""Show the local toolchain selected by the Explain installer."""
import argparse
import json
import os
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')
    receipt = state / 'explain/toolchain.json'
    try:
        data = json.loads(receipt.read_text())
        runtime = data.get('runtime')
        if not isinstance(runtime, dict):
            raise ValueError('The media tools are not configured. Run the full installer.')
        required = [Path(runtime[key]) for key in ('root', 'python', 'models', 'browser', 'marker')]
        required += [Path(runtime['models']) / name for name in ('kokoro-v1.0.onnx', 'voices-v1.0.bin')]
        required += [Path(runtime[key]) / 'node_modules' for key in ('video', 'diagrams')]
        missing = [str(path) for path in required if not path.exists()]
        result = {'configured': not missing, 'receipt': str(receipt), 'skill': data['skill'],
                  'runtime': runtime, 'missing': missing,
                  'scope': 'Configured paths and file presence; the installer performs synthesis and rendering checks.'}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print('Explain tools: ' + ('configured' if not missing else 'missing files'))
            print('Runtime: ' + runtime['root'])
            print('Python: ' + runtime['python'])
            print('Remotion modules: ' + str(Path(runtime['video']) / 'node_modules'))
            print('Speech models: ' + runtime['models'])
            print('Browser: ' + runtime['browser'])
            for path in missing:
                print('Missing: ' + path)
        return 1 if missing else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Explain tools: ' + str(exc))
        return 1
