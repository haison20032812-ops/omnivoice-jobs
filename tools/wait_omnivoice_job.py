import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def find_git():
    candidates = [
        "git",
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
    ]
    for candidate in candidates:
        try:
            subprocess.run(
                [candidate, "--version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return candidate
        except Exception:
            pass
    raise RuntimeError("Cannot find git. Install Git or add it to PATH.")


def run_git(args):
    git = find_git()
    return subprocess.run([git, *args], cwd=REPO, check=True, stdout=subprocess.DEVNULL)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def map_colab_drive_path(colab_path, local_my_drive):
    prefix = "/content/drive/MyDrive/"
    if not colab_path.startswith(prefix):
        return None
    return Path(local_my_drive) / colab_path[len(prefix):].replace("/", "\\")


def main():
    parser = argparse.ArgumentParser(description="Wait for a Colab OmniVoice job to finish.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--timeout", type=int, default=1800, help="Seconds to wait.")
    parser.add_argument("--interval", type=int, default=20, help="Polling interval in seconds.")
    parser.add_argument(
        "--local-my-drive",
        help="Optional local Google Drive MyDrive folder for copying output, for example G:\\My Drive.",
    )
    parser.add_argument("--copy-to", help="Optional local destination file path.")
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    done_path = REPO / "jobs" / "done" / f"{args.job_id}.json"
    failed_path = REPO / "jobs" / "failed" / f"{args.job_id}.json"

    while time.time() < deadline:
        run_git(["pull", "--rebase"])

        if done_path.exists():
            job = read_json(done_path)
            print(f"Done: {args.job_id}")
            print(f"Colab output: {job.get('output_path')}")

            if args.local_my_drive and args.copy_to:
                source = map_colab_drive_path(job.get("output_path", ""), args.local_my_drive)
                if not source or not source.exists():
                    raise FileNotFoundError(f"Cannot find local synced output: {source}")
                target = Path(args.copy_to)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                print(f"Copied to: {target}")
            return

        if failed_path.exists():
            job = read_json(failed_path)
            raise RuntimeError(f"Failed: {args.job_id}\n{job.get('error')}")

        print(f"Waiting for {args.job_id}...")
        time.sleep(args.interval)

    raise TimeoutError(f"Timed out waiting for {args.job_id}")


if __name__ == "__main__":
    main()
