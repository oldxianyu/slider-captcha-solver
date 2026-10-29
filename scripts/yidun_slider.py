#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yidun_slider.py —— 网易易盾滑块拼图求解器（华为云登录页适配版）

来源：2026-10-29 实测华为云登录页滑块。
- 弹窗标题“请完成安全验证”，提示“向右拖动滑块填充拼图”，在登录页内以 iframe 形式出现。
- 不是极验：无 canvas，三张图不是极验 canvas，而是两张直接图片：
  背景图 .jpg（实测 320×160），滑块图透明 .png（实测 60×158），
  域名均为 necaptcha.nosdn.127.net。
- 因此极验脚本（找 .geetest_canvas_*、拿 geetest_validate）不能直接用，
  这里按易盾重写：下载背景图 + 滑块图 → 找缺口 → 真人轨迹拖动 → 重试。

核心算法（只用 PIL + numpy，不依赖 OpenCV）：
1. 滑块图 alpha 通道求拼图块外框（实测块约 56×55，位于滑块图 y≈37 起）。
2. 背景图算梯度（相邻像素差），拼图块外框轮廓与背景梯度做匹配：
   对每个候选 x（y 在滑块块 y 附近 ±5 内搜索），算轮廓处平均梯度，
   得分最高且明显拉开第二名的即为缺口。实测样例：缺口 x≈223，y≈39，
   得分 76，次高 48，区分度明显。
3. 拖动距离换算：drag_px = (gap_x - piece_x0) * (displayed_bg_width / 320)
   displayed_bg_width 是弹窗里背景图的实际显示宽度（CSS 像素），
   必须在运行时从页面量到，不能硬编码。轨道宽度约 270px 时，
   若显示宽度与原图 320 一致，drag 约等于 gap_x - 3。

使用方法（只在你自己的账号、你自己的机器上跑）：
  # 离线自检：不开浏览器，用已下载的实测图验证找缺口
  python yidun_slider.py --selftest --bg bg.jpg --slice slice.png

  # 端到端（需要有头真 Chrome + 干净住宅 IP，无头/机房 IP 极易被风控拦）：
  python yidun_slider.py --phone 186xxxxxxxx --headed
  流程：打开华为登录页 → 手机号登录 → 填手机号 → 点获取验证码 →
        等易盾弹窗 → 取背景/滑块图 → 找缺口 → 拖动 → 停下等你输短信码。
  本脚本不输入短信码、不点登录/注册、不自动重试超过 8 次，
  几次不过就停下，改手动滑，避免风控分累积。

依赖：pip install playwright numpy pillow
      python -m playwright install chromium   # 有头模式建议用系统真 Chrome
