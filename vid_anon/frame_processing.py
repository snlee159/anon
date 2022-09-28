import mediapipe
import cv2
import pandas as pd
import numpy as np
import os
import subprocess
from .utils import find_and_blur_pts
from datetime import datetime as dt
from datetime import timedelta as td 

def load_mp():
    """
    Loads objects needed for mediapipe to run properly.

    Inputs:
    None

    Returns:
    The holistic model object.
    """
    holisticModule = mediapipe.solutions.holistic
    holistic = holisticModule.Holistic(min_detection_confidence=0.2,
                                        min_tracking_confidence=0.2,
                                        model_complexity=0)

    return holistic

def blur_vid(file, blurred_file, blur_shirt_bool, blur_face_bool):
    """
    Blurs the video based on the face and logo blur preferences. Takes in the booleans to know
    what to blur.

    Inputs:
    file            - String  - where the video to blur is saved
    blurred_file    - String  - where to save the blurred video
    blur_shirt_bool - Boolean - whether or not to blur the logos on shirts
    blur_face_bool  - Boolean - whether or not to blur faces

    Returns:
    The location where the blurred video is stored (no audio).
    """
    if not os.path.exists(blurred_file): 
        print_msg = 'Blurring {}' + f' in {file}...saving to {blurred_file}'

        # Changes the print message based on what will be blurred according
        # to user inputs
        if blur_face_bool:
            print_msg = print_msg.format('faces{}')
            if blur_shirt_bool:
                print_msg = print_msg.format(' and logos')
        else:
            print_msg = print_msg.format('logos')
        print(print_msg)

        # Get the holistic object if faces are being blurred
        if blur_face_bool:
            holistic = load_mp()

        # Read in the video file and set up the output file
        cap = cv2.VideoCapture(file)
        out = cv2.VideoWriter(blurred_file, cv2.VideoWriter_fourcc('m','p','4','v'), 
                            30, (int(cap.get(3)), int(cap.get(4))))

        # Iterators for tracking changes between frames and errors in empty
        # frames at file end
        good_frame = 0
        bad_frame = 0

        while True:
            try:
                # Read in the next frame and get its shape if it's the first frame
                _, frame = cap.read()
                if good_frame == 0:
                    (f_h, f_w) = frame.shape[:2]

                # Get the body pose estimation points
                results = holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                # If the shirt logos should be blurred, do this
                if blur_shirt_bool:
                    shirt_lms = results.pose_landmarks.landmark
                    shirt_points = [11,12,24,23]
                    frame = find_and_blur_pts(frame, shirt_lms, shirt_points, [f_w, f_h], 20)

                # If the faces should be blurred, do this
                if blur_face_bool:
                    face_lms = results.face_landmarks.landmark

                    face_pts = range(468)
                    frame = find_and_blur_pts(frame, face_lms, face_pts, [f_w, f_h], 10)

                # Save the file and print an update regularly to show progress
                out.write(frame)
                if good_frame % 1000 == 0:
                    print(f'Finished frame {good_frame}')
                good_frame += 1
            except Exception as e:
                # At end of file, break the loop
                bad_frame += 1
                if bad_frame > 1000:
                    break
                pass

        # Close the original file and the new file
        out.release()
        cap.release()

        return blurred_file
    else:
        print('Blurred file already exists...continuing...')
        return blurred_file

def cut_vid(file, cut_file, timings_file):
    """
    Shorten a video based on a file which gives when a driver starts and stops driving
    in a video and an estimate of what buffer will need to be cut in order to remove the 
    first and last mile of a driver's footage. The purpose is to be able to obfuscate where
    the driver lives.

    Inputs:
    file - String - where the original file is stored
    cut_file - String - where the shortened file will be stored
    timings_file - String - where to find the file with the start/stop times
        NOTE: this has a special format with the following columns in this order and only these:
        [filename, start, stop] where start and stop are formatted as strings as HH:MM:SS

    Returns:
    The location where the shortened video is stored.
    """
    if not os.path.exists(cut_file):
        # Read in the file timings
        file_timings_df = pd.read_csv(timings_file)

        # If the file being processed is in the file, get the start stop times
        if file.split('/')[1] in file_timings_df.file.values:
            print(f'Removing first and last mile of driving from {file}...saving to {cut_file}')
            (_, start, end) = file_timings_df[file_timings_df['file'] == file.split('/')[1]].values[0]

            # Add 2 minutes 24 seconds to the start and subtracted from the end to remove the first and 
            # last mile. Assumes average residential speed of 25 mph
            # NOTE if file is longer than a day long, this will not work....
            start = dt.strftime(dt.strptime(start, "%H:%M:%S") + td(minutes=2, seconds=24), "%H:%M:%S")
            end = dt.strftime(dt.strptime(end, "%H:%M:%S") - td(minutes=2, seconds=24), "%H:%M:%S")

            # Remove the start and stop times from the file
            # TODO add GPU
            os.system(f'ffmpeg -y -i {file} -ss {start} -to {end} -filter:v fps=30 {cut_file}')

            return cut_file
        else:
            return file
    else:
        print('First/last mile already removed...continuing...')
        return cut_file