# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""Command-line entry for Monitor bot Edge."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from monitor_bot_edge import __version__
from monitor_bot_edge.detect import DEFAULT_WEIGHTS, run_detect
from monitor_bot_edge.license import LicenseError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monitor_bot_edge",
        description="Monitor bot Edge — on-prem kindergarten safety vision (YOLO-World).",
    )
    parser.add_argument("--version", action="version", version=f"Monitor bot Edge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    detect = sub.add_parser("detect", help="Run YOLO-World on a video and write annotated MP4 + JSONL events")
    detect.add_argument("--video", required=True, help="Path to an on-site video file")
    detect.add_argument("--keywords", required=True, help='Open-vocab phrases, e.g. "幼兒,跌倒,攀爬" (split on 、，,;)')
    detect.add_argument("--output-dir", default="outputs", help="Directory for annotated MP4 and events JSONL")
    detect.add_argument("--weights", default=None, help=f"YOLO-World weights (default: $YOLO_WEIGHTS or {DEFAULT_WEIGHTS})")
    detect.add_argument("--conf", type=float, default=0.25, help="Detection confidence")
    detect.add_argument("--alone-s", type=float, default=8.0, dest="alone_s")
    detect.add_argument("--crowd-count", type=int, default=4, dest="crowd_count")
    detect.add_argument("--fall-hold-s", type=float, default=0.4, dest="fall_hold_s")
    detect.add_argument("--climb-window-s", type=float, default=0.8, dest="climb_window_s")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "detect":
        try:
            mp4, jsonl = run_detect(
                video=args.video,
                keywords=args.keywords,
                output_dir=args.output_dir,
                weights=args.weights,
                conf=args.conf,
                fall_hold_s=args.fall_hold_s,
                climb_window_s=args.climb_window_s,
                alone_s=args.alone_s,
                crowd_count=args.crowd_count,
            )
        except LicenseError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"annotated video: {mp4}")
        print(f"events jsonl:    {jsonl}")
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
