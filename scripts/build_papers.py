"""Build drafts in isolated directories; optionally refresh tracked draft PDFs."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors='replace')
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-pdfs', action='store_true')
    args = parser.parse_args()
    version = run(['pdflatex', '--version'], ROOT)
    tex_args = ['--disable-installer'] if 'MiKTeX' in version else []
    for kind in ('Conference', 'Journal'):
        source = ROOT / f'Research_Paper_{kind}'
        output = ROOT / '.deployment/research' / kind.lower()
        output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'main.tex', output / 'main.tex')
        for directory in ('figures', 'bibliography'):
            shutil.copytree(source / directory, output / directory, dirs_exist_ok=True)
        command = ['pdflatex', *tex_args, '-interaction=nonstopmode', '-halt-on-error', 'main.tex']
        run(command, output)
        run(['bibtex', 'main'], output)
        run(command, output)
        log = run(command, output)
        if 'There were undefined references' in log or 'There were undefined citations' in log:
            raise RuntimeError(f'{kind} still contains unresolved references; inspect {output}/main.log')
        if args.refresh_pdfs:
            shutil.copy2(output / 'main.pdf', source / 'main.pdf')
        print(f'{kind} draft built with audit notice: {output / "main.pdf"}', flush=True)


if __name__ == '__main__':
    main()
