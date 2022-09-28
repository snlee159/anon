import os
import wave
import json
import math
import pandas as pd
import numpy as np
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from nltk.tag import pos_tag
from vosk import Model, KaldiRecognizer 

def get_audio(file, audio_file):
    """
    Extracts audio from a video file.

    Inputs:
    file       - String - the name and path of the video file to extract audio from
    audio_file - String - the name and path of where the extracted audio should be saved

    Returns:
    The name and path of where the extracted audio was saved
    """
    print(f'Extracting audio from {file}...saving to {audio_file}')
    # TODO add GPU
    os.system(f'ffmpeg -loglevel quiet -y -i {file} -vn {audio_file}')

    return audio_file

def merge_audio(audio_file, file, merged_file):
    """
    Combines the audio and visual files to make a final video file.

    Inputs:
    audio_file  - String - the name and path of the audio file
    file        - String - the name and path of the visual file
    merged_file - String - the name and path where the combined video will be saved

    Returns:
    The name and path where the combined video was saved
    """
    print(f'Combining audio and video streams and saving to {merged_file}')
    # TODO add GPU
    os.system(f'ffmpeg -y -i {file} -i {audio_file} -map 0:v:0 -map 1:a:0 {merged_file}')

    return merged_file

def redact_names(audio_file, redacted_file, out_path):
    """
    Redacts proper nouns from an audio file by first converting an audio file to text
    then finding the proper nouns in that text. Requires matching across two speech
    to text tools so does not recognize uncommon names well. Very good with common names.

    Inputs:
    audio_file    - String - the path where the audio file is saved
    redacted_file - String - where the redacted audio file should be saved
    out_path      - String - the path where all temporary files are saved for chunk files

    Returns:
    A list where the first entry is the redacted audio file location followed by the
    chunk files to delete later.
    """
    if not os.path.exists(redacted_file):
        print(f'Redacting proper nouns from {audio_file}...saving to {redacted_file}')

        # Pull in the audio objects and chunk the audio for manageable processing
        r = sr.Recognizer()
        files = []
        sound = AudioSegment.from_wav(f'{audio_file}')
        chunks = split_on_silence(sound,
                                min_silence_len = 5000,
                                silence_thresh = sound.dBFS-14,
                                keep_silence=500,
                                )
 
        # Loop through and process each audio chunk into text and find proper nouns
        redacted_words = []
        for i, audio_chunk in enumerate(chunks, start=1):
            # Save the chunk file
            chunk_filename = os.path.join(out_path, f'chunk{i}.wav')
            files += [chunk_filename]
            audio_chunk.export(chunk_filename, format="wav")

            try:
                with sr.AudioFile(chunk_filename) as source:
                    # Convert audio to text with google
                    audio_data = r.record(source)
                    text = r.recognize_google(audio_data, language='en', show_all=True)

                # Split the text into words and label by parts of speech (pos)
                tagged_sent = pos_tag(text['alternative'][0]['transcript'].split())

                # If the word is a proper noun, state that it will be redacted and save the
                # redacted word to a list
                new_text = [word if pos != "NNP" else "[redacted]" for word, pos in tagged_sent]
                redacted_words.append([word.lower() for word, pos in tagged_sent if pos == 'NNP'])
            except Exception as e:
                pass

        # Read in the second speech to text tool which gives us the word timings
        model = Model('/home/farlab/vid_anon/vid_anon/vosk-model-en-us-0.22')
        wf = wave.open(f'{audio_file}', "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)

        # Found from a stackoverflow...I think this one: https://stackoverflow.com/questions/68175694/how-to-use-wave-file-as-input-in-vosk-speech-recognition
        results = []
        # Recognize speech using vosk model
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                results.append(part_result)
        part_result = json.loads(rec.FinalResult())
        results.append(part_result)

        # Convert list of JSON dictionaries to dataframe where each word is a row and gives the start/stop times
        word_df = pd.DataFrame(columns=['word','start','end','conf'])
        i = 0
        for sentence in results:
            if len(sentence) == 1:
                # Account for empty words from pauses
                continue
            for obj in sentence['result']:
                word_df.loc[i] = [obj['word'], obj['start'], obj['end'], obj['conf']]
                i += 1

        # Only redact if there are redacted words
        if len(redacted_words) > 0:
            # Mark a word as redacted in the dataframe with the timings if it was determined to be a proper
            # noun by nltk. (Weirdly the text from the vosk model doesn't determine proper nouns well.)
            word_df['redacted'] = np.where(word_df['word'].isin(redacted_words[0]), 1, 0)
            redacted_df = word_df[word_df['redacted'] == 1].reset_index(drop=True)
            
            # Form the ffmpeg command to redact each redacted word from the actual file using the start/stop times
            # TODO add GPU
            ffmpeg_cmd = f'''ffmpeg -y -i {audio_file} -af "'''
            for i, row in redacted_df.iterrows():
                if i > 0:
                    ffmpeg_cmd += """, """
                ffmpeg_cmd += f"""volume=enable='between(t,{row['start']}, {row['end']})':volume=0"""

            ffmpeg_cmd += f"""" {redacted_file}"""
            os.system(ffmpeg_cmd)

        else:
            # If no redaction, return the original audio file
            word_df['redacted'] = 0
            redacted_file = audio_file

        # Close the audio file
        wf.close() 

        return [redacted_file] + files
    else:
        print(f'Redacted file already exists...continuing...')
        return [redacted_file]