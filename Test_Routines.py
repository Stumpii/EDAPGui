import logging
import os

from EDKeys import EDKeys
from EDWayPoint import EDWayPoint
#from NavPanel import NavPanel
from OCR import OCR
from Screen_Regions import *
from Overlay import *
from Screen import *
from Image_Templates import *
from time import sleep
import numpy as np

from Voice import Voice

"""
File:Test_Routines.py    

Description:
  Class to allow testing 
"""


def main():
    # Uncomment one tests to be performed as each runs in a loop until exited.
    # Run this file instead of the main EDAPGUI file.
    logger.setLevel(logging.DEBUG)  # Default to log all debug when running this file.

    # Rescale screenshots from the user scaling (i.e. 1920x1080 [0.75,0.75]
    # to the default scaling of 3440x1440 [1.0, 1.0]. Note the scaling is by
    # the ratio, not the resolution. Refer to Screen.py for resolution to
    # ratio conversions.
    # This only needs to be competed for new screenshots that were not take
    # at 3440x1440. Once complete, remove the original images and move the
    # converted images to relevant test folder.
    #
    # Does NOT require Elite Dangerous to be running.
    # ======================================================================
    # rescale_screenshots('test/images-to-rescale', 0.76, 0.76)

    # Shows filtering and matching for the specified region...
    # Requires Elite Dangerous to be running.
    # ========================================================
    # template_matching_test('compass', 'compass')
    # template_matching_test('compass','navpoint')
    # template_matching_test('target', 'target')
    # template_matching_test('target_occluded', 'target_occluded')

    # More complicated specific test cases...
    # =======================================
    # Requires Elite Dangerous to be running.
    # compass_test()

    # Shows regions on the Elite window...
    # Requires Elite Dangerous to be running.
    # =======================================
    wanted_regions = ["compass", "target", "nav_panel", "disengage", "fss", "sun"]
    wanted_regions = ["compass", "target", "nav_panel", "disengage"]  # The more common regions for navigation
    # show_regions(wanted_regions)

    # HSV Tester...
    #
    # Does NOT require Elite Dangerous to be running.
    # ===============================================
    # hsv_tester("test/compass/Screenshot 2024-07-04 20-01-49.png")
    # hsv_tester("test/disengage/Screenshot 2024-08-13 21-32-58.png")
    # hsv_tester("test/navpoint/Screenshot 2024-07-04 20-02-01.png")
    # hsv_tester("test/navpoint-behind/Screenshot 2024-07-04 20-01-33.png")
    # hsv_tester("test/target/Screenshot 2024-07-04 23-22-02.png")
    # hsv_tester("test/nav panel location_panel - Copy.png")

    # Testing of OCR...
    #
    # Does NOT require Elite Dangerous to be running.
    # =====================================================================================
    # image_ocr_test('test/dest-sirius-atmos/','mission_dest_col')
    # image_ocr_alltext_test('test/dest-sirius-atmos/','mission_dest_col')
    # image_ocr_test('test/dest-sirius-atmos/', 'nav_panel')
    # get_highlighted_item_in_image("test/nav panel location_panel - Copy.png")

    # Testing of Nav Panel OCR...
    #
    # Does NOT require Elite Dangerous to be running.
    # =====================================================================================
    #nav_panel_display_all_text_test('test/nav-panel/')
    #nav_panel_selected_item_text('test/nav-panel/')
    # nav_panel_lock_station("QUAID'S VISION")
    # nav_panel_lock_station("SMITH'S OBLIGATION")
    # nav_panel_request_docking()

