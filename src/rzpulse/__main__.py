import argparse


def main():
    parser = argparse.ArgumentParser(description="RZPulse — read-only Razorpay terminal explorer")
    parser.add_argument("--version", action="version", version="RZPulse 0.1.0")
    parser.parse_args()
    try:
        from rzpulse.app import RZPulse
    except ModuleNotFoundError as exc:
        if exc.name in {"rich", "textual", "httpx", "pydantic", "dotenv"}:
            parser.exit(2, "RZPulse dependencies are missing. Run: pip install -e .\n")
        raise
    RZPulse().run()


if __name__ == "__main__":
    main()
