# Slider Captcha Solver

A reusable skill for solving slider puzzle captchas.

## What it does

- Identify the captcha provider before writing any solver. A Geetest solver and a YiDun solver are not interchangeable.
- Capture the real background and piece images from the popup.
- Find the gap with image matching: piece shape from the PNG alpha channel, outline matched against background gradients.
- Convert the gap to a drag distance using the displayed image width.
- Drag with a human-like trajectory: about 18 steps, fast then slow, jitter under 1 pixel, pause before release.
- Stop at the one-time code step. Never guess a code.

## Files

- `SKILL.md`: the method, in full.
- `skill.yaml`: skill metadata.
- `scripts/yidun_slider.py`: YiDun adapter. Offline selftest: `python scripts/yidun_slider.py --selftest --bg bg.jpg --slice slice.png`. Dependencies: `numpy`, `pillow`, and `playwright` for end-to-end runs.

## Verified example

YiDun, background 320 by 160, piece about 54 by 55: gap at x 230, score 85.1 against 54.7 for the next distinct position, drag about 184 CSS pixels at a 260 pixel display width, passed on the first drag in a live test.

## Limits

- Every trigger fetches a new puzzle. Recompute the gap for every new puzzle.
- Headed real browser and clean residential IP are recommended. Headless browsers and datacenter IPs are the known failure mode for slider risk scoring.
- Do not loop indefinitely on failures. Repeated failures raise the risk score.
- No phone numbers, codes, passwords, or tokens are stored in this repository.
