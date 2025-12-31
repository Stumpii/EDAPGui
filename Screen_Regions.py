from copy import copy

import numpy as np
from numpy import array, sum
import cv2
from datetime import datetime

"""
File:Screen_Regions.py    

Description:
  Class to rectangle areas of the screen to capture along with filters to apply. Includes functions to
  match a image template to the region using opencv 

Author: sumzer0@yahoo.com
"""


def scale_region(region, sub_region) -> [float, float, float, float]:
    """ Converts a sub region scale to a region scale """
    r = Quad.from_rect(region)
    sr = Quad.from_rect(sub_region)
    r.subregion_from_quad(sr)
    return r.to_rect_list()


class Screen_Regions:
    def __init__(self, screen, templ):
        self.screen = screen
        self.templates = templ

        # Define the thresholds for template matching to be consistent throughout the program
        self.compass_match_thresh = 0.50
        self.navpoint_match_thresh = 0.8
        self.target_thresh = 0.50
        self.target_occluded_thresh = 0.55
        self.sun_threshold = 125
        self.disengage_thresh = 0.35

        # array is in HSV order which represents color ranges for filtering
        self.orange_color_range   = [array([0, 130, 123]),  array([25, 235, 220])]
        self.orange_2_color_range = [array([16, 165, 220]), array([98, 255, 255])]
        self.orange_text_color_range = [array([15, 110, 150]), array([50, 255, 255])]
        self.orange_text_color_range = [array([0, 0, 0]), array([179, 255, 255])]
        self.target_occluded_range= [array([16, 31, 85]),   array([26, 160, 255])]
        self.blue_color_range     = [array([0, 28, 170]), array([180, 100, 255])]
        self.blue_sco_color_range = [array([10, 0, 0]), array([100, 150, 255])]
        self.fss_color_range      = [array([95, 210, 70]),  array([105, 255, 120])]

        self.reg = {}
        # regions with associated filter and color ranges
        # The rect is [L, T, R, B] top left x, y, and bottom right x, y in fraction of screen resolution
        self.reg['compass']   = {'rect': [0.33, 0.65, 0.46, 1.0], 'width': 1, 'height': 1, 'filterCB': self.equalize,                                'filter': None}
        self.reg['target']    = {'rect': [0.33, 0.27, 0.66, 0.70], 'width': 1, 'height': 1, 'filterCB': self.filter_by_color, 'filter': self.orange_2_color_range}   # also called destination
        self.reg['target_occluded']    = {'rect': [0.33, 0.27, 0.66, 0.70], 'width': 1, 'height': 1, 'filterCB': self.filter_by_color, 'filter': self.target_occluded_range}
        self.reg['sun']       = {'rect': [0.30, 0.30, 0.70, 0.68], 'width': 1, 'height': 1, 'filterCB': self.filter_sun, 'filter': None}
        self.reg['disengage'] = {'rect': [0.42, 0.65, 0.60, 0.80], 'width': 1, 'height': 1, 'filterCB': self.filter_by_color, 'filter': self.blue_sco_color_range}
        self.reg['sco']       = {'rect': [0.42, 0.65, 0.60, 0.80], 'width': 1, 'height': 1, 'filterCB': self.filter_by_color, 'filter': self.blue_sco_color_range}
        self.reg['fss']       = {'rect': [0.5045, 0.7545, 0.532, 0.7955], 'width': 1, 'height': 1, 'filterCB': self.equalize, 'filter': None}
        self.reg['mission_dest']  = {'rect': [0.46, 0.38, 0.65, 0.86], 'width': 1, 'height': 1, 'filterCB': self.equalize, 'filter': None}    
        self.reg['missions']    = {'rect': [0.50, 0.78, 0.65, 0.85], 'width': 1, 'height': 1, 'filterCB': self.equalize, 'filter': None}   
        self.reg['nav_panel']   = {'rect': [0.25, 0.36, 0.60, 0.85], 'width': 1, 'height': 1, 'filterCB': self.equalize, 'filter': None}  

        # convert rect from percent of screen into pixel location, calc the width/height of the area
        for i, key in enumerate(self.reg):
            xx = self.reg[key]['rect']
            self.reg[key]['rect'] = [int(xx[0]*screen.screen_width), int(xx[1]*screen.screen_height), 
                                     int(xx[2]*screen.screen_width), int(xx[3]*screen.screen_height)]
            self.reg[key]['width']  = self.reg[key]['rect'][2] - self.reg[key]['rect'][0]
            self.reg[key]['height'] = self.reg[key]['rect'][3] - self.reg[key]['rect'][1]

    def capture_region(self, screen, region_name):
        """ Just grab the screen based on the region name/rect.
        Returns an unfiltered image. """
        return screen.get_screen_region(self.reg[region_name]['rect'])

    def capture_region_filtered(self, screen, region_name, inv_col=True):
        """ Grab screen region and call its filter routine.
        Returns the filtered image. """
        scr = screen.get_screen_region(self.reg[region_name]['rect'], inv_col)
        if self.reg[region_name]['filterCB'] is None:
            # return the screen region untouched in BGRA format.
            return scr
        else:
            # return the screen region in the format returned by the filter.
            return self.reg[region_name]['filterCB'](scr, self.reg[region_name]['filter'])

    def match_template_in_region(self, region_name, templ_name, inv_col=True):
        """ Attempt to match the given template in the given region which is filtered using the region filter.
        Returns the filtered image, detail of match and the match mask. """
        img_region = self.capture_region_filtered(self.screen, region_name, inv_col)    # which would call, reg.capture_region('compass') and apply defined filter
        img_templ = self.templates.template[templ_name]['image']

        # now = datetime.now()
        # x = now.strftime("%Y-%m-%d %H-%M-%S.%f")[:-3]  # Date time with mS.
        # cv2.imwrite(f'test/match/{templ_name} {x} region.png', img_region)
        # cv2.imwrite(f'test/match/{templ_name} {x} templ.png', img_templ)

        match = cv2.matchTemplate(img_region, img_templ, cv2.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)
        return img_region, (minVal, maxVal, minLoc, maxLoc), match

    def match_template_in_region_x3(self, region_name, templ_name, inv_col=True):
        """ Attempt to match the given template in the given region which is unfiltered.
        The region's image is split into separate HSV channels, each channel tested and the best result kept.
        Returns the image, detail of match and the match mask. """
        img_region = self.screen.get_screen_region(self.reg[region_name]['rect'], rgb=False)
        templ = self.templates.template[templ_name]['image']

        # Convert to HSV and split.
        img_hsv = cv2.cvtColor(img_region, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(img_hsv)
        # hsv_comb = np.concatenate((h, s, v), axis=1)  # Combine 3 images
        # cv2.imshow("Split HSV", hsv_comb)

        # Perform matches
        match_h = cv2.matchTemplate(h, templ, cv2.TM_CCOEFF_NORMED)
        match_s = cv2.matchTemplate(s, templ, cv2.TM_CCOEFF_NORMED)
        match_v = cv2.matchTemplate(v, templ, cv2.TM_CCOEFF_NORMED)
        (minVal_h, maxVal_h, minLoc_h, maxLoc_h) = cv2.minMaxLoc(match_h)
        (minVal_s, maxVal_s, minLoc_s, maxLoc_s) = cv2.minMaxLoc(match_s)
        (minVal_v, maxVal_v, minLoc_v, maxLoc_v) = cv2.minMaxLoc(match_v)
        # match_comb = np.concatenate((match_h, match_s, match_v), axis=1)  # Combine 3 images
        # cv2.imshow("Split Matches", match_comb)

        # Get best result
        # V is likely the best match, so check it first
        if maxVal_v > maxVal_s and maxVal_v > maxVal_h:
            return img_region, (minVal_v, maxVal_v, minLoc_v, maxLoc_v), match_v
        # S is likely the 2nd best match, so check it
        if maxVal_s > maxVal_h:
            return img_region, (minVal_s, maxVal_s, minLoc_s, maxLoc_s), match_s
        # H must be the best match
        return img_region, (minVal_h, maxVal_h, minLoc_h, maxLoc_h), match_h

    def match_template_in_image(self, image, template):
        """ Attempt to match the given template in the (unfiltered) image.
        Returns the original image, detail of match and the match mask. """
        match = cv2.matchTemplate(image, self.templates.template[template]['image'], cv2.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(match)
        return image, (minVal, maxVal, minLoc, maxLoc), match     

    def match_template_in_image_x3(self, image, templ_name):
        """ Attempt to match the given template in the (unfiltered) image.
        The image is split into separate HSV channels, each channel tested and the best result kept.
        Returns the original image, detail of match and the match mask. """
        templ = self.templates.template[templ_name]['image']

        # Convert to HSV and split.
        img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(img_hsv)
        # hsv_comb = np.concatenate((h, s, v), axis=1)  # Combine 3 images
        # cv2.imshow("Split HSV", hsv_comb)

        # Perform matches
        match_h = cv2.matchTemplate(h, templ, cv2.TM_CCOEFF_NORMED)
        match_s = cv2.matchTemplate(s, templ, cv2.TM_CCOEFF_NORMED)
        match_v = cv2.matchTemplate(v, templ, cv2.TM_CCOEFF_NORMED)
        (minVal_h, maxVal_h, minLoc_h, maxLoc_h) = cv2.minMaxLoc(match_h)
        (minVal_s, maxVal_s, minLoc_s, maxLoc_s) = cv2.minMaxLoc(match_s)
        (minVal_v, maxVal_v, minLoc_v, maxLoc_v) = cv2.minMaxLoc(match_v)
        # match_comb = np.concatenate((match_h, match_s, match_v), axis=1)  # Combine 3 images
        # cv2.imshow("Split Matches", match_comb)

        # Get best result
        # V is likely the best match, so check it first
        if maxVal_v > maxVal_s and maxVal_v > maxVal_h:
            return image, (minVal_v, maxVal_v, minLoc_v, maxLoc_v), match_v
        # S is likely the 2nd best match, so check it
        if maxVal_s > maxVal_h:
            return image, (minVal_s, maxVal_s, minLoc_s, maxLoc_s), match_s
        # H must be the best match
        return image, (minVal_h, maxVal_h, minLoc_h, maxLoc_h), match_h

    def equalize(self, image=None, noOp=None):
        # Load the image in greyscale
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # create a CLAHE object (Arguments are optional).  Histogram equalization, improves constrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        img_out = clahe.apply(img_gray)

        return img_out
        
    def filter_by_color(self, image, color_range):
        """Filters an image based on a given color range.
        Returns the filtered image. Pixels within the color range are returned
        their original color, otherwise black."""
        # converting from BGR to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # filter passed in color low, high
        filtered = cv2.inRange(hsv, color_range[0], color_range[1])

        return filtered
 
    # not used
    def filter_bright(self, image=None, noOp=None):
        equalized = self.equalize(image)
        equalized = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)    #hhhmm, equalize() already converts to gray
        equalized = cv2.cvtColor(equalized, cv2.COLOR_BGR2HSV)
        filtered  = cv2.inRange(equalized, array([0, 0, 215]), array([0, 0, 255]))  #only high value

        return filtered
    
    def set_sun_threshold(self, thresh):
        self.sun_threshold = thresh

    # need to compare filter_sun with filter_bright
    def filter_sun(self, image=None, noOp=None):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # set low end of filter to 25 to pick up the dull red Class L stars
        (thresh, blackAndWhiteImage) = cv2.threshold(hsv, self.sun_threshold, 255, cv2.THRESH_BINARY)

        return blackAndWhiteImage

    # percent the image is white
    def sun_percent(self, screen):
        blackAndWhiteImage = self.capture_region_filtered(screen, 'sun')
 
        wht = sum(blackAndWhiteImage == 255)     
        blk = sum(blackAndWhiteImage != 255)

        result = int((wht / (wht+blk))*100)

        return result


class Point:
    """Creates a point on a coordinate plane with values x and y."""
    def __init__(self, x, y):
        """Defines x and y variables"""
        self.x: float = x
        self.y: float = y

    def __str__(self):
        return "Point(%s, %s)" % (self.x, self.y)

    def get_x(self) -> float:
        return self.x

    def get_y(self) -> float:
        return self.y

    def to_list(self) -> [float, float]:
        return [self.x, self.y]

    @classmethod
    def from_xy(cls, xy_tuple: (float, float)):
        """ From (x, y) """
        return cls(xy_tuple[0], xy_tuple[1])

    @classmethod
    def from_list(cls, xy_list: [float, float]):
        """ From (x, y) """
        return cls(xy_list[0], xy_list[1])


class Quad:
    """ Represents a quadrilateral (a four-sided polygon that has four edges and four vertices).
    It can be classified into various types, such as squares, rectangles, trapezoids, and rhombuses.
    """
    def __init__(self, p1: Point = None, p2: Point = None, p3: Point = None, p4: Point = None):
        self.pt1: Point = p1
        self.pt2: Point = p2
        self.pt3: Point = p3
        self.pt4: Point = p4

    @classmethod
    def from_list(cls, pt_list: [[float, float], [float, float], [float, float], [float, float]]):
        """ Creates a quad from a list of points as
        [[left, top], [right, top], [right, bottom], [left, bottom]]."""
        return cls(Point.from_list(pt_list[0]), Point.from_list(pt_list[1]),
                   Point.from_list(pt_list[2]), Point.from_list(pt_list[3]))

    @classmethod
    def from_rect(cls, pt_list: [float, float, float, float]):
        """ Creates a quad from a list of points as [left, top, right, bottom] """
        return cls(Point(pt_list[0], pt_list[1]), Point(pt_list[2], pt_list[1]),
                   Point(pt_list[2], pt_list[3]), Point(pt_list[0], pt_list[3]))

    def to_rect_list(self, round_dp: int = -1) -> [float, float, float, float]:
        """ Returns the bounds of the quadrilateral as a list of values [left, top, right, bottom].
        @param: round_dp: If >=0, the number of decimal places to round numbers to, otherwise no rounding.
        """
        if round_dp < 0:
            return [self.get_left(), self.get_top(), self.get_right(), self.get_bottom()]
        else:
            return [round(self.get_left(), round_dp), round(self.get_top(), round_dp),
                    round(self.get_right(), round_dp), round(self.get_bottom(), round_dp)]

    def to_list(self) -> [[float, float], [float, float], [float, float], [float, float]]:
        """ Returns the list of points of the quadrilateral as
        [[left, top], [right, top], [right, bottom], [left, bottom]]."""
        return [self.pt1.to_list(), self.pt2.to_list(), self.pt3.to_list(), self.pt4.to_list()]

    def get_left(self) -> float:
        """ Returns the value of the left most point. """
        return min(self.pt1.x, self.pt2.x, self.pt3.x, self.pt4.x)

    def get_top(self) -> float:
        """ Returns the value of the top most point. """
        return min(self.pt1.y, self.pt2.y, self.pt3.y, self.pt4.y)

    def get_right(self) -> float:
        """ Returns the value of the right most point. """
        return max(self.pt1.x, self.pt2.x, self.pt3.x, self.pt4.x)

    def get_bottom(self) -> float:
        """ Returns the value of the bottom most point. """
        return max(self.pt1.y, self.pt2.y, self.pt3.y, self.pt4.y)

    def get_width(self):
        """Returns the maximum width."""
        return self.get_right() - self.get_left()

    def get_height(self):
        """Returns the maximum height."""
        return self.get_bottom() - self.get_top()

    def get_bounds(self) -> (Point, Point):
        """ Returns the bounds of the quadrilateral as a rectangle defined by two points,
        the top-left and bottom-right."""
        return Point(self.get_left(), self.get_top()), Point(self.get_right(), self.get_bottom())

    def get_center(self) -> Point:
        cx = (self.pt1.x + self.pt2.x + self.pt3.x + self.pt4.x) / 4
        cy = (self.pt1.y + self.pt2.y + self.pt3.y + self.pt4.y) / 4
        return Point(cx, cy)

    def scale(self, fx: float, fy: float):
        """ Scales the quad from the center.
        @param fy: Scaling in the Y direction.
        @param fx: Scaling in the X direction.
        """
        center = self.get_center()
        self.pt1 = self._scale_point(self.pt1, center, fx, fy)
        self.pt2 = self._scale_point(self.pt2, center, fx, fy)
        self.pt3 = self._scale_point(self.pt3, center, fx, fy)
        self.pt4 = self._scale_point(self.pt4, center, fx, fy)

    def subregion_from_quad(self, quad):
        """ Crops the quad as region specified by the % (0.0-1.0) inputs.
        NOTE: This assumes that the quad is a rectangle or square. Won't work with other shapes!
        Example: An input of [0.0, 0.0, 1.0, 1.0] returns the quad unchanged.
        Example: An input of [0.0, 0.0, 0.25, 0.25] returns the top left quarter of the quad.
        @param quad: A quad.
        """
        new_l = (quad.get_left() * self.get_width()) + self.get_left()
        new_t = (quad.get_top() * self.get_height()) + self.get_top()
        new_r = (quad.get_right() * self.get_width()) + self.get_left()
        new_b = (quad.get_bottom() * self.get_height()) + self.get_top()

        self.pt1 = Point(new_l, new_t)
        self.pt2 = Point(new_r, new_t)
        self.pt3 = Point(new_r, new_b)
        self.pt4 = Point(new_l, new_b)

    def scale_from_origin(self, fx: float, fy: float):
        """ Scales the quad from the origin (0,0).
        @param fy: Scaling in the Y direction.
        @param fx: Scaling in the X direction.
        """
        origin = Point(0, 0)
        self.pt1 = self._scale_point(self.pt1, origin, fx, fy)
        self.pt2 = self._scale_point(self.pt2, origin, fx, fy)
        self.pt3 = self._scale_point(self.pt3, origin, fx, fy)
        self.pt4 = self._scale_point(self.pt4, origin, fx, fy)

    def offset(self, dx: float, dy: float):
        """ Offsets (moves) the quad by the given amount.
        @param dx: The amount to move in the x direction.
        @param dy: The amount to move in the y direction.
        """
        self.pt1 = self._offset_point(self.pt1, dx, dy)
        self.pt2 = self._offset_point(self.pt2, dx, dy)
        self.pt3 = self._offset_point(self.pt3, dx, dy)
        self.pt4 = self._offset_point(self.pt4, dx, dy)

    @staticmethod
    def _scale_point(pt: Point, center: Point, fx: float, fy: float) -> Point:
        return Point(
            center.x + (pt.x - center.x) * fx,
            center.y + (pt.y - center.y) * fy
        )

    @staticmethod
    def _offset_point(pt: Point, dx: float, dy: float) -> Point:
        """ Offsets the point.
        Using this instead of calling offset on the point directly allows shallow copy of the quad."""
        return Point(pt.x + dx, pt.y + dy)

    def __str__(self):
        return (f"Quadrilateral:\n"
                f" pt1: ({self.pt1.x}, {self.pt1.y})\n"
                f" pt2: ({self.pt2.x}, {self.pt2.y})\n"
                f" pt3: ({self.pt3.x}, {self.pt3.y})\n"
                f" pt4: ({self.pt4.x}, {self.pt4.y})")




