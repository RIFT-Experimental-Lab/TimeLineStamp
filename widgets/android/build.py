"""Build the standalone Android widget using the official SDK and a private signing key."""
from pathlib import Path
import argparse
import hashlib
import os
import secrets
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parents[2]


def run(arguments, cwd=ROOT):
    subprocess.run([str(value) for value in arguments], cwd=cwd, check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,default=WORKSPACE/'local/tools/android-sdk')
    parser.add_argument('--jdk',type=Path,default=Path.home()/'Library/Java/JavaVirtualMachines/corretto-17.0.12/Contents/Home')
    parser.add_argument('--output',type=Path,default=WORKSPACE/'local/packages/TimeLineStamp-widget-android-0.2.1.apk')
    parser.add_argument('--private-dir',type=Path,default=WORKSPACE/'local/keys')
    parser.add_argument('--build-dir',type=Path,default=WORKSPACE/'local/build/widget-android')
    args=parser.parse_args()
    sdk=args.sdk.resolve(); tools=sdk/'build-tools/35.0.0'; platform=sdk/'platforms/android-35/android.jar'
    jdk=args.jdk.resolve(); build=args.build_dir.resolve()
    for path in (platform,tools/'aapt2',tools/'lib/d8.jar',tools/'lib/apksigner.jar',jdk/'bin/javac'):
        if not path.exists(): parser.error('Missing SDK/JDK component: '+str(path))
    # Clear only this build's known subdirectories, never the SDK or signing material.
    build.mkdir(parents=True,exist_ok=True)
    for name in ('generated','classes','dex'):
        directory=build/name
        if directory.exists(): shutil.rmtree(directory)
        directory.mkdir()
    run([tools/'aapt2','compile','--dir','src/main/res','-o',build/'resources.zip'])
    run([tools/'aapt2','link','-o',build/'resources.apk','--manifest','src/main/AndroidManifest.xml',
         '-I',platform,'--java',build/'generated','--min-sdk-version','26','--target-sdk-version','35',
         '--version-code','3','--version-name','0.2.1','-R',build/'resources.zip','--auto-add-overlay'])
    sources=sorted((ROOT/'src/main/java').rglob('*.java'))+sorted((build/'generated').rglob('*.java'))
    run([jdk/'bin/javac','--release','8','-encoding','UTF-8','-classpath',platform,'-d',build/'classes',*sources])
    classes=sorted((build/'classes').rglob('*.class'))
    run([jdk/'bin/java','-cp',tools/'lib/d8.jar','com.android.tools.r8.D8','--min-api','26','--lib',platform,'--output',build/'dex',*classes])
    unsigned=build/'unsigned.apk'
    shutil.copyfile(build/'resources.apk',unsigned)
    with zipfile.ZipFile(unsigned,'a',compression=zipfile.ZIP_DEFLATED) as archive:
        for dex in sorted((build/'dex').glob('*.dex')): archive.write(dex,dex.name)
    run([tools/'zipalign','-f','4',unsigned,build/'aligned.apk'])
    private=args.private_dir.resolve(); private.mkdir(parents=True,exist_ok=True)
    key=private/'widget-release.p12'; password=private/'widget-signing.password'
    if not key.exists():
        if not password.exists():
            with password.open('x') as stream: stream.write(secrets.token_hex(32)+'\n')
            password.chmod(0o600)
        run([jdk/'bin/keytool','-genkeypair','-keystore',key,'-storetype','PKCS12','-alias','rift-widget',
             '-keyalg','RSA','-keysize','3072','-validity','36500','-dname','CN=RIFT Experimental Lab,O=RIFT,C=ZZ',
             '-storepass:file',password,'-keypass:file',password])
        key.chmod(0o600)
    if not password.exists(): parser.error('Signing password is missing; preserve the existing release key')
    output=args.output.resolve(); output.parent.mkdir(parents=True,exist_ok=True)
    run([jdk/'bin/java','-jar',tools/'lib/apksigner.jar','sign','--ks',key,'--ks-key-alias','rift-widget',
         '--ks-pass','file:'+str(password),'--v4-signing-enabled','false',
         '--out',output,build/'aligned.apk'])
    run([jdk/'bin/java','-jar',tools/'lib/apksigner.jar','verify','--verbose','--print-certs',output])
    output.with_suffix('.apk.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
    print('Built '+output.name+f' ({output.stat().st_size} bytes)')


if __name__=='__main__': main()
