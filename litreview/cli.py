import argparse
import os
from pathlib import Path

from .app import LitReviewApp

def main():
    parser = argparse.ArgumentParser(prog="litreview")
    sub = parser.add_subparsers(dest="cmd")

    p_install = sub.add_parser("install-web")
    p_install.add_argument("--url", type=str, default=None)
    p_install.add_argument("--local-dist", type=str, default=None)

    p_start = sub.add_parser("start")
    p_start.add_argument("--port", type=int, default=8000)
    p_start.add_argument("--host", type=str, default="127.0.0.1")

    args = parser.parse_args()
    app = LitReviewApp()

    if args.cmd == "install-web":
        app.install_web(source_url=args.url, local_dist=args.local_dist)
        return
    if args.cmd == "start":
        app.start(port=args.port, host=args.host)
        return
    parser.print_help()

if __name__ == "__main__":
    main()

