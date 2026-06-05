from __future__ import annotations

import argparse
import json
from pathlib import Path

from idea_to_research.pipeline import (
    _override_route,
    build_idea_brief,
    build_research_prompt,
    build_route_decision,
    continue_session,
    export_session,
    run_pipeline,
    start_session,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Align a vague idea, decide the route, then enter the matching research layer."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    align = subparsers.add_parser("align", help="Generate a route decision from a natural-language idea.")
    align.add_argument("request", help="The user's natural-language idea.")

    brief = subparsers.add_parser("brief", help="Generate an idea brief from a natural-language request.")
    brief.add_argument("request", help="The user's natural-language idea.")

    prompt = subparsers.add_parser("prompt", help="Generate a route-specific research prompt.")
    prompt.add_argument("request", help="The user's natural-language idea.")
    prompt.add_argument(
        "--route",
        choices=["github-build", "product-research", "social-research"],
        help="Optional route override.",
    )

    run = subparsers.add_parser("run", help="Run the aligned idea -> research pipeline.")
    run.add_argument("request", help="The user's natural-language idea.")
    run.add_argument("--slug", help="Optional custom output directory slug.")
    run.add_argument(
        "--route",
        choices=["github-build", "product-research", "social-research"],
        help="Optional route override.",
    )
    run.add_argument(
        "--discover-count",
        type=int,
        default=8,
        help="How many repositories to fetch for each generated query.",
    )
    run.add_argument(
        "--harvest-top",
        type=int,
        default=4,
        help="How many ranked repositories to harvest deeply on GitHub route.",
    )
    run.add_argument(
        "--output-root",
        help="Optional output root. Defaults to workspace task_draft/consensus.",
    )

    session_start = subparsers.add_parser("session-start", help="Start a multi-turn idea alignment session.")
    session_start.add_argument("request", help="The user's natural-language idea.")
    session_start.add_argument("--slug", help="Optional custom session slug.")
    session_start.add_argument(
        "--output-root",
        help="Optional session root. Defaults to workspace task_draft/idea_sessions.",
    )

    session_continue = subparsers.add_parser("session-continue", help="Continue an existing alignment session.")
    session_continue.add_argument("session_dir", help="Session directory created by session-start.")
    session_continue.add_argument("reply", help="The user's follow-up reply.")

    session_export = subparsers.add_parser("session-export", help="Export a research-ready session into a formal package.")
    session_export.add_argument("session_dir", help="Session directory created by session-start.")
    session_export.add_argument("--slug", help="Optional custom output slug.")
    session_export.add_argument(
        "--output-root",
        help="Optional output root. Defaults to workspace task_draft/consensus.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "align":
        route_decision = build_route_decision(args.request)
        print(route_decision.markdown)
        return

    if args.command == "brief":
        brief = build_idea_brief(args.request)
        print(brief.markdown)
        return

    if args.command == "prompt":
        route_decision = build_route_decision(args.request)
        if args.route:
            route_decision = _override_route(route_decision, args.route)
        brief = build_idea_brief(args.request)
        prompt = build_research_prompt(brief, route_decision)
        print(prompt.markdown)
        return

    if args.command == "run":
        result = run_pipeline(
            request=args.request,
            slug=args.slug,
            route_override=args.route,
            discover_count=args.discover_count,
            harvest_top=args.harvest_top,
            output_root=Path(args.output_root).expanduser() if args.output_root else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "session-start":
        result = start_session(
            request=args.request,
            slug=args.slug,
            output_root=Path(args.output_root).expanduser() if args.output_root else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "session-continue":
        result = continue_session(
            session_dir=args.session_dir,
            reply=args.reply,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "session-export":
        result = export_session(
            session_dir=args.session_dir,
            slug=args.slug,
            output_root=Path(args.output_root).expanduser() if args.output_root else None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
