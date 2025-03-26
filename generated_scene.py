
from manim import *

class GeneratedScene(MovingCameraScene):
    def get_final_camera_setup(self):
        # Create all mobjects first
        title = Tex(r"Set Theory and Analysis Snippets", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title

        element0 = Tex(r"$(\bigcup_{i \in I} E_i)^c \subset \bigcap_{i \in I} E_i^c$", font_size=40).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element0)
        prev_mobject = element0

        element1 = Tex(r"Let $I = \phi$. Then the LHS $= \phi^c = X$", font_size=40).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element1)
        prev_mobject = element1

        element2 = Tex(r"$\max(\chi_{E}(x), \chi_{F}(x)) = 0$ then both $\chi_{E}(x)$, $\chi_{F}(x)$ must be zero. Hence $\chi_{E \cup F}(x) = 0$", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element2)
        prev_mobject = element2

        element3 = Tex(r"If max value is $1$, then either one or both $\chi_{E} = 1$. $\chi_{F}$ must be $1$ and so $\chi_{E \cup F}$ will also $= 1$.", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element3)
        prev_mobject = element3

        element4 = Tex(r"For every $0 < \alpha < 1$, we can find $N \ni$ $\alpha < 1-\frac{1}{n}$ for all $n \ge N$. This shows that $\alpha \in E_* \implies \alpha \in E$", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element4)
        prev_mobject = element4

        element5 = Tex(r"In general $E_* \subset E^*$.", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element5)
        prev_mobject = element5

        # Group all content elements
        content = VGroup(*content_elements)
        self.add(title)
        title.set_opacity(0)
        self.camera.auto_zoom([title], margin=1)
        current_content = [title]
        for element in content_elements[1:]:
            self.add(element)
            element.set_opacity(0)
            current_content.append(element)
        self.play(
            self.camera.auto_zoom(
                content,
                margin=0.5,
                animate=True
            ).build(),
            run_time=2
        )
        self.camera.frame.save_state()
        self.camera.auto_zoom(content, margin=0.5)
        final_frame_center = self.camera.frame.get_center()
        final_focal_width = self.camera.frame.get_width()
        self.camera.frame.restore()
        return final_frame_center, final_focal_width

    def construct(self):
        # Get the final camera settings from a silent run
        final_center, final_width = self.get_final_camera_setup()
        title = Tex(r"{title}", font_size=50).to_edge(UP)
        content_elements = [title]
        prev_mobject = title

        element0 = Tex(r"$(\bigcup_{i \in I} E_i)^c \subset \bigcap_{i \in I} E_i^c$", font_size=40).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element0)
        prev_mobject = element0

        element1 = Tex(r"Let $I = \phi$. Then the LHS $= \phi^c = X$", font_size=40).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element1)
        prev_mobject = element1

        element2 = Tex(r"$\max(\chi_{E}(x), \chi_{F}(x)) = 0$ then both $\chi_{E}(x)$, $\chi_{F}(x)$ must be zero. Hence $\chi_{E \cup F}(x) = 0$", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element2)
        prev_mobject = element2

        element3 = Tex(r"If max value is $1$, then either one or both $\chi_{E} = 1$. $\chi_{F}$ must be $1$ and so $\chi_{E \cup F}$ will also $= 1$.", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element3)
        prev_mobject = element3

        element4 = Tex(r"For every $0 < \alpha < 1$, we can find $N \ni$ $\alpha < 1-\frac{1}{n}$ for all $n \ge N$. This shows that $\alpha \in E_* \implies \alpha \in E$", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element4)
        prev_mobject = element4

        element5 = Tex(r"In general $E_* \subset E^*$.", font_size=36).next_to(prev_mobject, DOWN, buff=0.5)
        content_elements.append(element5)
        prev_mobject = element5

        content = VGroup(*content_elements)
        self.camera.frame.move_to(final_center)
        self.camera.frame.set_width(final_width)
        self.play(Write(title))
        self.wait(1)

        self.play(Write(element0))
        self.wait(1)

        self.play(Write(element1))
        self.wait(1)

        self.play(Write(element2))
        self.wait(1)

        self.play(Write(element3))
        self.wait(1)

        self.play(Write(element4))
        self.wait(1)

        self.play(Write(element5))
        self.wait(1)

        self.wait(2)
