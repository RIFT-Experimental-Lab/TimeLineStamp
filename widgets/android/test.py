"""Run the widget's JVM record contract tests against the collector's own output."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
REPOSITORY = ROOT.parents[1]
WORKSPACE = REPOSITORY.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk', type=Path, default=Path.home() / 'Library/Java/JavaVirtualMachines/corretto-17.0.12/Contents/Home')
    args = parser.parse_args()
    jar = WORKSPACE / 'local/tools/widget-tests/json-20250517.jar'
    jar.parent.mkdir(parents=True, exist_ok=True)
    if not jar.exists():
        urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar', jar)
    if hashlib.sha256(jar.read_bytes()).hexdigest() != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':
        raise SystemExit('Test dependency checksum mismatch')
    out = WORKSPACE / 'local/build/widget-tests'
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(args.jdk / 'bin/javac'), '--release', '8', '-encoding', 'UTF-8', '-cp', str(jar), '-d', str(out),
                    str(ROOT / 'src/main/java/lab/rift/timelinestamp/widget/Reading.java'), str(ROOT / 'tests/ReadingTest.java')], check=True)
    sys.path.insert(0, str(REPOSITORY))
    from timelinestamp import display_coefficient
    subprocess.run([str(args.jdk / 'bin/java'), '-cp', str(out) + ':' + str(jar), 'lab.rift.timelinestamp.widget.ReadingTest',
                    str(REPOSITORY / 'docs/data/status.json'), display_coefficient('f' * 64)], check=True)


if __name__ == '__main__':
    main()
