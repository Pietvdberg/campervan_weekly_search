"""Extract one checksum-verified Actions ZIP, preserving hidden history files.

The official action handles authenticated download and SHA-256 validation first.
Only ZIP artifacts produced by this repository's upload steps are supported.
"""
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from zipfile import ZipFile

MAX_BYTES = 256 * 1024 * 1024
MAX_ENTRIES = 10000


def extract(directory, destination):
    archives = list(Path(directory).iterdir())
    if len(archives) != 1 or not archives[0].is_file() or archives[0].is_symlink():
        raise ValueError('Expected exactly one downloaded ZIP artifact')
    root = Path(destination).expanduser().resolve()
    if '\n' in str(root) or '\r' in str(root):
        raise ValueError('Invalid destination directory')
    with ZipFile(archives[0]) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES or sum(info.file_size for info in entries) > MAX_BYTES:
            raise ValueError('Artifact exceeds extraction limits')
        targets = []
        seen = set()
        # Validate the entire directory before writing any archive member.
        for info in entries:
            name = PurePosixPath(info.filename)
            mode = stat.S_IFMT(info.external_attr >> 16)
            if (not name.parts or name.is_absolute() or '..' in name.parts
                    or '\\' in info.filename or ':' in info.filename
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR) or info.flag_bits & 1):
                raise ValueError('Unsafe artifact member')
            target = root.joinpath(*name.parts)
            if target in seen or not target.resolve().is_relative_to(root):
                raise ValueError('Conflicting or unsafe artifact path')
            if any(part.is_symlink() for part in (target, *target.parents) if part.is_relative_to(root)):
                raise ValueError('Artifact extraction cannot traverse symlinks')
            seen.add(target)
            targets.append((info, target))
        files = {target for info, target in targets if not info.is_dir()}
        if any(parent in files for _, target in targets for parent in target.parents):
            raise ValueError('Artifact file conflicts with a parent directory')
        root.mkdir(parents=True, exist_ok=True)
        written = 0
        for info, target in targets:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                    temporary = Path(output.name)
                    with archive.open(info) as source:
                        while block := source.read(65536):
                            written += len(block)
                            if written > MAX_BYTES:
                                raise ValueError('Artifact exceeds extraction limits')
                            output.write(block)
                temporary.replace(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    return root


if __name__ == '__main__':
    restored = extract(os.environ['ARTIFACT_ARCHIVE_DIRECTORY'], os.environ['ARTIFACT_DESTINATION'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('download-path=' + str(restored) + '\n')
    print('Extracted verified artifact to', restored)
