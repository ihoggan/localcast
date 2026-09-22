# nix6 Environments — v2

A complete workflow for setting up Python + GitHub work on nix6 (Intel i5-6500, Ubuntu 24.04). Written once, followed forever.

**v2 changes:** Adds APT package installs (git, gh weren't pre-installed on a fresh Ubuntu 24.04). Collapses SSH key setup into `gh auth login` (one step, not two). Adds an explicit gate between Parts 1 and 2. Adds a preflight check at the start of Part 2.

Three parts:

- **Part 1** — one-time machine setup. Do this once, and nix6 is ready for any Python + Git + GitHub project.
- **Part 2** — the reusable per-project pattern. Follow this for every new project.
- **Part 3** — worked example: setting up `localcast` from scratch.

Each step has a **checkpoint** — a command that confirms it worked before you move on.

---

## Part 1 — One-time machine setup

Do these once, ever. After this, nix6 is set up for any Python + Git + GitHub work.

**DO ALL OF PART 1 BEFORE ANY OF PART 2.** Otherwise `git init` runs before `init.defaultBranch` is set and you get stuck renaming branches.

### 1.1 Install the tools

Fresh Ubuntu 24.04 doesn't have `git` or `gh`. Get them:

```bash
sudo apt update
sudo apt install -y git gh
```

**Checkpoint:**
```bash
git --version && gh --version
```
Should print versions for both.

### 1.2 Git identity + defaults

```bash
git config --global user.name "IHoggan"
git config --global user.email "iain.hoggan1170@gmail.com"
git config --global init.defaultBranch main
git config --global pull.rebase false
```

**Checkpoint:**
```bash
git config --global --list | grep -E "user|init|pull"
```
Should show your name, email, `init.defaultbranch=main`, `pull.rebase=false`.

### 1.3 GitHub authentication + SSH key (single step)

`gh auth login` can generate an SSH key AND upload it to GitHub for you. One command replaces the old two-step dance.

```bash
gh auth login
```

Answer the prompts in this order:
- **What account do you want to log into?** → `GitHub.com`
- **What is your preferred protocol for Git operations?** → `SSH`
- **Generate a new SSH key to add to your GitHub account?** → `Yes`
- **Enter a passphrase for your new SSH key:** → press Enter (empty passphrase)
- **Title for your SSH key:** → `nix6`
- **How would you like to authenticate GitHub CLI?** → `Login with a web browser`
- Copy the one-time code shown → press Enter → browser opens → paste code → **Authorize**

**Checkpoints:**
```bash
gh auth status
```
Should show `Logged in to github.com account IHoggan`.

```bash
ssh -T git@github.com
```
Answer `yes` when it asks about known_hosts. Should print:
```
Hi IHoggan! You've successfully authenticated, but GitHub does not provide shell access.
```

### 1.4 Make sure `~/.local/bin` is on PATH

Needed later for CLI wrappers.

```bash
mkdir -p ~/.local/bin

echo $PATH | tr ':' '\n' | grep -q "$HOME/.local/bin" && echo "PATH OK" || {
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Added to .bashrc — open a new terminal or: source ~/.bashrc"
}
```

**Checkpoint:**
```bash
echo $PATH | tr ':' '\n' | grep local
```
Should show `/home/iain/.local/bin`.

---

**Part 1 done.** These four sections never need repeating on nix6.

---

## Part 2 — Per-project workflow

Follow this pattern for every new Python + GitHub project. Substitute `<project>` for the project name.

### 2.0 Preflight — is Part 1 done?

Run this before starting a new project:

```bash
git --version >/dev/null 2>&1 && \
gh --version >/dev/null 2>&1 && \
git config --global user.name >/dev/null 2>&1 && \
gh auth status >/dev/null 2>&1 && \
echo "Part 1 OK — ready for a new project" || \
echo "Part 1 incomplete — do that first"
```

If it says `Part 1 incomplete`, go back and do Part 1. Don't try to muddle through — that's what leaves branches called `master` when they should be `main`.

### 2.1 Create the venv

```bash
python3 -m venv ~/<project>_env
source ~/<project>_env/bin/activate
pip install <the-deps-you-need>
```

Each project gets its own venv. Isolates dependencies and never fights with system Python again.

**Checkpoint:**
```bash
python -c "import <one-of-your-deps>; print('OK')"
```

### 2.2 Create the project folder and copy files in

```bash
mkdir -p ~/code/<project>
cd ~/code/<project>

# Copy every project file from ~/Downloads
cp ~/Downloads/<file1> .
cp ~/Downloads/<file2> .
# ... etc

# Make any scripts executable
chmod +x <script1> <script2>
```

`mkdir -p` creates parent directories as needed — no separate `mkdir ~/code`.

**Checkpoint:**
```bash
ls -la
```

### 2.3 Initialise git and commit

```bash
git init
git add .
git commit -m "Initial commit — <one-line description>"
```

Because Part 1.2 set `init.defaultBranch main`, the branch will already be `main` — no rename needed.

**Checkpoint:**
```bash
git branch --show-current
```
Prints `main`.

### 2.4 Push to GitHub

```bash
gh repo create IHoggan/<project> --public --source=. --remote=origin --push \
  --description "<short description>"
```

**Checkpoint:**
Visit `https://github.com/IHoggan/<project>`. All files should appear with the README rendered below.

### 2.5 Install a CLI wrapper (if the project provides one)

If the project has a shell wrapper (like `chat` in localcast):

```bash
cp ~/code/<project>/<wrapper-name> ~/.local/bin/<wrapper-name>
chmod +x ~/.local/bin/<wrapper-name>
```

**Checkpoint:**
```bash
which <wrapper-name>
```
Should print `/home/iain/.local/bin/<wrapper-name>`.

---

**That's the pattern.** Five steps for any new project, plus a preflight.

---

## Part 3 — Worked example: localcast

The Part 2 pattern applied to a real project.

### 3.0 Preflight

```bash
git --version >/dev/null 2>&1 && \
gh --version >/dev/null 2>&1 && \
git config --global user.name >/dev/null 2>&1 && \
gh auth status >/dev/null 2>&1 && \
echo "Part 1 OK — ready" || \
echo "Do Part 1 first"
```

### 3.1 Create the venv

```bash
python3 -m venv ~/localcast_env
source ~/localcast_env/bin/activate
pip install requests rich
```

**Checkpoint:**
```bash
python -c "import requests, rich; print('OK')"
```

### 3.2 Create the folder and copy files in

Download these six files from the conversation into `~/Downloads`:
- `chat.py`
- `README.md`
- `.gitignore`
- `migrate.sh`
- `chat`
- `nix6_environments.md` (this document, latest version)

Then:

```bash
mkdir -p ~/code/localcast
cd ~/code/localcast
cp ~/Downloads/{chat.py,README.md,.gitignore,migrate.sh,chat,nix6_environments.md} .
chmod +x chat.py chat migrate.sh
```

**Checkpoint:**
```bash
ls -la
```
Six files, three executable.

### 3.3 Initialise git and commit

```bash
git init
git add .
git commit -m "Initial commit — persistent local-model characters on Ollama"
```

**Checkpoint:**
```bash
git branch --show-current
```
Prints `main`.

### 3.4 Push to GitHub

```bash
gh repo create IHoggan/localcast --public --source=. --remote=origin --push \
  --description "Persistent local-model characters running on Ollama"
```

**Checkpoint:**
Visit <https://github.com/IHoggan/localcast>. All six files visible, README rendering.

### 3.5 Install the `chat` wrapper

```bash
cp ~/code/localcast/chat ~/.local/bin/chat
chmod +x ~/.local/bin/chat
which chat
```

Prints `/home/iain/.local/bin/chat`.

### 3.6 Migrate existing personas

```bash
cd ~/code/localcast
./migrate.sh
```

Expected:
```
migrating: bubba_glasgow.txt  ->  bubba_glasgow/
migrating: bubba_pro.txt      ->  bubba_pro/
migrating: dave.txt           ->  dave/
migrating: expert.txt         ->  expert/
```

**Checkpoint:**
```bash
ls ~/bubba/dave/
```
Should show `system.txt`, `diary.md`, `config.json`.

### 3.7 First run

```bash
chat --list
chat dave
```

Have a conversation, `/exit`, run `chat dave` again to see the pending diary review and confirm memory works end-to-end.

---

## Part 4 — Ongoing development

### Small changes

```bash
cd ~/code/<project>
# Edit files
git add <files>
git commit -m "Short imperative message"
git push
```

### Feature branches for bigger changes

```bash
git checkout -b <feature-name>
# ... work, commit, work, commit ...
git push -u origin <feature-name>
gh pr create --fill
# Merge via GitHub (Squash and merge)
git checkout main
git pull
git branch -d <feature-name>
```

### Deleting a project

```bash
gh repo delete IHoggan/<project> --yes
rm -rf ~/code/<project>
rm -rf ~/<project>_env
rm -f ~/.local/bin/<wrapper-name>
```

---

## Part 5 — Troubleshooting

### `git: command not found` or `gh: command not found`
Part 1.1 not done. `sudo apt install -y git gh`.

### `Please tell me who you are` when committing
Part 1.2 not done. Set `user.name` and `user.email`.

### First commit lands on `master` instead of `main`
Part 1.2's `init.defaultBranch main` wasn't set before `git init` ran. Rename:
```bash
git branch -m master main
```
Then re-run Part 1.2 so future repos don't hit this again.

### `Permission denied (publickey)` when pushing
SSH key not set up or not registered with GitHub. Rerun Part 1.3.

### `gh: To get started with GitHub CLI, please run: gh auth login`
Part 1.3 not done. Run `gh auth login`.

### `chat: command not found` (or any wrapper)
`~/.local/bin` not on PATH in current shell. `source ~/.bashrc` or open a fresh terminal.

### `ModuleNotFoundError` when running a Python script
venv not active. The wrapper script activates it automatically — if running `python <script>.py` directly, `source ~/<project>_env/bin/activate` first.

### `Ollama isn't responding on http://localhost:11434`
`systemctl status ollama` — if inactive, `sudo systemctl start ollama`.

### `error: externally-managed-environment` from pip
Trying to install into system Python. Always work inside a venv.

### Committed under wrong author BEFORE first push
Fix the last commit: `git commit --amend --author="IHoggan <iain.hoggan1170@gmail.com>" --no-edit`

### Committed under wrong author AFTER first push
Leave it. Rewriting pushed history isn't worth one wrong-authored commit.

---

## Cheat sheet — new project in five commands

Once Part 1 is done (once, ever), starting a new project is:

```bash
# 1. venv
python3 -m venv ~/<project>_env && source ~/<project>_env/bin/activate && pip install <deps>

# 2. folder
mkdir -p ~/code/<project> && cd ~/code/<project>

# 3. add files (edit or copy), then commit
git init && git add . && git commit -m "Initial commit"

# 4. push (creates GitHub repo, uploads all files)
gh repo create IHoggan/<project> --public --source=. --remote=origin --push --description "..."

# 5. wrapper (optional)
cp <wrapper> ~/.local/bin/ && chmod +x ~/.local/bin/<wrapper>
```

Everything else is variations on this theme.

---

## Version history

- **v2** (2026-09-22) — Real-world hardening after first run: added `apt install git gh`, collapsed SSH+gh into single `gh auth login`, added Part 2.0 preflight check, added "master → main" troubleshooting entry.
- **v1** (2026-09-22) — Initial draft.
