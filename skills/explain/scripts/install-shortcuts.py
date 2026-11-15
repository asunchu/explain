#!/usr/bin/env python3
"""Link the bundled Explain command into a user-owned directory on PATH."""
import argparse
import os
from pathlib import Path
import stat
import sys
import tempfile


def install(bin_dir, dry_run=False, replace=False):
    launcher = Path(__file__).resolve().with_name('explain')
    if not launcher.is_file():
        raise ValueError('The installed skill is missing its explain launcher')
    link = bin_dir.expanduser().absolute() / 'explain'
    old_target = None
    if link.is_symlink():
        old_target = os.readlink(link)
        try:
            current = link.resolve(strict=False)
        except (OSError, RuntimeError):
            current = None
        if current == launcher:
            if not dry_run:
                launcher.chmod(stat.S_IMODE(launcher.stat().st_mode) | stat.S_IXUSR)
            return 'Already linked: ' + str(link)
        if not replace:
            raise ValueError('A different shortcut exists. Use --replace to replace only this symlink: ' + str(link))
    elif link.exists():
        raise ValueError('A file or directory already uses the command name: ' + str(link))
    if dry_run:
        return 'Would link: ' + str(link) + ' -> ' + str(launcher)
    link.parent.mkdir(parents=True, exist_ok=True)
    launcher.chmod(stat.S_IMODE(launcher.stat().st_mode) | stat.S_IXUSR)
    if old_target is None:
        link.symlink_to(launcher)
    else:
        fd, temporary = tempfile.mkstemp(prefix='.explain-link-', dir=link.parent)
        os.close(fd)
        os.unlink(temporary)
        try:
            os.symlink(launcher, temporary)
            if not link.is_symlink() or os.readlink(link) != old_target:
                raise ValueError('The existing shortcut changed. Run setup again.')
            os.replace(temporary, link)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)
    result = 'Linked: ' + str(link) + ' -> ' + str(launcher)
    if old_target is not None:
        result += '\nPrevious target: ' + old_target
    if str(link.parent) not in os.environ.get('PATH', '').split(os.pathsep):
        result += '\nAdd this directory to PATH: ' + str(link.parent)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path.home() / '.local/bin')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--replace', action='store_true', help='Replace a different existing symlink; never replace a regular file or directory')
    args = parser.parse_args()
    try:
        print(install(args.bin_dir, args.dry_run, args.replace))
    except (OSError, RuntimeError, ValueError) as exc:
        print('Explain shortcut: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
