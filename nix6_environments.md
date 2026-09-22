# nix6 Environments

A complete workflow for setting up Python + GitHub work on nix6 (Intel i5-6500, Ubuntu 24.04). Written once, followed forever.

Three parts:

- **Part 1** — one-time machine setup. Do this once, and nix6 is ready for any Python + Git + GitHub project.
- **Part 2** — the reusable per-project pattern. Follow this for every new project.
- **Part 3** — worked example: setting up `localcast` (persistent local-model characters) from scratch.

Each step has a **checkpoint** — a command that confirms it worked before you move on.

---

## Part 1 — One-time machine setup

Do these once, ever. After this, nix6 is set up for any Python + Git + GitHub work.

### 1.1 Git identity

```bash
git config --global user.name "IHoggan"
git config --global user.email "iain.hoggan1170@gmail.com"
git config --global init.defaultBranch main
git config --global pull.rebase false
```

**Checkpoint:**
```bash
git config --global --list | grep user
```
Should show `user.name=IHoggan` and `user.email=iain.hoggan1170@gmail.com`.

---

### 1.2 SSH key for GitHub

```bash
# Generate the key (no passphrase — press Enter when asked)
ssh-keygen -t ed25519 -C "iain.hoggan1170@gmail.com" -f ~/.ssh/id_ed25519 -N ""

# Start the agent and add the key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Print the public key
cat ~/.ssh/id_ed25519.pub
```

Copy the output (starts with `ssh-ed25519 ...`).

Go to <https://github.com/settings/keys> → **New SSH key** → title: `nix6` → paste → **Add SSH key**.

**Checkpoint:**
```bash
ssh -T git@github.com
```
Answer `yes` when it asks about known_hosts. Success:
```
Hi IHoggan! You've successfully authenticated, but GitHub does not provide shell access.
```

---

### 1.3 GitHub CLI

Lets you create repos from the terminal instead of the web.

```bash
sudo apt install -y gh
gh auth login
```

Answer the prompts:
- **GitHub.com**
- **SSH**
- **Skip uploading key** (already done in 1.2)
- **Login with a web browser** → opens Firefox → paste the one-time code

**Checkpoint:**
```bash
gh auth status
```
Should say `Logged in to github.com account IHoggan`.

---

### 1.4 Make sure `~/.local/bin` is on PATH

Ubuntu usually has this by default, but check and create the directory:

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
Should show `/home/iain/.local/bin`. If it doesn't, open a fresh terminal or run `source ~/.bashrc`.

---

**Part 1 done.** These four steps never need repeating on nix6.

---

## Part 2 — Per-project workflow

Follow this pattern every time you start a new Python + GitHub project. Substitute `<project>` for the project name (e.g. `localcast`).

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

# Copy every project file from ~/Downloads (or wherever they landed)
cp ~/Downloads/<file1> .
cp ~/Downloads/<file2> .
# ... etc

# Make any scripts executable
chmod +x <script1> <script2>
```

`mkdir -p` creates parent directories as needed — you don't need to make `~/code/` separately first.

**Checkpoint:**
```bash
ls -la
```
Confirms all your files are present with the right permissions.

### 2.3 Initialise git and commit

```bash
git init
git add .
git commit -m "Initial commit — <one-line description>"
```

### 2.4 Push to GitHub

**With `gh` (recommended):**
```bash
gh repo create IHoggan/<project> --public --source=. --remote=origin --push \
  --description "<short description>"
```

**Without `gh` (manual fallback):**
```bash
# 1. Create the repo in the browser: https://github.com/new
#    Name: <project>, Public, no README/gitignore/licence
# 2. Then:
git branch -M main
git remote add origin git@github.com:IHoggan/<project>.git
git push -u origin main
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

**That's the pattern.** Five steps for any new project.

---

## Part 3 — Worked example: localcast

The Part 2 pattern applied to a real project. Follow these exact commands.

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
Prints `OK`.

### 3.2 Create the project folder and copy files in

Download these six files from the conversation and put them in `~/Downloads`:
- `chat.py`
- `README.md`
- `.gitignore`
- `migrate.sh`
- `chat` (shell wrapper, no extension)
- `nix6_environments.md` (this document)

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
Should show six files. The executable ones (`chat.py`, `chat`, `migrate.sh`) show `x` in the permissions column.

### 3.3 Initialise git and commit

```bash
git init
git add .
git commit -m "Initial commit — persistent local-model characters on Ollama"
```

### 3.4 Push to GitHub

**With `gh`:**
```bash
gh repo create IHoggan/localcast --public --source=. --remote=origin --push \
  --description "Persistent local-model characters running on Ollama"
```

**Without `gh`:**
```bash
# 1. Create the repo at https://github.com/new
#    Name: localcast, Public, no README/gitignore/licence
# 2. Then:
git branch -M main
git remote add origin git@github.com:IHoggan/localcast.git
git push -u origin main
```

**Checkpoint:**
Visit <https://github.com/IHoggan/localcast>. All six files visible, README rendering underneath.

