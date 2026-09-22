# localcast

Persistent local-model characters, running on [Ollama](https://ollama.com).

A small Python tool that turns Ollama's throwaway chat sessions into ongoing relationships with a **cast** of characters. Each character has a persona, a diary of what they've learned about you over time, and a conversation history that survives restarts.

## Why

Out of the box, `ollama run llama3.2:3b` gives you a stateless chat. Every session starts fresh — the model forgets your name, forgets what you talked about yesterday, and loses any persona instructions the moment you exit.

`localcast` wraps Ollama with three simple ideas:

1. **A folder per character** — persona, diary, history, config
2. **A diary** — durable notes the character carries into every future session
3. **Automatic diary extraction** — after each chat, the model proposes what it should remember; you approve

That's it. About 300 lines of Python.

## Requirements

- Linux, macOS, or WSL
- Python 3.10+
- [Ollama](https://ollama.com) running locally with at least one model pulled
- `pip install requests rich`

## Install

```bash
git clone git@github.com:ihoggan/localcast.git ~/code/localcast
cd ~/code/localcast

python3 -m venv ~/localcast_env
source ~/localcast_env/bin/activate
pip install requests rich

# Put a 'chat' wrapper on your PATH
mkdir -p ~/.local/bin
cat > ~/.local/bin/chat <<'EOF'
#!/usr/bin/env bash
source ~/localcast_env/bin/activate
python ~/code/localcast/chat.py "$@"
EOF
chmod +x ~/.local/bin/chat

# Make sure ~/.local/bin is on PATH (usually is on Ubuntu)
echo $PATH | tr ':' '\n' | grep -q "$HOME/.local/bin" || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

## Usage

```bash
chat --list              # what characters exist
chat --new dave          # scaffold a new character
chat --diary dave        # peek at what dave remembers
chat dave                # actually chat
```

Inside a chat session:

```
/exit          leave (or Ctrl+D)
/diary         show what this character remembers
/remember X    add a manual note
/history       show the last 10 turns
/clear         wipe conversation history (keeps the diary)
/help
```

## File layout

Everything lives under `~/bubba/`:

```
~/bubba/
├── dave/
│   ├── system.txt       # the persona prompt
│   ├── diary.md         # durable notes about the Maker
│   ├── history.jsonl    # every turn ever
│   ├── config.json      # model, temperature, num_ctx
│   └── pending.md       # awaiting approval (transient)
└── bubba/
    └── ...
```

## How the diary works

At the end of each session (if you exchanged more than a couple of turns), `localcast` asks the model itself to look at the transcript and propose what's worth remembering. Those proposals go into `pending.md`.

When you next start a session with that character, you're shown the pending additions and asked:

- **keep** — merge them into the diary as-is
- **edit** — open in `$EDITOR` first
- **discard** — bin them

The diary is markdown. Facts accumulate as bullet lines. You can also edit it directly in a text editor whenever you want.

## Configuration

Each character's `config.json`:

```json
{
  "model": "llama3.2:3b",
  "temperature": 0.85,
  "num_ctx": 4096,
  "history_turns": 20
}
```

Change `model` to any model you have pulled (`ollama list` shows them). Higher `temperature` = more spontaneous. `history_turns` controls how many prior turns are sent to the model each time.

## Character prompts

`system.txt` is a plain system prompt. There are working examples in `examples/`:

- `dave.txt` — a grumpy Northern electrician who has no idea he's an AI
- `bubba_glasgow.txt` — a Glaswegian IT mate
- `bubba_pro.txt` — the toned-down professional version
- `expert.txt` — a warm thinking partner

## Roadmap

Currently at what I'd call **Level 2**: persistent characters with diaries. Future levels:

- **Level 3** — characters that can reference each other, single CLI, character-to-character conversations
- **Level 4** — RAG-backed knowledge (Dave gets the wiring regs)
- **Level 6** — voice input/output
- **Level 7** — characters as NPCs in games (HUSTLER commentary, HexWars enemy generals)

## Licence

MIT.
