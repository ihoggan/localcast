#!/usr/bin/env python3
"""
chat — persistent local-model characters, running on Ollama.

Each character lives in ~/bubba/<name>/ with:
  system.txt     — the persona system prompt
  diary.md       — durable facts the character remembers about you
  history.jsonl  — every turn ever, one JSON object per line
  config.json    — model, temperature, num_ctx, history_turns
  pending.md     — proposed diary additions awaiting review (transient)

Usage:
  chat <name>              start chatting with a character
  chat --list              list characters
  chat --new <name>        scaffold a new character
  chat --diary <name>      show a character's diary
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

BASE = Path.home() / "bubba"
OLLAMA_URL = "http://localhost:11434"

console = Console()


# ---------- Ollama plumbing ----------

def ollama_up() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def chat_ollama(model, messages, temperature=0.85, num_ctx=4096, stream=True):
    """Call Ollama /api/chat. Yields text chunks."""
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        },
        stream=stream,
    )
    r.raise_for_status()
    if stream:
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("done"):
                return
            yield chunk.get("message", {}).get("content", "")
    else:
        yield r.json()["message"]["content"]


# ---------- Character ----------

class Character:
    def __init__(self, name: str):
        self.name = name
        self.dir = BASE / name
        if not self.dir.exists():
            raise FileNotFoundError(f"No character named {name!r} at {self.dir}")
        if not (self.dir / "system.txt").exists():
            raise FileNotFoundError(
                f"Character {name!r} has no system.txt in {self.dir}"
            )
        self.system = (self.dir / "system.txt").read_text().strip()
        self.diary_path = self.dir / "diary.md"
        self.history_path = self.dir / "history.jsonl"
        self.config_path = self.dir / "config.json"
        self.pending_path = self.dir / "pending.md"
        self.config = (
            json.loads(self.config_path.read_text())
            if self.config_path.exists()
            else {}
        )

    def diary(self) -> str:
        return self.diary_path.read_text().strip() if self.diary_path.exists() else ""

    def recent_history(self, n: int = 20):
        if not self.history_path.exists():
            return []
        lines = [
            l for l in self.history_path.read_text().splitlines() if l.strip()
        ]
        turns = [json.loads(l) for l in lines]
        return turns[-n:] if n else turns

    def append_turn(self, role: str, content: str) -> None:
        with self.history_path.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "role": role,
                        "content": content,
                    }
                )
                + "\n"
            )

    def build_system(self) -> str:
        diary = self.diary()
        if diary:
            return (
                f"{self.system}\n\n---\n"
                f"WHAT YOU KNOW ABOUT THE MAKER AND THE WORLD "
                f"(from previous conversations):\n{diary}"
            )
        return self.system

    def build_messages(self, user_input: str, n_history: int = 20):
        msgs = [{"role": "system", "content": self.build_system()}]
        for turn in self.recent_history(n_history):
            msgs.append({"role": turn["role"], "content": turn["content"]})
        msgs.append({"role": "user", "content": user_input})
        return msgs


# ---------- Diary extraction ----------

DIARY_PROMPT = """You are helping {name} remember things about the Maker.

Here is what {name} currently knows:
---
{diary}
---

Here is a recent conversation between them:
---
{transcript}
---

List any NEW durable facts about the Maker or the world that {name} should \
remember for future conversations. Keep it terse — one bullet per fact. Skip \
anything already in the existing notes. Skip small talk and transient stuff \
(what they had for tea, weather, mood). If nothing new is worth noting, \
respond with the single word: NONE

Format each new fact as a markdown bullet starting with `- `. Write in \
neutral third-person notes, not in {name}'s voice."""