### 3.5 Install the `chat` wrapper on PATH

```bash
cp ~/code/localcast/chat ~/.local/bin/chat
chmod +x ~/.local/bin/chat
```

**Checkpoint:**
```bash
which chat
```
Prints `/home/iain/.local/bin/chat`. If it prints nothing, open a fresh terminal or run `source ~/.bashrc`.

### 3.6 Migrate existing personas

Your `~/bubba/` currently has flat `.txt` files (dave.txt, bubba_glasgow.txt, etc). `migrate.sh` moves them into per-character folders that localcast expects.

```bash
cd ~/code/localcast
./migrate.sh
```

Expected output:
```
migrating: bubba_glasgow.txt  ->  bubba_glasgow/
migrating: bubba_pro.txt      ->  bubba_pro/
migrating: dave.txt           ->  dave/
migrating: expert.txt         ->  expert/
```

**Checkpoint:**
```bash
ls ~/bubba/
ls ~/bubba/dave/
```
The first shows folders (not `.txt` files). The second shows `system.txt`, `diary.md`, `config.json`.

### 3.7 First run

```bash
chat --list
```
Lists your four characters, each with `diary: 0 chars` and `history: 0 turns`.

```bash
chat dave
```

Have a conversation. Tell Dave something durable — like "Maker's got a Land Rover Defender." Reference it later in the same chat. `/exit` when done.

On exit, you'll see `Updating diary…` then `Proposed additions saved. Review on next start.`

```bash
chat dave
```

This time it shows Dave's pending diary additions and asks keep/edit/discard. Pick `keep`.

```bash
chat --diary dave
```
Shows Dave's diary — the durable facts he now carries into every future session.

**Every future `chat dave`** injects that diary above his persona. He'll act like he genuinely remembers.

---

## Part 4 — Ongoing development

### 4.1 Small changes

Standard git flow:

```bash
cd ~/code/localcast
# Edit files
git add <files>
git commit -m "Short imperative message"
git push
```

Commit messages: imperative present ("Add /forget command" not "Added /forget command"). Under 60 characters for the subject line. Add a blank line and a longer body if needed.

### 4.2 Bigger changes — work on a branch

```bash
git checkout -b <feature-name>
# ... work, commit, work, commit ...
git push -u origin <feature-name>
gh pr create --fill  # or open a PR in the browser
```

Merge via GitHub (Squash and merge keeps main history tidy), then locally:

```bash
git checkout main
git pull
git branch -d <feature-name>
```

### 4.3 Deleting a repo

If a project turns out to be a false start:

```bash
# Delete on GitHub
gh repo delete IHoggan/<project> --yes

# Delete locally
rm -rf ~/code/<project>
rm -rf ~/<project>_env
rm -f ~/.local/bin/<wrapper-name>
```

---

## Part 5 — Troubleshooting

### `gh: command not found`
- Not installed. `sudo apt install -y gh`.

### `Permission denied (publickey)` when pushing
- SSH key not registered with GitHub. Rerun `ssh -T git@github.com` — if it fails, redo section 1.2.

### `chat: command not found` (or any wrapper)
- `~/.local/bin` not on PATH in current shell. `source ~/.bashrc` or open a fresh terminal.

### `ModuleNotFoundError` when running a Python script
- venv not active. The wrapper script activates it automatically — if you're running `python <script>.py` directly, `source ~/<project>_env/bin/activate` first.

### `Ollama isn't responding on http://localhost:11434`
- Ollama service isn't running. `systemctl status ollama` — if inactive, `sudo systemctl start ollama`.

### `error: externally-managed-environment` from pip
- Trying to install into system Python. Always work inside a venv: `source ~/<project>_env/bin/activate` first.

### `migrate.sh` says "skip: <name> (directory already exists)"
- You've already migrated. Fine, nothing to do.

### Git config shows the wrong user
- Overwrite it: `git config --global user.name "IHoggan"`. Previous commits keep their old author but new ones use the new name.

### Committed under wrong author BEFORE first push
- Fix the last commit only: `git commit --amend --author="IHoggan <iain.hoggan1170@gmail.com>" --no-edit`

### Committed under wrong author AFTER first push
- Leave it. Rewriting pushed history is more hassle than one wrong-authored commit is worth.

---

## Cheat sheet — new project in five commands

Once nix6 is set up (Part 1 done), starting a new project is:

```bash
# 1. venv
python3 -m venv ~/<project>_env && source ~/<project>_env/bin/activate && pip install <deps>

# 2. folder
mkdir -p ~/code/<project> && cd ~/code/<project>

# 3. add files (edit or copy) then commit
git init && git add . && git commit -m "Initial commit"

# 4. push
gh repo create IHoggan/<project> --public --source=. --remote=origin --push --description "..."

# 5. wrapper (optional)
cp <wrapper> ~/.local/bin/ && chmod +x ~/.local/bin/<wrapper>
```

Everything else is variations on this theme.
