from sec_cyber_timing.config import ROOT, load_config
from sec_cyber_timing.sec import SecClient


def main() -> None:
    config = load_config()
    sec_config = config["sec"]
    client = SecClient.from_env(
        max_requests_per_second=float(sec_config["max_requests_per_second"])
    )
    destination = ROOT / "data" / "raw" / "sec" / "submissions.zip"
    client.download(sec_config["submissions_bulk_url"], destination)
    print(destination)


if __name__ == "__main__":
    main()
