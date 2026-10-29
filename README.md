# Slider Captcha Solver 滑块验证码求解器

一个可复用的滑块验证码求解技能。

## 这个技能是做什么的

- 先识别验证码厂商，再写求解器。极验和易盾的求解器不能通用。
- 从弹窗里取真实的背景图和拼图块图片。
- 用图像匹配找缺口：从 PNG 的 alpha 通道取拼图块形状，用块的外框轮廓在背景图梯度上匹配。
- 用背景图的显示宽度把缺口换算成拖动距离。
- 用真人轨迹拖动：约 18 步，先快后慢，每步抖动小于 1 像素，松开前稍停。
- 到短信验证码那一步就停下，绝不猜验证码。

## 文件

- `SKILL.md`：完整的方法说明。
- `skill.yaml`：技能元数据。
- `scripts/yidun_slider.py`：易盾适配器。离线自检：`python scripts/yidun_slider.py --selftest --bg bg.jpg --slice slice.png`。依赖：`numpy`、`pillow`，端到端运行还需要 `playwright`。

## 已验证的例子

易盾，背景图 320×160，拼图块约 54×55：缺口在 x=230，得分 85.1，对下一个不同位置的 54.7 拉开明显，显示宽度 260 像素时拖动距离约 184 CSS 像素，实测一次拖动通过。

## 限制

- 每次触发都会拉一张新拼图，每张新拼图都要重新算缺口。
- 建议用有头真浏览器和干净的住宅 IP。无头浏览器和机房 IP 是滑块风控的已知失败原因。
- 失败不要无限重试，反复失败会拉高风控分。
- 本仓库不存放手机号、验证码、密码、Token。

---

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
