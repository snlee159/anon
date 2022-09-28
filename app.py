import argparse
import glob
import os
from vid_anon import audio_processing, frame_processing, utils

def main():
    # Read in all of the command-line arguments
    parser = argparse.ArgumentParser(description="Video anonymization tool")

    # TODO add GPU
    parser.add_argument("input_dir", type=str)
    parser.add_argument("--blur_face", help="Enable face blurring", action='store_true')
    parser.add_argument("--blur_shirt", help="Enable shirt blurring to hide logos", action='store_true')
    parser.add_argument("--redact_names", help="Remove proper nouns from audio", action='store_true')
    parser.add_argument("--cut_first_last_mile", 
                        help="Remove the first and last mile of driving to \
                            protect participant address", type=str)
    parser.add_argument("--output_dir", help="Where the anonymized files should be stored.\
                                            default to store where this is run.",
                        type=str, default='')
    parser.add_argument("--clean_up", help="Delete intermediate files.", action='store_true')

    args = parser.parse_args()

    # Find all the files to anonymize (even with different namings)
    files = glob.glob(f'{args.input_dir}/**/*.mp4', recursive=True)
    files += glob.glob(f'{args.input_dir}/**/*.MP4', recursive=True)

    print('Anonymizing the following files:')
    print(files) 
    
    # For each file, run the anonymization and keep track of the intermediate files
    for file in files: 
        # TODO add check to see if file has already been processed
        print(f'\nAnonymizing {file}...Please be patient, each step may take a few minutes...\n')
        file_tracking = []

        # Builds a format string for the output file depending on the suffix
        output_file = utils.get_output(file, args.input_dir, args.output_dir)

        # Remove the first and last mile to anonymize home location of drivers in videos
        # If no cut necessary/found in the timings file, returns original file
        if args.cut_first_last_mile:
            cut_file = frame_processing.cut_vid(file, output_file.format('cut.mp4'), 
                                                f'{args.input_dir}/{args.cut_first_last_mile}')
            if cut_file != file:
                file = cut_file
                file_tracking += [file]

        # Extracts the audio from the cut file
        audio_file = audio_processing.get_audio(file, output_file.format('audio.wav'))
        file_tracking += [audio_file]

        # Removes proper nouns from the separated audio file
        if args.redact_names:
            chunk_files = audio_processing.redact_names(audio_file, 
                                                        output_file.format('redacted.wav'), 
                                                        args.output_dir)

            # The redacted file is the first in the list, all others are temporary "chunks" for easier
            # processing
            if audio_file != chunk_files[0]:
                audio_file = chunk_files[0]
                file_tracking += chunk_files
            else:
                file_tracking += chunk_files[1:]

        # Blur the faces and logos on shirts
        if args.blur_face or args.blur_shirt:
            file = frame_processing.blur_vid(file, output_file.format('blurred.mp4'), 
                                             args.blur_shirt, args.blur_face)
            file_tracking += [file]
        
        # Re-combine the video and audio streams for the final video
        audio_processing.merge_audio(audio_file, file, output_file.format('anon.mp4'))
    
        # Clean up by deleting the extra files created in the anonymization process
        if len(file_tracking) > 0 and args.clean_up:
            for del_file in file_tracking:
                print(f'Deleting support file {del_file}')
                os.remove(del_file)

    print()