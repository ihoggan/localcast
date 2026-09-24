# localcast

Persistent local AI characters, running on [Ollama](https://ollama.com), on hardware you already own.

Out of the box, `ollama run llama3.2:3b` forgets you the moment you exit: your name, yesterday's conversation, and any persona you gave it are all gone. localcast wraps Ollama so each character keeps a **persona**, a **diary** of what you've told it, and a **conversation history** that survives restarts. I call that set of files the *personality matrix*.

It's one Python file with two dependencies. No cloud, no API key, no subscription.

## Tested on

Built and used on a 2015 office PC that was headed for the skip:

| | |
|---|---|
| Machine | Dell OptiPlex 3040, no graphics card |
| CPU | Intel Core i5-6500 (4 cores, 3.2 GHz, 2015) |
| RAM | 16 GB (the model uses 2.6 GB of it) |
| OS | Ubuntu 24.04 LTS |
| Ollama | 0.34.2 |
| Model | `llama3.2:3b`, running 100% on the CPU |
| Speed | **8.0 tokens/s** generating (measured with `ollama run --verbose`), so a 100-word reply takes about 13 seconds |

That's roughly reading pace: slow enough to notice, fast enough to hold a conversation. Any newer machine should be quicker.

## What it looks like

A real session with Dave, a grumpy Northern electrician character, started from an empty diary:

```
Maker: Hows it going Dave, long time no see?

dave: What's up, Maker? Just had a busy day, been up to me elbows in
electrics. Wires, sockets, the whole lot. Just finished a job in Prenton,
all sound. You're not 'ere for a chat, are ya?

Maker: The van is good, a old 1979 transit just runs and runs, and we can
always get the parts

dave: Blimey, that's old! Me van's a 2015, still running like a top. [...]

Maker: /exit

Updating diary…
Nothing new worth remembering.
```

Dave invented a job in Prenton, his own van, a hotel and a dog. None of it went into his diary, which is supposed to hold facts about *you*. He also missed a real one: the Transit. See [Honest limits](#honest-limits).

## How it works

Each character is a folder:

```
~/bubba/
└── dave/
    ├── system.txt       # the persona: who this character is
    ├── diary.md         # facts you've told this character, each with your own words
    ├── history.jsonl    # every turn, one JSON object per line
    ├── config.json      # model, temperature, context size, history length
    └── pending.md       # proposed diary lines awaiting your approval
```

Every time you talk to a character, it's given its persona, its diary and your last few turns.

### How the diary is kept honest

When you `/exit`, the model reads the conversation and proposes things worth remembering. Small models invent things, so every proposal has to pass checks in code before you ever see it:

1. It must come with **your exact words** from the conversation. The code checks the quote really appears in something *you* said, not something the character said.
2. The quote must be long enough to mean something, and the fact must share a real word with it, so a genuine quote can't be attached to an invented fact.

Anything that fails is thrown away, and you're told what was discarded and why. What survives goes into `pending.md`. The next time you open that character, you see each line next to your own words and have to type `keep`, `edit` or `discard`. There's no default, so pressing Enter adds nothing.

The diary is plain markdown, so you can also edit it by hand, or add a fact directly with `/remember`.

**Why this exists:** the first version didn't have it. When I finally read Dave's diary, every line was wrong. One joke about my old van had become four lines of invented "company van policy", and Dave's own made-up dog had gone in as well. I measured it: over 15 test runs, **35 of 35** proposed lines were invented. After the fix, **10 of 22**, and general-knowledge filler ("The M56 is a major motorway in the UK") dropped from 19 lines to none. The method, raw results and caveats are in [`tests/results/NOTES.md`](tests/results/NOTES.md).

## Install

These steps assume Ubuntu 24.04 (other Linux, macOS and WSL should work the same). Run each block, then check the checkpoint before moving on.

**1. Install Ollama and pull the model**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

Checkpoint: `ollama list` shows `llama3.2:3b`.

**2. Clone localcast and create its venv inside the project folder**

```bash
sudo apt install -y git python3-venv
mkdir -p ~/code
git clone https://github.com/IHoggan/localcast.git ~/code/localcast
cd ~/code/localcast
python3 -m venv venv
source venv/bin/activate
pip install requests rich
```

Checkpoint: `python -c "import requests, rich; print('OK')"` prints `OK`.

**3. Put the `cast` command on your PATH**

```bash
mkdir -p ~/.local/bin
cp ~/code/localcast/cast ~/.local/bin/cast
chmod +x ~/.local/bin/cast
```

Checkpoint: open a new terminal and run `which cast`. It should print `/home/<you>/.local/bin/cast`. If it prints nothing, run:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

(Why `cast` and not `chat`? Ubuntu already ships a `/usr/sbin/chat`, an old modem dialler. Run `which <name>` before picking a command name.)

**4. Create your first character**

```bash
cast --new dave
nano ~/bubba/dave/system.txt
cast dave
```

In `system.txt`, describe who the character is in plain English: their job, how they talk, what they care about. Save with Ctrl+O, Enter, then exit with Ctrl+X.

## Usage

```bash
cast --list          # list characters
cast --new <name>    # scaffold a new character
cast --diary <name>  # show what a character remembers
cast <name>          # start chatting
```

Inside a session:

```
/diary         show what this character remembers
/remember X    add a fact to the diary yourself
/history       show the last 10 turns
/clear         wipe conversation history (keeps the diary)
/help          list commands
/exit          leave (or Ctrl+D)
```

## Configuration

`~/bubba/<name>/config.json`:

```json
{
  "model": "llama3.2:3b",
  "temperature": 0.85,
  "num_ctx": 4096,
  "history_turns": 20
}
```

- `model`: any model you've pulled (`ollama list`).
- `temperature`: higher means more spontaneous, lower means more consistent.
- `history_turns`: how many previous turns are sent each time. More gives better short-term memory, but on old hardware it gets slower as the conversation fills the context window.

## Honest limits

A 3-billion-parameter model on a 2015 CPU is not a frontier chatbot.

- **Characters make things up about their own lives.** That's usually what you want from a character, and it's why the diary only accepts your words.
- **They'll play along with a false premise.** Ask "did you finish that job in Wrexham?" and a character will describe a job that never happened. The diary check stops that becoming a "memory".
- **The diary misses things.** It now errs towards saying nothing, and in testing it caught about half of the real facts. Use `/remember` for anything important.
- **It can't tell your real life from role-play.** If you tell Dave you're his boss, that's something you said, so it can go in the diary.
- **It sometimes proposes trivia** ("Raining again here"). You'll see your words beside it at review time; type `discard`.

## Tests

```bash
cd ~/code/localcast && source venv/bin/activate
python tests/test_diary_check.py      # the diary checks, no Ollama needed
python tests/diary_eval.py --help     # the before/after measuring rig
```

## Roadmap

At the moment this is what I call **level 2**: persistent characters. The next levels:

- **Level 3**: characters that know about each other, and can talk to each other.
- **Level 4**: characters backed by reference material (Dave gets the wiring regs).
- **Level 6**: voice in and out.
- **Level 7**: characters as game NPCs.

## Setting up the machine itself

If you're starting from a bare old PC, the whole workflow (Ubuntu, git, GitHub, a new project in one command) is in [nix6-tools](https://github.com/IHoggan/nix6-tools).

## Licence

MIT. See [LICENSE](LICENSE).