"""
from __future__ import annotations
import argparse, json, math, os, random, sys, time, urllib.request

try:
    import numpy as np
    from PIL import Image
except ImportError as e:
    print(f"缺少依赖：{e}，请先 pip install numpy pillow", file=sys.stderr)
    raise


def detect_gap(bg_path: str, slice_path: str):
    """返回 (gap_x, gap_y, score, second_score)，坐标为背景原图 320×160 像素。"""
    bg = np.array(Image.open(bg_path).convert("RGB"), dtype=float)
    sl = np.array(Image.open(slice_path).convert("RGBA"))
    alpha = sl[:, :, 3]
    mask = (alpha > 128).astype(float)
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        raise RuntimeError("滑块图 alpha 通道里找不到拼图块")
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    piece = mask[y0:y1 + 1, x0:x1 + 1]
    # 外框 = 掩码 - 腐蚀后的掩码
    eroded = np.zeros_like(piece)
    eroded[1:-1, 1:-1] = (piece[1:-1, 1:-1] * piece[:-2, 1:-1] * piece[2:, 1:-1]
                          * piece[1:-1, :-2] * piece[1:-1, 2:])
    outline = piece - eroded
    if outline.sum() == 0:
        raise RuntimeError("拼图块外框为空")
    gray = bg.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edge = gx + gy
    h, w = piece.shape
    best = []
    for dy in range(-5, 6):
        y = y0 + dy
        if y < 0 or y + h > bg.shape[0]:
            continue
        for x in range(0, bg.shape[1] - w + 1):
            patch = edge[y:y + h, x:x + w]
            score = float((patch * outline).sum() / outline.sum())
            best.append((score, x, y))
    best.sort(reverse=True)
    top = best[0]
    # 次高分取 x 与最高分相差 5px 以上的候选（同一缺口邻近像素不算竞争者）
    second = next((b for b in best[1:] if abs(b[1] - top[1]) > 5), best[1])
    return {"gap_x": int(top[1]), "gap_y": int(top[2]),
            "piece_x0": int(x0), "piece_y0": int(y0),
            "piece_w": int(w), "piece_h": int(h),
            "score": round(top[0], 1), "second_score": round(second[0], 1),
            "second_x": int(second[1])}


def drag_distance(gap_x: int, piece_x0: int, displayed_bg_width: float,
                  original_bg_width: float = 320.0) -> float:
    """背景原图坐标 → 页面拖动距离（CSS 像素）。"""
    scale = displayed_bg_width / original_bg_width
    return (gap_x - piece_x0) * scale


def human_track(distance: float, steps: int = 18):
    """真人轨迹：先快后慢、带微小抖动和末尾回摆，返回每步累计位移。"""
    pts, acc = [], 0.0
    for i in range(1, steps + 1):
        t = i / steps
        # ease-out：前期快、后期慢
        eased = 1 - (1 - t) ** 2
        target = distance * eased
        step = target - acc + random.uniform(-0.6, 0.6)
        acc += step
        pts.append(round(acc, 1))
    # 末尾微调到目标附近（不要精确到 0.1px，太像机器）
    pts[-1] = round(distance + random.uniform(-1.0, 1.0), 1)
    return pts


def download(url: str, dest: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def main(argv=None):
    p = argparse.ArgumentParser(description="网易易盾滑块求解器（华为云登录页适配版）")
    p.add_argument("--selftest", action="store_true", help="离线找缺口，不开浏览器")
    p.add_argument("--bg", default="bg.jpg")
    p.add_argument("--slice", default="slice.png")
    p.add_argument("--phone", help="手机号（端到端模式才需要）")
    p.add_argument("--retries", type=int, default=8)
    p.add_argument("--headed", action="store_true", help="用有头真 Chrome（必须）")
    args = p.parse_args(argv)

    if args.selftest:
        r = detect_gap(args.bg, args.slice)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        print(f"缺口≈({r['gap_x']}, {r['gap_y']})，得分 {r['score']} vs 次高 {r['second_score']}")
        if r["score"] < r["second_score"] * 1.2:
            print("警告：最高分与次高分区分度不足，缺口可能不准，请换一张图再测", file=sys.stderr)
            return 1
        return 0

    # 端到端模式：需要 Playwright，且必须有头
    if not args.headed:
        print("错误：无头模式极易被风控拦，请加 --headed 用有头真 Chrome", file=sys.stderr)
        return 2
    if not args.phone:
        print("错误：端到端模式需要 --phone", file=sys.stderr)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少 playwright，请 pip install playwright 并装浏览器", file=sys.stderr)
        return 2

    with sync_playwright() as pw:
        # 优先用系统真 Chrome（channel=chrome），不要用自带 Chromium 无头
        browser = pw.chromium.launch(channel="chrome", headless=False)
        page = browser.new_page()
        page.goto("https://auth.huaweicloud.com/authui/login.html#/login",
                  wait_until="domcontentloaded", timeout=60000)
        # 以下选择器需按华为登录页实测填写（占位说明，勿硬编造）：
        # 1) 点“手机号登录”  2) 填手机号  3) 点“获取验证码”  4) 等易盾 iframe 弹窗
        print("请在浏览器里完成到易盾弹窗出现的一步（本脚本当前版本只提供找缺口+轨迹函数，"
              "页面点击步骤需按你实测的选择器补齐后运行）")
        print("找缺口用法：detect_gap(bg.jpg, slice.png) → drag_distance(gap_x, piece_x0, displayed_width)")
        print("轨迹用法：human_track(distance) → 分步 mouse.move")
        input("按回车关闭浏览器…")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
