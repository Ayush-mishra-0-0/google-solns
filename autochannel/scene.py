"""Data-driven Manim scenes: no LLM-generated Python is executed.

Run only through autochannel.pipeline, which validates the storyboard first.
The spec contains both beat content and per-beat narration durations.
"""
import json
import os
from manim import *
import numpy as np

BG = "#0B1120"
FG = "#F8FAFC"
ACCENT = "#22D3EE"
GOLD = "#FBBF24"
PANEL = "#17233C"


def clean_text(value, limit=180):
    # The planner enforces bounds too; this is a render-time fallback.
    return str(value or "").strip()[:limit]


def word_wrap(value, max_chars=42):
    words = clean_text(value, 240).split()
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if len(test) > max_chars and line:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return "\n".join(lines[:6])


class AutoChannelScene(Scene):
    def construct(self):
        self.camera.background_color = BG
        with open(os.environ["AUTOCHANNEL_SPEC"], encoding="utf-8") as handle:
            spec = json.load(handle)
        beats = spec["beats"]
        durations = spec["durations"]
        for index, (beat, duration) in enumerate(zip(beats, durations)):
            self.clear()
            self.show_beat(beat, index + 1, len(beats), float(duration))

    def shell(self, heading, step, total):
        top = Text(clean_text(heading, 70), color=FG, font_size=37, weight=BOLD)
        top.scale_to_fit_width(11.8)
        top.to_edge(UP, buff=0.58)
        underline = Line(LEFT * 5.9, RIGHT * 5.9, color=ACCENT, stroke_width=3)
        underline.next_to(top, DOWN, buff=0.22)
        footer = Text(f"{step:02d}/{total:02d}", font_size=18, color=GRAY_B).to_corner(DR, buff=0.35)
        return VGroup(top, underline, footer)

    def caption(self, body):
        t = Text(word_wrap(body, 66), font_size=28, color=FG, line_spacing=1.2)
        t.scale_to_fit_width(11.5)
        t.to_edge(DOWN, buff=0.65)
        return t

    def equation_layout(self, beat):
        equation = beat.get("equation", "")
        if not equation:
            raise ValueError("equation layout requires equation")
        formula = MathTex(equation, font_size=74, color=GOLD)
        formula.scale_to_fit_width(10.8)
        frame = SurroundingRectangle(formula, buff=0.5, color=ACCENT, stroke_width=2)
        return VGroup(formula, frame).move_to(UP * 0.2)

    def comparison_layout(self, beat):
        left = clean_text(beat.get("left", ""), 100)
        right = clean_text(beat.get("right", ""), 100)
        if not left or not right:
            raise ValueError("comparison layout requires left and right")
        panels = []
        for i, value in enumerate((left, right)):
            rect = RoundedRectangle(width=5.7, height=3.3, corner_radius=0.23,
                                    fill_color=PANEL, fill_opacity=1,
                                    stroke_width=2, stroke_color=(ACCENT if i == 0 else GOLD))
            words = Text(word_wrap(value, 24), color=FG, font_size=30, line_spacing=1.2)
            words.scale_to_fit_width(4.9)
            words.scale_to_fit_height(2.5)
            words.move_to(rect)
            panels.append(VGroup(rect, words))
        return VGroup(*panels).arrange(RIGHT, buff=0.55).move_to(UP * 0.05)

    def graph_layout(self, beat):
        name = beat.get("curve", "sin")
        functions = {
            "sin": lambda x: np.sin(x),
            "cos": lambda x: np.cos(x),
            "quadratic": lambda x: x * x / 4,
            "exponential": lambda x: np.exp(x) / 5,
            "normal": lambda x: np.exp(-(x * x) / 2),
        }
        if name not in functions:
            raise ValueError("Unknown graph family")
        axes = Axes(x_range=[-4, 4, 2], y_range=[-2, 5, 1],
                    x_length=9.1, y_length=3.5, axis_config={"color": GRAY_B},
                    tips=False)
        curve = axes.plot(functions[name], x_range=[-4, 4], color=GOLD)
        return VGroup(axes, curve).move_to(UP * 0.1)

    def timeline_layout(self, beat):
        labels = beat.get("steps") or []
        if not (2 <= len(labels) <= 4):
            raise ValueError("timeline layout requires 2-4 steps")
        dots = VGroup(*[Dot(radius=0.12, color=ACCENT) for _ in labels])
        dots.arrange(RIGHT, buff=2.6).move_to(UP * 0.15)
        segments = VGroup(*[
            Line(dots[i].get_center(), dots[i+1].get_center(),
                 stroke_width=3, color=GRAY_B) for i in range(len(dots)-1)
        ])
        texts = VGroup(*[
            Text(word_wrap(label, 14), font_size=24, color=FG)
            .scale_to_fit_width(2.4).next_to(dot, DOWN, buff=0.25)
            for label, dot in zip(labels, dots)
        ])
        return VGroup(segments, dots, texts)

    def concept_layout(self, beat):
        text = Text(word_wrap(beat.get("body", ""), 39),
                    color=FG, font_size=46, line_spacing=1.3)
        text.scale_to_fit_width(9.6)
        text.scale_to_fit_height(3.8)
        bg = RoundedRectangle(width=11.1, height=4.0, corner_radius=0.35,
                              fill_color=PANEL, fill_opacity=1,
                              stroke_color=ACCENT, stroke_width=2)
        return VGroup(bg, text.move_to(bg)).move_to(UP * 0.15)

    def show_beat(self, beat, step, total, duration):
        # Every beat has its own narration track, so visual time exactly matches audio time.
        style = beat["layout"]
        shell = self.shell(beat["heading"], step, total)
        visuals = {
            "equation": self.equation_layout,
            "comparison": self.comparison_layout,
            "graph": self.graph_layout,
            "timeline": self.timeline_layout,
            "concept": self.concept_layout,
        }[style](beat)
        footer = self.caption(beat.get("body", ""))
        if style == "concept":
            footer = VGroup()  # avoid duplicating the main copy
        head_time = min(0.65, duration * 0.10)
        visual_time = min(1.45, duration * 0.22)
        self.play(FadeIn(shell, shift=DOWN * 0.1), run_time=head_time)
        self.play(FadeIn(visuals, shift=UP * 0.15), run_time=visual_time)
        tail_time = 0
        if len(footer):
            tail_time = min(0.45, duration * 0.08)
            self.play(FadeIn(footer), run_time=tail_time)
        self.wait(max(0.1, duration - head_time - visual_time - tail_time))
