import random
import re
import shutil
import string
import subprocess
import zipfile
import requests
import os
from pathlib import Path
from flask import Flask, abort, jsonify, request

app = Flask(__name__)

CODE_FILE = Path.cwd().joinpath("templates/code.dm")
TEST_DME = Path.cwd().joinpath("templates/test.dme")
HOST = "127.0.0.1"
PORT = 5000
MAIN_PROC = "proc/main()"
BYOND_ROOT = Path.cwd().joinpath("byond")

template = None
test_killed = False

@app.route("/compile", methods=["POST"])
def startCompile():
    if request.method == "POST":
        posted_data = request.get_json()
        if "code_to_compile" in posted_data:
            return jsonify(compileTest(posted_data["code_to_compile"], posted_data["byond_version"]))
        else:
            abort(400)


def loadTemplate(line: str, includeProc=True):
    with open(CODE_FILE) as filein:
        template = string.Template(filein.read())

    if includeProc:
        line = "\n\t".join(line.splitlines())
        d = {"proc": MAIN_PROC, "code": f"{line}\n"}
    else:
        d = {"proc": line, "code": ""}

    return template.substitute(d)


def randomString(stringLength=24):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(stringLength))


def checkVersions(version: str):
    return os.path.exists(f"{BYOND_ROOT}/{version}")


def buildVersion(version: str):
    version_parts = version.split(".")
    byond_major = version_parts[0]
    byond_minor = version_parts[1]

    # Check if the version is already built
    if checkVersions(version=version):
        return
    else:
        print(f"Attempting to download version: {version}")
        byond_path = f"{BYOND_ROOT}/{version}"
        file_name = f"{version}_byond_linux.zip"
        download_path = f"/tmp/{file_name}"
        url = f"https://www.byond.com/download/build/{byond_major}/{file_name}"

        r = requests.get(url)
        with open(download_path, "wb") as outfile:
            outfile.write(r.content)

        with zipfile.ZipFile(download_path, "r") as zip_ref:
            zip_ref.extractall("/tmp")

        shutil.move("/tmp/byond", byond_path)
        os.system(f"chmod -R 770 {byond_path}/bin")
        os.remove(download_path)


def compileTest(codeText: str, version: str):
    buildVersion(version=version)

    randomDir = Path.cwd().joinpath(randomString())
    randomDir.mkdir()
    shutil.copyfile(TEST_DME, randomDir.joinpath("test.dme"))
    print(randomDir.joinpath("test.dme"))
    with open(randomDir.joinpath("code.dm"), "a") as fc:
        if MAIN_PROC not in codeText:
            fc.write(loadTemplate(codeText))
        else:
            fc.write(loadTemplate(codeText, False))

    proc = subprocess.Popen(
        [
            "/bin/bash",
            f"{Path.cwd()}/compile.sh",
            randomDir,
            f"{BYOND_ROOT}/{version}"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        compile_log, run_log = proc.communicate(
            timeout=30
        )  # A bit hacky, but provides exceptionally clean results. The main output will be captured as the compile_log while the "error" output is captured as run_log
        test_killed = False
    except subprocess.TimeoutExpired:
        proc.kill()
        compile_log, run_log = proc.communicate()
        test_killed = True

    compile_log = compile_log.decode("utf-8")
    run_log = run_log.decode("utf-8")
    run_log = re.sub(
        r"The BYOND hub reports that port \d* is not reachable.", "", run_log
    )  # remove the network error message
    compile_log = (compile_log[:1200] + "...") if len(compile_log) > 1200 else compile_log
    run_log = (run_log[:1200] + "...") if len(run_log) > 1200 else run_log

    shutil.rmtree(randomDir)

    if f"Unable to find image 'test:{version}' locally" in run_log:
        results = {"build_error": True, "exception": run_log}
    else:
        results = {"compile_log": compile_log, "run_log": run_log, "timeout": test_killed}

    return results


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
