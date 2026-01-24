#!/usr/bin/env python3
"""
Briefing Generator - Main entry point for market briefings.
Generates and optionally sends to WhatsApp group.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def ensure_venv() -> None:
    """Re-exec inside local venv if available and not already active."""
    if os.environ.get("FINANCE_NEWS_VENV_BOOTSTRAPPED") == "1":
        return
    if sys.prefix != sys.base_prefix:
        return
    venv_python = Path(__file__).resolve().parent.parent / "venv" / "bin" / "python3"
    if not venv_python.exists():
        print("⚠️ finance-news venv missing; run scripts from the repo venv to avoid dependency errors.", file=sys.stderr)
        return
    env = os.environ.copy()
    env["FINANCE_NEWS_VENV_BOOTSTRAPPED"] = "1"
    os.execvpe(str(venv_python), [str(venv_python)] + sys.argv, env)


ensure_venv()


def send_to_whatsapp(message: str, group_name: str = "Niemand Boerse"):
    """Send message to WhatsApp group via Clawdbot message tool."""
    # Use clawdbot message tool
    try:
        result = subprocess.run(
            [
                'clawdbot', 'message', 'send',
                '--channel', 'whatsapp',
                '--target', group_name,
                '--message', message
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Sent to WhatsApp group: {group_name}", file=sys.stderr)
            return True
        else:
            print(f"⚠️ WhatsApp send failed: {result.stderr}", file=sys.stderr)
            return False
    
    except Exception as e:
        print(f"❌ WhatsApp error: {e}", file=sys.stderr)
        return False


def generate_and_send(args):
    """Generate briefing and optionally send to WhatsApp."""
    
    # Determine briefing type based on current time or args
    if args.time:
        briefing_time = args.time
    else:
        hour = datetime.now().hour
        briefing_time = 'morning' if hour < 12 else 'evening'
    
    # Generate the briefing
    cmd = [
        sys.executable, SCRIPT_DIR / 'summarize.py',
        '--time', briefing_time,
        '--style', args.style,
        '--lang', args.lang
    ]

    if args.deadline is not None:
        cmd.extend(['--deadline', str(args.deadline)])

    if args.fast:
        cmd.append('--fast')

    if args.llm:
        cmd.append('--llm')
        cmd.extend(['--model', args.model])

    if args.debug:
        cmd.append('--debug')
    
    # Pass --json flag if requested
    if args.json:
        cmd.append('--json')
    
    print(f"📊 Generating {briefing_time} briefing...", file=sys.stderr)
    
    timeout = args.deadline if args.deadline is not None else 300
    timeout = max(1, int(timeout))
    if args.deadline is not None:
        timeout = timeout + 5
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout
    )
    
    if result.returncode != 0:
        print(f"❌ Briefing generation failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    briefing = result.stdout.strip()
    
    # Print to stdout
    print(briefing)
    
    # Send to WhatsApp if requested
    if args.send and args.group:
        if args.json:
            # Parse JSON and send summary only
            try:
                data = json.loads(briefing)
                message = data.get('summary', '')
                if message:
                    send_to_whatsapp(message, args.group)
                else:
                    print(f"⚠️ No summary field in JSON output", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"⚠️ Cannot parse JSON for WhatsApp send", file=sys.stderr)
        else:
            send_to_whatsapp(briefing, args.group)
    
    return briefing


def main():
    parser = argparse.ArgumentParser(description='Briefing Generator')
    parser.add_argument('--time', choices=['morning', 'evening'], 
                        help='Briefing type (auto-detected if not specified)')
    parser.add_argument('--style', choices=['briefing', 'analysis', 'headlines'],
                        default='briefing', help='Summary style')
    parser.add_argument('--lang', choices=['en', 'de'], default='en',
                        help='Output language')
    parser.add_argument('--send', action='store_true',
                        help='Send to WhatsApp group')
    parser.add_argument('--group', default='120363421796203667@g.us',
                        help='WhatsApp group name')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--deadline', type=int, default=None,
                        help='Overall deadline in seconds')
    parser.add_argument('--llm', action='store_true', help='Use LLM summary')
    parser.add_argument('--model', choices=['claude', 'minimax', 'gemini'],
                        default='claude', help='LLM model (only with --llm)')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast mode (shorter timeouts, fewer items)')
    parser.add_argument('--debug', action='store_true',
                        help='Write debug log with sources')
    
    args = parser.parse_args()
    generate_and_send(args)


if __name__ == '__main__':
    main()