def draw_match_rect(img, pt1, pt2, color, thick):
    """ Utility function to add a rectangle to an image. """
    wid = pt2[0] - pt1[0]
    hgt = pt2[1] - pt1[1]

    if wid < 20:
        # cv2.rectangle(screen, pt, (pt[0] + compass_width, pt[1] + compass_height),  (0,0,255), 2)
        cv2.rectangle(img, pt1, pt2, color, thick)
    else:
        len_wid = wid / 5
        len_hgt = hgt / 5
        half_wid = wid / 2
        half_hgt = hgt / 2
        tic_len = thick - 1
        # top
        cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0] + len_wid), int(pt1[1])), color, thick)
        cv2.line(img, (int(pt1[0] + (2 * len_wid)), int(pt1[1])), (int(pt1[0] + (3 * len_wid)), int(pt1[1])), color, 1)
        cv2.line(img, (int(pt1[0] + (4 * len_wid)), int(pt1[1])), (int(pt2[0]), int(pt1[1])), color, thick)
        # top tic
        cv2.line(img, (int(pt1[0] + half_wid), int(pt1[1])), (int(pt1[0] + half_wid), int(pt1[1]) - tic_len), color,
                 thick)
        # bot
        cv2.line(img, (int(pt1[0]), int(pt2[1])), (int(pt1[0] + len_wid), int(pt2[1])), color, thick)
        cv2.line(img, (int(pt1[0] + (2 * len_wid)), int(pt2[1])), (int(pt1[0] + (3 * len_wid)), int(pt2[1])), color, 1)
        cv2.line(img, (int(pt1[0] + (4 * len_wid)), int(pt2[1])), (int(pt2[0]), int(pt2[1])), color, thick)
        # bot tic
        cv2.line(img, (int(pt1[0] + half_wid), int(pt2[1])), (int(pt1[0] + half_wid), int(pt2[1]) + tic_len), color,
                 thick)
        # left
        cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0]), int(pt1[1] + len_hgt)), color, thick)
        cv2.line(img, (int(pt1[0]), int(pt1[1] + (2 * len_hgt))), (int(pt1[0]), int(pt1[1] + (3 * len_hgt))), color, 1)
        cv2.line(img, (int(pt1[0]), int(pt1[1] + (4 * len_hgt))), (int(pt1[0]), int(pt2[1])), color, thick)
        # left tic
        cv2.line(img, (int(pt1[0]), int(pt1[1] + half_hgt)), (int(pt1[0] - tic_len), int(pt1[1] + half_hgt)), color,
                 thick)
        # right
        cv2.line(img, (int(pt2[0]), int(pt1[1])), (int(pt2[0]), int(pt1[1] + len_hgt)), color, thick)
        cv2.line(img, (int(pt2[0]), int(pt1[1] + (2 * len_hgt))), (int(pt2[0]), int(pt1[1] + (3 * len_hgt))), color, 1)
        cv2.line(img, (int(pt2[0]), int(pt1[1] + (4 * len_hgt))), (int(pt2[0]), int(pt2[1])), color, thick)
        # right tic
        cv2.line(img, (int(pt2[0]), int(pt1[1] + half_hgt)), (int(pt2[0] + tic_len), int(pt1[1] + half_hgt)), color,
                 thick)


