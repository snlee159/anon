# anon
Anonymizing videos with face blurring, logo blurring, and speech redaction.

Author: @snlee159

## Acknowledgements
This project was made in collaboration with @FARLab to meet some of their needs for automatic face blurring for showing participant study research publicly.

## Purpose and Context 
Oftentimes videos need to be shared publicly for demonstrating a technology or project. However, it is critical to protect a participant's identity.

Anon anonymizes videos for this purpose for blurring faces, redacting proper nouns from audio, and blurring logos on shirts.

## How to Install
Only available for developer installation right now. Install via git for now with:

```
git clone https://github.com/snlee159/anon.git
cd anon
sudo python setup.py
```

to install all requirements.

You'll also need to install the vosk model for speech redaction. You can do that with the following:

```
cd anon
cd vid_anon
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
sudo apt-get install unzip
unzip vosk-model-en-us-0.22.zip
rm vosk-model-en-us-0.22.zip
```

You should now be ready to run the program.

## How to Use
### Command Line Interface
Anon must be run via a command line argument  (within the `anon` directory) with the following additional arguments:

```
python vid_anon <video_directory> [optional arguments]
```

Where `video_directory` is the path to the directory where every video you want to anonymize is located. Any file ending in `.MP4` or `.mp4` in that directory will be anonymized. **Do not include the trailing backslash at the end of the video directory path.**

Optional arguments include:
* `--blur_face`: to automatically blur faces in the video; will blur all faces in the videos
* `--blur_shirt`: to automatically blur logos on shirts. All shirts will be blurred
* `--redact_names`: to remove proper nouns from the audio
* `--cut_first_last_mile <drive_times>.csv`: to remove the first and last mile from drive start/stop time in a video which includes driving. A lot of FARLab's videos including in-vehicle recordings and this was included to protect participant home location information. Requires the `drive_times` csv path to the file to be referenced. Which includes the following columns: `filename`, `start_frame`, `end_frame` where filename is the exact filenames (with `.mp4`) in the `video_directory` and `start_frame` and `end_frame` are the frames, not the times, when the driver starts/stops driving. Assumes a video of 30 fps
* `--clean_up` remove support files (audio chunks, etc)
* `--output_dir <output_directory>`: default will save the anonymized files to where this is run. If this is set, `output_directory` will be the path where the anonymized files (and support files, if not deleted) will be stored (**include the trailing backslash in the output directory path**).

### Exceptions and Things That May Break
Right now, this only works properly for `.mp4` or `.MP4` file extensions.

In addition, videos over 10 minutes may experience issues.

## Future Improvements
* Make intermediary video files to avoid memory overload that breaks process for long videos
* Save face and body points to CSV for reference post-anonymization
* Remove trailing backslash for path specification for easier command line arguments