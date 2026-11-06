"""Separate process permits a stable speech Python alongside the Studio runtime."""
import json
import sys


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel(sys.argv[2], device='cpu', compute_type='int8')
    segments, info = model.transcribe(sys.argv[1], language='vi', word_timestamps=True,
                                      vad_filter=True, condition_on_previous_text=False)
    words = []
    for segment in segments:
        for word in segment.words or []:
            text = word.word.strip()
            if text and word.end > word.start:
                # Token-level alignments occasionally overlap by a few ms.
                start = max(word.start, words[-1]['end'] if words else 0)
                if word.end > start:
                    words.append({'text': text, 'start': start, 'end': word.end})
    print(json.dumps({'words': words, 'duration': info.duration}, ensure_ascii=True))


if __name__ == '__main__':
    main()