def compass_test():
    """ Performs a compass test. """
    scr = Screen()
    templ = Image_Templates(scr.scaleX, scr.scaleY)
    scr_reg = Screen_Regions(scr, templ)

    while True:
        region_name = 'compass'
        template = 'compass'

        img_region, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region(region_name, template)
        pt = maxLoc
        c_wid = scr_reg.templates.template['compass']['width']
        c_hgt = scr_reg.templates.template['compass']['height']
        draw_match_rect(img_region, pt, (pt[0] + c_wid, pt[1] + c_hgt), (0, 0, 255), 2)
        cv2.putText(img_region, f'Match: {maxVal:5.2f}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(region_name, img_region)
        cv2.imshow(template + ' match', match)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break


def template_matching_test(region_name, template):
    """ To test the template matching. Using the provided region and template.
    :param region_name: The name of the region with the required filter to apply to the image.
    :param template: The name of the template to find in each file being tested. """
    scr = Screen()
    templ = Image_Templates(scr.scaleX, scr.scaleY)
    scr_reg = Screen_Regions(scr, templ)

    while True:
        img_region, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region(region_name, template)
        cv2.putText(img_region, f'Match: {maxVal:5.2f}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(region_name, img_region)
        cv2.imshow(template + ' match', match)

        key = cv2.waitKey(10)
        if key == 27:  # ESC
            break


# def nav_panel_display_all_text_test(directory):
#     """ OCR all the image files in the given folder.
#         :param directory: The directory to process.
#     """
#     scr = Screen()
#     ocr = OCR(scr)
#     keys = EDKeys()
#     keys.activate_window = True  # Helps with single steps testing
#     nav_pnl = NavPanel(scr, keys)
#     nav_pnl.using_screen = False
#
#     directory_out = os.path.join(directory, 'out')
#     if not os.path.exists(directory_out):
#         os.makedirs(directory_out)
#
#     for filename in os.listdir(directory_out):
#         os.remove(os.path.join(directory_out, filename))
#
#     for filename in os.listdir(directory):
#         if filename.endswith(".png"):
#             image_path = os.path.join(directory, filename)
#             image_out_path = os.path.join(directory_out, filename)
#             text_out_path = os.path.join(directory_out, filename.replace('png', 'txt'))
#
#             # Load image
#             orig_image = cv2.imread(image_path)
#             nav_pnl.screen_image = orig_image
#
#             # Extract region
#             image = nav_pnl.capture_region_straightened('nav_panel')
#
#             ocr_data, ocr_textlist = ocr.image_ocr(image)
#
#             draw_bounding_boxes(image, ocr_data, 0.25)
#             cv2.imwrite(image_out_path, image)
#
#
# def nav_panel_selected_item_text(directory):
#     """ OCR all the image files in the given folder. Images are filtered using the filter defined for the region.
#         :param directory: The directory to process.
#     """
#     scr = Screen()
#     keys = EDKeys()
#     keys.activate_window = True  # Helps with single steps testing
#
#     nav_pnl = NavPanel(scr, keys)
#     nav_pnl.using_screen = False
#     ocr = OCR(scr)
#
#     directory_out = os.path.join(directory, 'out_selected')
#     if not os.path.exists(directory_out):
#         os.makedirs(directory_out)
#
#     for filename in os.listdir(directory_out):
#         os.remove(os.path.join(directory_out, filename))
#
#     for filename in os.listdir(directory):
#         if filename.endswith(".png"):
#             image_path = os.path.join(directory, filename)
#             image_out_path = os.path.join(directory_out, filename)
#             text_out_path = os.path.join(directory_out, filename.replace('png', 'txt'))
#
#             # Load image
#             orig_image = cv2.imread(image_path)
#             nav_pnl.screen_image = orig_image
#
#             # Get the location panel image
#             loc_panel = nav_pnl.capture_location_panel()
#
#             # Find the selected item/menu (solid orange)
#             #img_item = nav_pnl.get_selected_location_image(image, 100, 10)
#             # if img_item is not None:
#             #crop_with_border = cv2.copyMakeBorder(img_item, 40, 20, 20, 20, cv2.BORDER_CONSTANT)
#             #ocr_data, ocr_textlist = nav_pnl.get_selected_location_data(crop_with_border, 100, 10)
#
#             # TODO - ocr min size
#             image, ocr_data, ocr_textlist = ocr.get_highlighted_item_data(loc_panel, 100, 10)
#             if image is not None:
#                 draw_bounding_boxes(image, ocr_data, 0.25)
#                 cv2.imwrite(image_out_path, image)
#                 # cv2.imshow("ocr", crop_with_border)
#
#                 # key = cv2.waitKey(10)
#                 # if key == 27:  # ESC
#                 #     break
#

def show_regions(region_names):
    """ Draw a rectangle indicating the given region on the Elite Dangerous window.
        :param region_names: An array names of the regions to indicate on screen (i.e. ["compass", "target"])."""
    ov = Overlay("", 1)
    scr = Screen()
    templ = Image_Templates(scr.scaleX, scr.scaleY)
    scrReg = Screen_Regions(scr, templ)

    overlay_colors = [
        (255, 255, 255),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
        (192, 192, 192),
        (128, 128, 128),
        (128, 0, 0),
        (128, 128, 0),
        (0, 128, 0),
        (128, 0, 128),
        (0, 128, 128),
        (0, 0, 128)
    ]

    for i, key in enumerate(scrReg.reg):
        #tgt = scrReg.capture_region_filtered(scr, key)
        #print(key)
        #print(scrReg.reg[key])
        if key in region_names:
            ov.overlay_rect(key, (scrReg.reg[key]['rect'][0], scrReg.reg[key]['rect'][1]),
                            (scrReg.reg[key]['rect'][2], scrReg.reg[key]['rect'][3]),
                            overlay_colors[i + 1], 2)
            ov.overlay_floating_text(key, key, scrReg.reg[key]['rect'][0], scrReg.reg[key]['rect'][1],
                                     overlay_colors[i + 1])

    ov.overlay_paint()

    sleep(10)
    ov.overlay_quit()
    sleep(2)


def show_all_regions(regions):
    """ Draw a rectangle indicating the given region on the Elite Dangerous window.
        :param regions: An array names of the regions to indicate on screen (i.e. ["compass", "target"])."""
    ov = Overlay("", 1)
    scr = Screen()

    overlay_colors = [
        (255, 255, 255),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (0, 255, 255),
        (255, 0, 255),
        (192, 192, 192),
        (128, 128, 128),
        (128, 0, 0),
        (128, 128, 0),
        (0, 128, 0),
        (128, 0, 128),
        (0, 128, 128),
        (0, 0, 128)
    ]

    for i, key in enumerate(regions):
        rect = regions[key]['rect']
        rect_abs = scr.screen_pct_to_abs(rect)

        ov.overlay_rect(key, (rect_abs[0], rect_abs[1]), (rect_abs[2], rect_abs[3]), overlay_colors[i + 1], 2)
        ov.overlay_floating_text(key, key, rect_abs[0], rect_abs[1], overlay_colors[i + 1])

    ov.overlay_paint()

    sleep(10)
    ov.overlay_quit()
    sleep(2)


def hsv_tester(image_path):
    """ Brings up a HSV test window with sliders to check the 'inRange' function on the provided image.
        Change the default values below where indicated to the values associated with the appropriate
        template in image_template.py.
        :param image_path: The file path of the image to test. """
    cv2.namedWindow("Trackbars", cv2.WINDOW_NORMAL)  # cv2.WINDOW_AUTOSIZE)

    cv2.createTrackbar("L - H", "Trackbars", 0, 179, callback)
    cv2.createTrackbar("L - S", "Trackbars", 0, 255, callback)
    cv2.createTrackbar("L - V", "Trackbars", 0, 255, callback)
    cv2.createTrackbar("U - H", "Trackbars", 255, 179, callback)
    cv2.createTrackbar("U - S", "Trackbars", 255, 255, callback)
    cv2.createTrackbar("U - V", "Trackbars", 255, 255, callback)

    frame = cv2.imread(image_path)

    # Set default values
    cv2.setTrackbarPos("L - H", "Trackbars", 43)
    cv2.setTrackbarPos("L - S", "Trackbars", 35)
    cv2.setTrackbarPos("L - V", "Trackbars", 100)
    cv2.setTrackbarPos("U - H", "Trackbars", 100)
    cv2.setTrackbarPos("U - S", "Trackbars", 255)
    cv2.setTrackbarPos("U - V", "Trackbars", 255)

    while True:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        l_h = cv2.getTrackbarPos("L - H", "Trackbars")
        l_s = cv2.getTrackbarPos("L - S", "Trackbars")
        l_v = cv2.getTrackbarPos("L - V", "Trackbars")
        u_h = cv2.getTrackbarPos("U - H", "Trackbars")
        u_s = cv2.getTrackbarPos("U - S", "Trackbars")
        u_v = cv2.getTrackbarPos("U - V", "Trackbars")

        lower_range = np.array([l_h, l_s, l_v])
        upper_range = np.array([u_h, u_s, u_v])
        mask = cv2.inRange(hsv, lower_range, upper_range)

        result = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.imshow("original", frame)
        cv2.imshow("mask", mask)
        cv2.imshow("result", result)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


def ocr_tester(image_path):
    """ Brings up a HSV test window with sliders to check the 'inRange' function on the provided image.
        Change the default values below where indicated to the values associated with the appropriate
        template in image_template.py.
        :param image_path: The file path of the image to test.
    """
    scr = Screen()
    templ = Image_Templates(scr.scaleX, scr.scaleY)
    scr_reg = Screen_Regions(scr, templ)
    ocr = OCR(scr)

    cv2.namedWindow("Trackbars", cv2.WINDOW_NORMAL)  # cv2.WINDOW_AUTOSIZE)

    cv2.createTrackbar("L - H", "Trackbars", 0, 179, callback)
    cv2.createTrackbar("L - S", "Trackbars", 0, 255, callback)
    cv2.createTrackbar("L - V", "Trackbars", 0, 255, callback)
    cv2.createTrackbar("U - H", "Trackbars", 255, 179, callback)
    cv2.createTrackbar("U - S", "Trackbars", 255, 255, callback)
    cv2.createTrackbar("U - V", "Trackbars", 255, 255, callback)

    orig_image = cv2.imread(image_path)

    # Warp nav panel for perspective
    #img_warped = nav_panel_perspective_warp(orig_image)
    img_warped = orig_image

    # Set default values
    cv2.setTrackbarPos("L - H", "Trackbars", 100)
    cv2.setTrackbarPos("L - S", "Trackbars", 0)
    cv2.setTrackbarPos("L - V", "Trackbars", 100)
    cv2.setTrackbarPos("U - H", "Trackbars", 100)
    cv2.setTrackbarPos("U - S", "Trackbars", 255)
    cv2.setTrackbarPos("U - V", "Trackbars", 255)

    while True:
        hsv = cv2.cvtColor(img_warped, cv2.COLOR_BGR2HSV)

        l_h = cv2.getTrackbarPos("L - H", "Trackbars")
        l_s = cv2.getTrackbarPos("L - S", "Trackbars")
        l_v = cv2.getTrackbarPos("L - V", "Trackbars")
        u_h = cv2.getTrackbarPos("U - H", "Trackbars")
        u_s = cv2.getTrackbarPos("U - S", "Trackbars")
        u_v = cv2.getTrackbarPos("U - V", "Trackbars")

        lower_range = np.array([l_h, l_s, l_v])
        upper_range = np.array([u_h, u_s, u_v])
        mask = cv2.inRange(hsv, lower_range, upper_range)
        # Return original image with filter applied.
        filtered = cv2.bitwise_and(img_warped, img_warped, mask=mask)

        adjusted = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
        #gray = cv2.bitwise_not(gray)
        # cv2.imshow("gray", gray)

        # kernel = np.ones((1, 1), np.uint8)
        # img = cv2.dilate(gray, kernel, iterations=1)
        # img = cv2.erode(gray, kernel, iterations=1)
        #
        # # Apply Gaussian blur to reduce noise and smoothen edges
        # blurred = cv2.GaussianBlur(src=gray, ksize=(3, 5), sigmaX=0.5)
        # cv2.imshow("blurred", blurred)
        #
        # # Perform Canny edge detection
        # edges = cv2.Canny(blurred, 70, 135)
        # cv2.imshow("edges", edges)

        #adjusted = cv2.convertScaleAbs(gray, l_h/100, l_s)
        #adjusted = cv2.convertScaleAbs(gray, alpha=2, beta=0)

        # Convert to B&W to allow FindContours to find rectangles.
        # ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)  # | cv2.THRESH_BINARY_INV)

        result = adjusted.copy()
        result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        ocr_data, ocr_textlist = ocr.image_ocr(adjusted)

        draw_bounding_boxes(result, ocr_data, 0.25)

        cv2.imshow("original", img_warped)
        cv2.imshow("result", result)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


def get_highlighted_item_in_image(image_path):
    scr = Screen()
    ocr = OCR(scr)

    orig_image = cv2.imread(image_path)
    img_selected, x, y = ocr.get_highlighted_item_in_image(orig_image, 500, 25)
    if img_selected is not None:
        cv2.imwrite('test/hl.png', img_selected)


def rescale_screenshots(directory, scalex, scaley):
    """ Rescale all images in a folder. Also convert BMP to PNG
    :param directory: The directory to process.
    :param scalex: The X scaling of the original image.
    :param scaley: The scaling of the original image. """

    # Calc factor to scale image up/down
    newScaleX = 1.0 / scalex
    newScaleY = 1.0 / scaley

    directory_out = os.path.join(directory, 'out')
    if not os.path.exists(directory_out):
        os.makedirs(directory_out)

    for filename in os.listdir(directory):
        if filename.endswith(".png") or filename.endswith(".bmp"):
            image_path = os.path.join(directory, filename)
            image_out_path = os.path.join(directory_out, filename.replace('bmp', 'png'))

            image = cv2.imread(image_path)

            # Scale image to user scaling
            image = cv2.resize(image, (0, 0), fx=newScaleX, fy=newScaleY)
            cv2.imwrite(image_out_path, image)


def draw_bounding_boxes(image, detections, threshold=0.25):
    for res in detections:
        for line in res:
            points = np.array(line[0]).astype(np.int32)
            w = points[1][0] - points[0][0]
            if w > threshold:
                cv2.polylines(image, [points.reshape(-1, 1, 2)], True, (255, 0, 0), 2)
                #cv2.rectangle(image, tuple(map(int, points[0])), tuple(map(int, points[2])), (255, 0, 0), 2)
                #            cv2.putText(image, text, tuple(map(int, bbox[0])), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.65, (255, 0, 0), 2)
                text_position = (int(points[0][0]), int(points[0][1]) - 0)
                cv2.putText(image, f"{line[1][0]} ({line[1][1]:.2f})", text_position,
                            cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 255, 0), 1, cv2.LINE_AA)


def reg_scale_for_station(region, w: int, h: int) -> [int, int, int, int]:
    """ Scale a station services region based on the target resolution.
    This is performed because the tables on the station services screen do
    not increase proportionally with the screen size. The width changes with
    the screen size, the height does not change based on the screen size
    height, but on the screen width and the position stays consistent to the
    center of the screen.
    To calculate the new region height, we take the initial region defined at
    1920x1080 and scale up the height based on the target width and apply the
    new proportion against the center line.
    @param h: The screen height in pixels
    @param w: The screen width in pixels
    @param region: The region at 1920x1080
    """
    ref_w = 1920
    ref_h = 1080

    # Calc the x and y scaling.
    x_scale = w / ref_w
    y_scale = h / ref_h

    # Determine centre of the region
    reg_avg = (region['rect'][1] + region['rect'][3]) / 2

    # Recalc the region as a % above and below the center line.
    pct_abv = (reg_avg - region['rect'][1]) * x_scale / y_scale
    pct_blw = (region['rect'][3] - reg_avg) * x_scale / y_scale

    # Apply new % to the center line.
    new_rect1 = reg_avg - pct_abv
    new_rect3 = reg_avg + pct_blw

    # Return the update top and bottom Y percentages with the original X percentages.
    new_reg = {'rect': [region['rect'][0], new_rect1, region['rect'][2], new_rect3]}
    return new_reg


def size_scale_for_station(width: int, height: int, w: int, h: int) -> (int, int):
    """ Scale an item in the station services region based on the target resolution.
    This is performed because the tables on the station services screen do
    not increase proportionally with the screen size. The width changes with
    the screen size, the height does not change based on the screen size
    height, but on the screen width and the position stays consistent to the
    center of the screen.
    To calculate the new region height, we take the initial region defined at
    1920x1080 and scale up the height based on the target width and apply the
    new proportion against the center line.
    @param width: The width of the item in pixels
    @param height: The height of the item in pixels
    @param h: The screen height in pixels
    @param w: The screen width in pixels
    """
    ref_w = 1920
    ref_h = 1080

    # Calc the x and y scaling.
    x_scale = w / ref_w
    y_scale = h / ref_h

    # Increase the height by the ratio of the width
    new_width = width * x_scale
    new_height = height * x_scale

    # Return the new height in pixels.
    return new_width, new_height


def draw_regions(directory: str, regions):
    """ Takes each image in a folder, draws all the defined regions
    and then outputs the result to the 'out' folder.
    """
    directory_out = os.path.join(directory, 'out')
    if not os.path.exists(directory_out):
        os.makedirs(directory_out)

    for filename in os.listdir(directory_out):
        os.remove(os.path.join(directory_out, filename))

    for filename in os.listdir(directory):
        if filename.endswith(".png"):
            image_path = os.path.join(directory, filename)
            image_out_path = os.path.join(directory_out, filename)

            # Load image
            orig_image = cv2.imread(image_path)

            scr = Screen()
            scr.using_screen = False
            scr.set_screen_image(orig_image)
            img = orig_image

            # Existing size
            h, w, ch = orig_image.shape

            for r in regions:
                # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
                reg_rect = regions[r]['rect']

                # Crop to leave only the selected rectangle
                x0 = int(w * reg_rect[0])
                y0 = int(h * reg_rect[1])
                x1 = int(w * reg_rect[2])
                y1 = int(h * reg_rect[3])

                draw_match_rect(img, (x0, y0), (x1, y1), color=(255, 0, 0), thick=3)

            cv2.imwrite(image_out_path, img)


def draw_station_regions(directory: str, regions):
    """ Takes each image in a folder, draws all the defined regions
    and then outputs the result to the 'out' folder.
    The station specific regions are determined because the table data
    does not scale linearly with resolution, so additional region scaling is needed.
    """
    directory_out = os.path.join(directory, 'out')
    if not os.path.exists(directory_out):
        os.makedirs(directory_out)

    for filename in os.listdir(directory_out):
        os.remove(os.path.join(directory_out, filename))

    for filename in os.listdir(directory):
        if filename.endswith(".png"):
            image_path = os.path.join(directory, filename)
            image_out_path = os.path.join(directory_out, filename)

            # Load image
            orig_image = cv2.imread(image_path)

            scr = Screen()
            scr.using_screen = False
            scr.set_screen_image(orig_image)
            img = orig_image

            # Existing size
            h, w, ch = orig_image.shape

            for r in regions:
                # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
                reg = regions[r]

                # Scale the regions based on the target resolution.
                scl_reg = reg_scale_for_station(reg, w, h)

                # Crop to leave only the selected rectangle
                x0 = int(w * scl_reg['rect'][0])
                y0 = int(h * scl_reg['rect'][1])
                x1 = int(w * scl_reg['rect'][2])
                y1 = int(h * scl_reg['rect'][3])

                draw_match_rect(img, (x0, y0), (x1, y1), color=(255, 0, 0), thick=3)

            cv2.imwrite(image_out_path, img)


def callback(value):
    print(value)


if __name__ == "__main__":
    main()
