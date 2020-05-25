import os
import traceback

import cv2
from PIL import Image

import module.config.server as server
from module.base.utils import *


class Button:
    def __init__(self, area, color, button, file=None, name=None):
        """Initialize a Button instance.

        Args:
            area (dict[tuple], tuple): Area that the button would appear on the image.
                          (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
            color (dict[tuple], tuple): Color we expect the area would be.
                           (r, g, b)
            button (dict[tuple], tuple): Area to be click if button appears on the image.
                            (upper_left_x, upper_left_y, bottom_right_x, bottom_right_y)
                            If tuple is empty, this object can be use as a checker.
        Examples:
            BATTLE_PREPARATION = Button(
                area=(1562, 908, 1864, 1003),
                color=(231, 181, 90),
                button=(1562, 908, 1864, 1003)
            )
        """
        self.server = server.server
        self.area = area[self.server] if isinstance(area, dict) else area
        self.color = color[self.server] if isinstance(color, dict) else color
        self._button = button[self.server] if isinstance(button, dict) else button
        self._button_offset = None
        self._match_init = False
        self.file = file[self.server] if isinstance(file, dict) else file
        self.image = None
        if self.file:
            self.name = os.path.splitext(os.path.split(self.file)[1])[0]
        elif name:
            self.name = name
        else:
            (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
            self.name = text[:text.find('=')].strip()

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    @property
    def button(self):
        if self._button_offset is None:
            return self._button
        else:
            return self._button_offset

    def appear_on(self, image, threshold=10):
        """Check if the button appears on the image.

        Args:
            image (PIL.Image.Image): Screenshot.
            threshold (int): Default to 10.

        Returns:
            bool: True if button appears on screenshot.
        """
        return color_similar(
            color1=get_color(image, self.area),
            color2=self.color,
            threshold=threshold
        )

    def load_color(self, image):
        """Load color from the specific area of the given image.
        This method is irreversible, this would be only use in some special occasion.

        Args:
            image: Another screenshot.

        Returns:
            tuple: Color (r, g, b).
        """
        self.color = get_color(image, self.area)
        self.image = np.array(image.crop(self.area))
        return self.color

    def ensure_template(self):
        """
        Load asset image.
        If needs to call self.match, call this first.
        """
        if not self._match_init:
            self.image = np.array(Image.open(self.file).crop(self.area).convert('RGB'))
            self._match_init = True

    def match(self, image, offset=30, threshold=0.85):
        """Detects button by template matching. To Some button, its location may not be static.

        Args:
            image: Screenshot.
            offset (int, tuple): Detection area offset.
            threshold (float): 0-1. Similarity.

        Returns:
            bool.
        """
        self.ensure_template()

        if isinstance(offset, tuple):
            offset = np.array((-offset[0], -offset[1], offset[0], offset[1]))
        else:
            offset = np.array((0, -offset, 0, offset))

        # offset = np.array((0, -offset, 0, offset))
        # offset = np.array((-offset, -offset, offset, offset))
        image = np.array(image.crop(offset + self.area))
        res = cv2.matchTemplate(self.image, image, cv2.TM_CCOEFF_NORMED)
        _, similarity, _, point = cv2.minMaxLoc(res)

        self._button_offset = area_offset(self._button, offset[:2] + np.array(point))

        return similarity > threshold


class ButtonGrid:
    def __init__(self, origin, delta, button_shape, grid_shape, name=None):
        self.origin = np.array(origin)
        self.delta = np.array(delta)
        self.button_shape = np.array(button_shape)
        self.grid_shape = np.array(grid_shape)
        if name:
            self._name = name
        else:
            (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
            self._name = text[:text.find('=')].strip()

    def __getitem__(self, item):
        base = np.round(np.array(item) * self.delta + self.origin).astype(int)
        area = tuple(np.append(base, base + self.button_shape))
        return Button(area=area, color=(), button=area, name='%s_%s_%s' % (self._name, item[0], item[1]))

    def generate(self):
        for y in range(self.grid_shape[1]):
            for x in range(self.grid_shape[0]):
                yield x, y, self[x, y]

    def buttons(self):
        return list([button for _, _, button in self.generate()])
