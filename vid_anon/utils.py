from cmath import rect
import numpy as np
import cv2
from scipy.spatial import ConvexHull

def get_output(file, split_dir, output_dir):
    """
    Forms a string format for the intermediary file names. Note, the original
    and output directories will contain any subdirectories the files are in 
    automatically.

    Inputs:
    file       - String - the location of the original input file
    split_dir  - String - the directory the original files are saved in
    output_dir - String - the directory where the files will be saved

    Returns:
    A string format to accept a suffix for the intermediary file names.
    """
    filename = file.split(split_dir)[1][1:-4]
    return '{0}{1}_'.format(output_dir, filename) + '{0}'

def sort_xy(x, y):
    """
    Sorts a series of coordinates in clockwise rotation. Necessary to build the mask 
    for blurring properly. Found here: https://stackoverflow.com/questions/58377015/counterclockwise-sorting-of-x-y-data

    Inputs:
    x - list - the x coordinates for the data
    y - list - the y coordinates for the data

    Returns:
    The clockwise ordered coordinates for around the shape observed.
    """
    x0 = np.mean(x)
    y0 = np.mean(y)

    r = np.sqrt((x-x0)**2 + (y-y0)**2)
    angles = np.where((y-y0) > 0, np.arccos((x-x0)/r), 2*np.pi-np.arccos((x-x0)/r))
    mask = np.argsort(angles)

    x_sorted = x[mask]
    y_sorted = y[mask]

    return np.stack((x_sorted, y_sorted), axis=1)


def anonymize_face_pixelate(image, blocks=3):
    """
    Taken from overstack (TODO: get link to reference). Easy pixelation of a
    block of a frame.

    Inputs:
    image  - numpy array - the portion of the frame that should be anonymized
    blocks - Integer     - the number of blocks in a row of the pixelation

    Returns:
    The blurred version of the input image
    """
    # divide the input image into NxN blocks
    (h, w) = image.shape[:2]
    xSteps = np.linspace(0, w, blocks + 1, dtype="int")
    ySteps = np.linspace(0, h, blocks + 1, dtype="int")
    # loop over the blocks in both the x and y direction
    for i in range(1, len(ySteps)):
        for j in range(1, len(xSteps)):
            # compute the starting and ending (x, y)-coordinates
            # for the current block
            startX = xSteps[j - 1]
            startY = ySteps[i - 1]
            endX = xSteps[j]
            endY = ySteps[i]
            # extract the ROI using NumPy array slicing, compute the
            # mean of the ROI, and then draw a rectangle with the
            # mean RGB values over the ROI in the original image
            roi = image[startY:endY, startX:endX]
            (B, G, R) = [int(x) for x in cv2.mean(roi)[:3]]
            cv2.rectangle(image, 
                          (startX, startY), 
                          (endX, endY),
                          (B, G, R), -1)
    # return the pixelated blurred image
    return image

def build_points(pts_list, lms, frame_shape):
    """
    Gets x, y coordinates from landmarks in mediapipe so the shapes can be blurred.

    Inputs:
    pts_list    - list             - the indexes to extract from the list of landmarks
    lms         - mediapipe Object - the actual landmarks, basically a list of dictionaries
    frame_shape - list             - frame width, frame height

    Returns:
    The formatted landmark coordinate list
    """
    pts = []
    for pt in pts_list:
        pts.append([lms[pt].x * frame_shape[0], lms[pt].y * frame_shape[1]])
    pts = np.array(pts).astype(int)

    return pts

def replace_pixels(blur_rect, blurred_frame, frame):
    """
    Takes the blurred frame and places it on top of the original frame, ignoring where
    alpha is set to 0.0 on the blurred frame (outside the blur shape).

    Inputs:
    blur_rect     - list        - the shape and offset of the blurred area (x,y,w,h)
    blurred_frame - numpy array - the blurred area as a frame
    frame         - numpy array - the original frame that will be overlayed with the blurred_frame

    Returns:
    The original frame with the blur superimposed on top.
    """
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
    alpha_cropped = blurred_frame[:,:,3]
    alpha_img = 1 - alpha_cropped
    x,y,w,h = blur_rect

    for c in range(0, 3):
        frame[y:y+h, x:x+w, c] = (alpha_img * frame[y:y+h, x:x+w, c]) + \
                                 (alpha_cropped * blurred_frame[:, :, c])

    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
    
    return frame

def find_and_blur_pts(frame, lms, pts, frame_shape, num_blocks): 
    """
    Takes in the frame, the outline points of the space to be blurred, separates that
    space, blurs it, and superimposes the blur on the original image.

    Inputs:
    frame       - numpy array - the original image that will be overlayed
    lms         - list        - the landmarks extracted from the image with mediapipe
    pts         - list        - the list of points outlining the shape to blur
    frame_shape - list        - the shape of the frame itself (f_w, h_h)
    num_blocks  - Integer     - the amount of blurring (more blocks for bigger sizes)

    Returns:
    The original frame with the blur superimposed on top
    """
    # Make an array with the outline of the face to know where to blur
    pts = build_points(pts, lms, frame_shape)

    # Extract the rectangle surrounding these points (around the face)
    rect = cv2.boundingRect(pts)
    x,y,w,h = rect
    cropped = frame[y:y + h, x:x + w].copy()

    # Anonymize the entire rectangle
    cropped = anonymize_face_pixelate(cropped, blocks=num_blocks)

    # In the cropped, anonymized rectangle, pull out just the shape of the torso or face (surrounding area
    # is given an alpha of 0 to make it transparent)
    pts = pts - pts.min(axis=0)
    mask = np.zeros(cropped.shape[:2], np.uint8)
    cropped = np.concatenate((cropped, np.ones((cropped.shape[0], cropped.shape[1], 1))), axis=2)
    
    # Pull out just the outside shape to ensure the entire torso and face is blurred
    hull = ConvexHull(points=pts)
    outside_shape = pts[hull.simplices].shape
    outside_points = np.unique(pts[hull.simplices].reshape(outside_shape[0]*outside_shape[1], 2), axis=0)
    ordered_points = sort_xy(outside_points[:,0], outside_points[:,1])
    
    # Make the mask
    cv2.drawContours(mask, [ordered_points], -1, (255,255,255, 0.0), -1, cv2.LINE_AA)
    cropped = cv2.bitwise_and(cropped, cropped, mask=mask)

    # Wherever the alpha isn't transparent, replace the original image pixel to blur just the 
    # torso area
    frame = replace_pixels(rect, cropped, frame)

    return frame