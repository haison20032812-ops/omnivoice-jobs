import argparse
import json
import subprocess
from datetime import datetime
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
    return subprocess.run([git, *args], cwd=REPO, check=True)


def main():
    parser = argparse.ArgumentParser(description="Submit an OmniVoice job for the Colab worker.")
    parser.add_argument("--job-id", required=True, help="Unique job id, for example job-004.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument(
        "--voice-sample",
        default="/content/drive/MyDrive/OmniVoiceRemote/inputs/sample.wav",
        help="Colab path to the reference voice sample.",
    )
    parser.add_argument(
        "--output",
        help="Colab output path. Defaults to OmniVoiceRemote/outputs/<job-id>.wav.",
    )
    parser.add_argument("--ref-text", default="", help="Optional transcript of the reference audio.")
    args = parser.parse_args()

    output = args.output or f"/content/drive/MyDrive/OmniVoiceRemote/outputs/{args.job_id}.wav"
    job = {
        "job_id": args.job_id,
        "status": "pending",
        "text": args.text,
        "voice_sample_path": args.voice_sample,
        "ref_text": args.ref_text,
        "output_path": output,
        "created_at": datetime.now().isoformat(),
    }

    pending = REPO / "jobs" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    job_path = pending / f"{args.job_id}.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    run_git(["pull", "--rebase"])
    run_git(["add", str(job_path.relative_to(REPO))])
    run_git(["commit", "-m", f"Add {args.job_id}"])
    run_git(["push"])
    print(f"Submitted {args.job_id}")
    print(f"Expected output: {output}")


if __name__ == "__main__":
    main()
