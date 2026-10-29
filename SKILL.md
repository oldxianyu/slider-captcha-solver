# Slider Captcha Solver

## Identify the provider before writing any solver

- Open the login page and trigger the slider once without dragging it, then inspect what the slider actually is.

- Check for canvas elements, image URLs, script domains, and the verification request domain.

- Treat a solver written for one provider as non-portable. A Geetest solver looks for Geetest canvas elements and Geetest validate values, while a YiDun slider uses plain images from necaptcha.nosdn.127.net and has no canvas.

- Record the provider, the image sizes, and the displayed width before computing any drag distance. Never invent a selector, a class name, or an interface path you could not see.

## Capture the real puzzle images

- Trigger the slider with the user's own login step, then download the background image and the piece image from the popup.

- For YiDun, the background is a JPEG and the piece is a transparent PNG. A verified example is a 320 by 160 background and a 60 by 158 piece image, with the opaque piece about 54 by 55 pixels.

- Save each new puzzle separately. Every trigger fetches a new puzzle, so a gap computed from an old puzzle never applies to a new one.

- Stop at the puzzle popup on the first capture. Do not drag, do not enter a one-time code, and do not submit the login until the gap is computed.

## Find the gap from the images

- Run `scripts/yidun_slider.py` with `--selftest`, `--bg`, and `--slice` on the downloaded images.

- The script reads the piece shape from the PNG alpha channel, builds the piece outline, and scores each candidate x position in the background by gradient strength along that outline, searching y within 5 pixels of the piece y.

- Accept a result only when the top score clearly beats the next score from a position more than 5 pixels away. In one verified YiDun run the gap was at x 230 with a score of 85.1 against 54.7 for the next distinct position.

- Reject a result whose top candidates cluster at the same gap or whose scores are close. Refresh the puzzle and recompute instead of guessing a drag distance.

## Convert the gap to a drag distance

- Measure the background image displayed width in CSS pixels from the popup. Do not hardcode it and do not use a screenshot estimate as a precise value when a measured value is available.

- Compute the drag distance as gap x minus piece left edge, multiplied by displayed width divided by original background width.

- Example with a 320 pixel original and a 260 pixel display: a gap at 230 with a piece left edge at 3 gives about 184 CSS pixels.

- If the displayed width is only estimated, say so in the report and treat the drag as an estimate that may need one correction, not as an exact value.

## Drag with a human-like trajectory

- Drag in about 18 steps, fast at first and slow at the end, with jitter under 1 pixel per step and a short pause before release.

- Use the trajectory helper in `scripts/yidun_slider.py` instead of a single straight drag.

- Attempt a puzzle only a limited number of times. The script default is 8 retries, and a single failed attempt that refreshes the puzzle ends that puzzle. Do not loop indefinitely, because repeated failures raise the risk score and can lock the account or throttle codes.

- Run in a headed real browser with a clean residential IP when possible. Headless browsers and datacenter IPs are the known failure mode for slider risk scoring, even when the drag distance is correct.

## Stop at the code step

- When the slider passes and a one-time code input appears, stop and report that the slider passed and a code was sent.

- Never guess a one-time code. Enter only a code the user sends for that login, then submit and report the login result with any error text shown.

- Keep phone numbers, codes, passwords, and tokens out of the skill files. A script that takes a phone number as a command line argument must never contain a real one.

## Available connectors

- [GitHub](/opt/hatch/connectors/github/CONNECTOR.md) for publishing this skill to a repository.

- Use `muse.connector_search` to find other connectors and `muse.skill_search` to find related skills.

- If nothing here fits, look on the web for a maintained API or MCP server and set it up with [Custom Connectors and MCPs](/opt/muse/skills/custom-connector-setup/SKILL.md), or build a custom connector.

## Alternatives for better results

- When automated dragging keeps failing, hand the live browser to the user for one manual drag instead of retrying. A single manual pass resets the puzzle state better than more automated attempts.

- When the provider is not YiDun, keep only the identify and capture steps from this skill and write a new adapter for that provider. Do not reuse YiDun image matching on a canvas based slider.
