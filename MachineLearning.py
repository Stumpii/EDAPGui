from __future__ import annotations
from dataclasses import dataclass
import cv2
from ultralytics import YOLO
from Screen_Regions import Quad

"""
File:Machine_Learning.py

Description:
  Class for Machine Learning using Yolo26.
  Ref: https://docs.ultralytics.com/

Author: Stumpii
"""


@dataclass
class MachLeanMatch:
    """ A machine learning match. """
    class_name: str  # i.e. 'compass'
    match_pct: float  # i.e. 0.0 - 1.0
    bounding_quad: Quad  # The bounding box


class MachLearn:
    def __init__(self, ed_ap, cb):
        self.ap = ed_ap
        self.ap_ckb = cb

        self.ml_model = YOLO("runs/detect/train7/weights/best.pt")

    def predict(self, image) -> list[MachLeanMatch] | None:
        """ Performs a prediction of an image and returns the results. """
        matches: list[MachLeanMatch] = []
        # Do prediction with ML
        results = self.ml_model.predict(image, verbose=False)  # Predict on an image
        if results and len(results) == 1:
            r = results[0]
            if len(r.boxes) > 0:
                for b in r.boxes:
                    clsid = int(b.cls.item())
                    class_name = r.names[clsid]  # Class name
                    confidence = b.conf.item()  # Confidence %
                    rect_tmp = b.xyxy.tolist()  # Match as a rect
                    rect_tmp = rect_tmp[0]
                    res_quad = Quad.from_rect(rect_tmp)

                    # Add item
                    match = MachLeanMatch(class_name=class_name, match_pct=confidence, bounding_quad=res_quad)
                    matches.append(match)
                return matches
            else:
                return None