def extract_diary_update(char: Character, recent_turns, model: str) -> str:
    if not recent_turns:
        return ""
    transcript = "\n".join(
        f"{t['role'].upper()}: {t['content']}" for t in recent_turns
    )
    current_diary = char.diary() or "(nothing yet)"
    prompt = DIARY_PROMPT.format(
        name=char.name, diary=current_diary, transcript=transcript
    )
    reply = ""
    for chunk in chat_ollama(
        model,
        [{"role": "user", "content": prompt}],
        temperature=0.3,
        stream=True,
    ):
        reply += chunk
    reply = reply.strip()
    if not reply or reply.upper().startswith("NONE"):
        return ""
    # Keep only bullet lines to filter out any preamble the model added
    bullets = [l for l in reply.splitlines() if l.strip().startswith("-")]
    return "\n".join(bullets)


def review_pending(char: Character) -> None:
    if not char.pending_path.exists():
        return
    pending = char.pending_path.read_text().strip()
    if not pending:
        char.pending_path.unlink()
        return
    console.print(
        Panel(
            Markdown(pending),
            title=f"[bold cyan]{char.name}'s pending diary additions[/bold cyan]",
            border_style="cyan",
        )
    )
    choice = Prompt.ask(
        "What now?", choices=["keep", "edit", "discard"], default="keep"
    )
    if choice == "keep":
        with char.diary_path.open("a") as f:
            f.write("\n" + pending + "\n")
        console.print("[green]Added to diary.[/green]")
    elif choice == "edit":
        editor = os.environ.get("EDITOR", "nano")
        os.system(f"{editor} {char.pending_path}")
        edited = char.pending_path.read_text().strip()
        if edited:
            with char.diary_path.open("a") as f:
                f.write("\n" + edited + "\n")
            console.print("[green]Edited and added to diary.[/green]")
        else:
            console.print("[yellow]Empty after edit — discarded.[/yellow]")
    else:
        console.print("[yellow]Discarded.[/yellow]")
    char.pending_path.unlink()


# ---------- Session ----------

HELP_TEXT = """[bold]Commands:[/bold]
  /exit           leave (Ctrl+D also works)
  /diary          show what this character remembers
  /remember X     add a manual note to the diary
  /history        show the last 10 turns
  /clear          wipe conversation history (KEEPS diary)
  /help           this"""


