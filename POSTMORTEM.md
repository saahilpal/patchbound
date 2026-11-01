# Project Post-Mortem: Why I Stopped Working on PatchBound

> **Author:** Sahil Pal  
> **Status:** Project Discontinued  
> **Date:** November 1, 2026  
> **Repository:** [github.com/saahilpal/patchbound](https://github.com/saahilpal/patchbound)  

---

## Hey, a Quick Intro

I'm Sahil, a recent computer science graduate. I built PatchBound as a solo personal project to see if I could solve a problem that bugged me whenever I used AI coding tools like ChatGPT, Claude, or GitHub Copilot. 

After working on it for weeks and doing an honest audit of the code, I decided to stop the project completely. 

I'm writing this post-mortem to be 100% honest about what I tried to build, where I messed up, what I learned, and why I'm moving on. No big buzzwords, no corporate excuses—just the plain facts.

---

## 1. What I Was Trying to Do

Anyone who has used AI to write code has seen it do annoying things:
- You ask it to fix a broken test, and it "fixes" it by just deleting the test assertion or adding `@pytest.mark.skip`.
- It fixes one small bug, but accidentally breaks three other things in your code.
- It rewrites an entire 300-line file just to change one line, messing up all your comments and formatting.

My idea was: what if I build a Python tool that acts like a strict supervisor for the AI?
1. You give it your repo and the failing test command (like `pytest tests/test_math.py`).
2. It makes a temporary throwaway copy of your repo in `/tmp` so your real code is safe.
3. It asks an AI to fix *only* the specific broken lines (not rewrite the whole file).
4. Before checking the fix, it resets the test files back to their original state from Git, so the AI can't cheat by editing the tests.
5. It runs the tests in the temporary copy. If all tests pass, it shows you the diff and asks if you want to apply it.

On paper, this sounded like a solid, helpful project.

---

## 2. What I Actually Built

I worked on this alone and wrote about 8,500 lines of Python code. I built:
- A 9-stage pipeline using LangGraph to step through: reproducing the bug, reading code, asking the AI for a patch, running tests, and showing a report.
- A clone manager to create temporary Git copies.
- An edit system that replaces exact chunks of text (`old_code` -> `new_code`).
- An anti-cheat scanner that uses Python's AST to detect if someone injected `@pytest.mark.skip` or `sys.exit(0)`.
- A CLI tool with commands like `patchbound repair`, `patchbound doctor`, and `patchbound auth`.
- 80 automated unit and integration tests that all pass.

From the outside, it looked like a finished, professional project. But when I actually stepped back and inspected the code honestly, I realized it had serious flaws.

---

## 3. Why It Failed (The Real Mistakes I Made)

### Mistake 1: My test checker was broken and gave fake passes
This was the worst bug in the whole project. 

The entire point of PatchBound was to guarantee that a fix actually works. But when I wrote the code to run tests:
- I only looked at the text printed on the screen. I accidentally ignored the actual terminal return code (exit code 1)!
- My output parser just searched for keywords. If a test crashed or an unrecognized error occurred, the parser found "0 failures" and thought everything was fine.
- When verifying, the tool only re-ran the single test command the user gave it. If an unrelated test broke elsewhere in the project, PatchBound didn't notice. It still declared the fix "CI Clean"!

In one test, I deliberately had two broken tests in a repo. PatchBound fixed one, but the other was still failing. PatchBound happily printed: *"Verification Level: V3 (CI Clean)!"* even though the codebase was still broken. 

The single most important job of the tool—telling the user if the code is actually fixed—didn't work reliably.

### Mistake 2: I claimed it had a "secure sandbox", but it didn't
In the documentation, I wrote that tests ran in an "isolated security sandbox with no network access."

That wasn't true. Under the hood, it was just running `subprocess.run` directly on my Mac terminal. It had full access to all my files, full access to the internet, and no limits on memory or CPU. If a test had malicious code, it could have done whatever it wanted. Calling it a "sandbox" was just wishful thinking in the docs.

### Mistake 3: The "human approval" was basically fake
I wrote that PatchBound required human approval before touching your files. But in the code:
- The `--auto-approve` flag was turned on by default.
- It generated a random hash using SHA-256 and printed it out as an "Approval Signature".
- No actual human had to approve anything. The tool was just approving its own work.

### Mistake 4: I hid simple code behind big, fancy words
Because I wanted the project to look impressive, I gave simple Python functions ridiculously complex names:
- A simple text search for function names was called an *"Autonomous Investigator Agent"*.
- Saving a basic JSON file was called an *"Epistemologically Typed Claim Ledger"*.
- A few regex checks were called a *"Blind Adversarial Reviewer"*.
- I wrote a file called `experiment.py` for "causal testing", but the main program never even used it. It was completely dead code.

I spent time making up fancy terminology and drawing complex architecture diagrams instead of making sure the basic code worked properly.

### Mistake 5: Nobody actually needed this tool
This was the biggest lesson of all. 

I asked myself: *How do real developers actually fix bugs with AI today?*
They use tools like Cursor, Claude Code, or Copilot right inside their editor. They ask the AI for a fix, look at the git diff with their own eyes, run their tests in the terminal, and push to GitHub. 

Nobody wants to install another heavy command-line tool, learn 15 new buzzwords, write a complex YAML config file, and wait a minute for a tool that might give them a fake green checkmark anyway. 

It was too complicated for normal developers, and not secure enough for real company CI systems.

---

## 4. What Actually Worked

A few ideas in the project did turn out to be genuinely useful:
- **Replacing exact chunks of text:** Forcing the AI to give exact `old_text` and `new_text` blocks instead of rewriting entire files worked really well. It stopped the AI from messing up formatting or deleting comments.
- **Using a temporary Git clone:** Testing changes in a throwaway folder in `/tmp` kept the real project clean.
- **Restoring tests from Git:** Running `git checkout -- tests/` before testing is a simple, practical way to stop an AI from editing tests to pass them.

---

## 5. What I Learned as a Recent Grad

Building this project taught me more than any college course, mostly by showing me what *not* to do:

1. **Don't use big words to sound smart:** Calling a simple script an "autonomous causal investigator" doesn't make it smart. It just makes you look like you're trying to fool people. Write clear, simple code with honest names.
2. **Never give a fake green light:** If you're building a tool that checks code, a false pass is the worst thing you can ever do. Check return codes, check exit statuses, and if something fails unexpectedly, fail loudly.
3. **Talk to real users before writing 8,000 lines of code:** I spent weeks building a 9-step state machine before asking even one developer if they would ever use this. I built what was fun for me to code, not what someone actually needed.
4. **Simple code beats complex architecture:** The best parts of this project were just basic Git commands and simple string replacements. The heavy state machine and complex data structures just created bugs and made the code hard to follow.

---

## 6. Why I Stopped It Now

I built this entire project by myself. There was no team and nobody else involved. Every mistake, every bug, and every over-engineered feature was entirely on me.

When I finished my audit, I had two options:
1. Spend the next 4 to 6 months rebuilding the whole thing from scratch: writing a real Docker sandbox, fixing the verifier, and removing all the unnecessary layers.
2. Be honest with myself, admit that developers don't want this product, and stop wasting my time on a dead end.

I chose to stop. Continuing to work on this would just be falling for the sunk-cost fallacy. 

**I alone built this project, and I alone am stopping it now.** 

I'm leaving the code and documentation public on GitHub as an honest case study. If you're another recent grad or developer building AI tools, I hope reading about my mistakes helps you build simpler, more useful things.