def run_session(char: Character) -> None:
    model = char.config.get("model", "llama3.2:3b")
    temperature = char.config.get("temperature", 0.85)
    num_ctx = char.config.get("num_ctx", 4096)
    n_history = char.config.get("history_turns", 20)

    if not ollama_up():
        console.print(
            f"[red]Ollama isn't responding on {OLLAMA_URL}. "
            f"Is the service running?[/red]"
        )
        console.print("[dim]Try: systemctl status ollama[/dim]")
        sys.exit(1)

    review_pending(char)

    console.print(
        Panel(
            f"[bold]{char.name}[/bold] · model [cyan]{model}[/cyan] · "
            f"temp {temperature} · ctx {num_ctx}\n"
            f"Type /help for commands. Ctrl+D or /exit to leave.",
            border_style="dim",
        )
    )

    turns_this_session = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]Maker[/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd, _, arg = user_input[1:].partition(" ")
            cmd = cmd.lower()
            if cmd in ("exit", "quit", "bye"):
                break
            if cmd == "help":
                console.print(Panel(HELP_TEXT, border_style="dim"))
                continue
            if cmd == "diary":
                console.print(
                    Panel(
                        Markdown(char.diary() or "(nothing yet)"),
                        title="diary",
                        border_style="cyan",
                    )
                )
                continue
            if cmd == "remember":
                if not arg.strip():
                    console.print("[red]Usage: /remember <fact>[/red]")
                    continue
                with char.diary_path.open("a") as f:
                    f.write(f"- {arg.strip()}\n")
                console.print(f"[green]Noted: {arg.strip()}[/green]")
                continue
            if cmd == "history":
                for t in char.recent_history(10):
                    tag = "Maker" if t["role"] == "user" else char.name
                    console.print(
                        f"[dim]{t['ts']}[/dim] [bold]{tag}:[/bold] "
                        f"{t['content'][:200]}"
                    )
                continue
            if cmd == "clear":
                if Confirm.ask(
                    "Wipe conversation history (diary is safe)?", default=False
                ):
                    if char.history_path.exists():
                        char.history_path.unlink()
                    console.print("[yellow]History cleared.[/yellow]")
                continue
            console.print(f"[red]Unknown command: /{cmd}[/red]")
            continue

        messages = char.build_messages(user_input, n_history)
        char.append_turn("user", user_input)
        turns_this_session.append({"role": "user", "content": user_input})

        console.print(f"\n[bold cyan]{char.name}[/bold cyan]", end=" ")
        reply = ""
        try:
            for chunk in chat_ollama(
                model, messages, temperature, num_ctx, stream=True
            ):
                console.print(chunk, end="")
                reply += chunk
        except requests.RequestException as e:
            console.print(f"\n[red]Ollama error: {e}[/red]")
            continue
        console.print()

        char.append_turn("assistant", reply)
        turns_this_session.append({"role": "assistant", "content": reply})

    if len(turns_this_session) >= 4:
        console.print("\n[dim]Updating diary…[/dim]")
        try:
            update = extract_diary_update(char, turns_this_session, model)
            if update:
                char.pending_path.write_text(update)
                console.print(
                    f"[dim]Proposed additions saved. Review on next start "
                    f"({char.pending_path}).[/dim]"
                )
            else:
                console.print("[dim]Nothing new worth remembering.[/dim]")
        except Exception as e:
            console.print(f"[red]Diary update failed: {e}[/red]")
    console.print(f"[dim]Bye, Maker.[/dim]")


# ---------- CLI commands ----------

def list_characters() -> None:
    if not BASE.exists():
        console.print(f"[yellow]No {BASE} directory yet.[/yellow]")
        return
    chars = [
        p.name
        for p in BASE.iterdir()
        if p.is_dir() and (p / "system.txt").exists()
    ]
    if not chars:
        console.print(f"[yellow]No characters in {BASE}.[/yellow]")
        return
    console.print("[bold]Characters:[/bold]")
    for name in sorted(chars):
        c = Character(name)
        diary_bytes = len(c.diary())
        hist = c.recent_history(0)
        console.print(
            f"  [cyan]{name:15s}[/cyan]  "
            f"diary: {diary_bytes:5d} chars  "
            f"history: {len(hist):4d} turns"
        )


def new_character(name: str) -> None:
    d = BASE / name
    if d.exists():
        console.print(f"[red]{d} already exists.[/red]")
        return
    d.mkdir(parents=True)
    (d / "system.txt").write_text(
        f"You are {name}. Describe your persona in this file.\n"
    )
    (d / "diary.md").write_text("")
    (d / "config.json").write_text(
        json.dumps(
            {
                "model": "llama3.2:3b",
                "temperature": 0.85,
                "num_ctx": 4096,
                "history_turns": 20,
            },
            indent=2,
        )
    )
    console.print(f"[green]Created {d}[/green]")
    console.print(f"Edit [cyan]{d / 'system.txt'}[/cyan] to define {name}.")


def show_diary(name: str) -> None:
    c = Character(name)
    console.print(
        Panel(
            Markdown(c.diary() or "(nothing yet)"),
            title=f"{name}'s diary",
            border_style="cyan",
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="chat — persistent local-model characters",
    )
    ap.add_argument("name", nargs="?", help="character name to chat with")
    ap.add_argument("--list", "-l", action="store_true", help="list characters")
    ap.add_argument(
        "--new", "-n", metavar="NAME", help="scaffold a new character"
    )
    ap.add_argument(
        "--diary", "-d", metavar="NAME", help="show a character's diary"
    )
    args = ap.parse_args()

    if args.list:
        list_characters()
    elif args.new:
        new_character(args.new)
    elif args.diary:
        show_diary(args.diary)
    elif args.name:
        try:
            char = Character(args.name)
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
            console.print("Try: chat --list  or  chat --new <name>")
            sys.exit(1)
        run_session(char)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
