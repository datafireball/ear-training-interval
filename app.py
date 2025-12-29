"""
Flask web application for Ear Training Exercise Generator
"""
import os
import re
import random
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Audio processing
try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# TTS - try multiple options
TTS_ENGINE = None
try:
    import pyttsx3
    TTS_ENGINE = 'pyttsx3'
except ImportError:
    try:
        import edge_tts
        import asyncio
        TTS_ENGINE = 'edge-tts'
    except ImportError:
        TTS_ENGINE = None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = Path('./uploads')
app.config['OUTPUT_FOLDER'] = Path('./output')

# Create necessary directories
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['OUTPUT_FOLDER'].mkdir(exist_ok=True)

# Note name to semitone mapping (C=0, C#=1, D=2, ..., B=11)
NOTE_TO_SEMITONE = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
}

SEMITONE_TO_NOTE_SHARP = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
]

SEMITONE_TO_NOTE_FLAT = [
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
]


def parse_note(note_str: str) -> Tuple[str, int]:
    """Parse a note string into (note_name, octave)."""
    note_str = note_str.strip()
    note_str = note_str.replace('sharp', '#')
    note_str = note_str.replace('flat', 'b')
    note_str = note_str.replace('Sharp', '#')
    note_str = note_str.replace('Flat', 'b')
    
    match = re.match(r'^([A-G])([#b]?)(\d+)$', note_str)
    if not match:
        raise ValueError(f"Cannot parse note: {note_str}")
    
    base_note = match.group(1)
    accidental = match.group(2) or ''
    octave = int(match.group(3))
    
    note_name = base_note + accidental
    
    if note_name in ['Db', 'Eb', 'Gb', 'Ab', 'Bb']:
        flat_to_sharp = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
        note_name = flat_to_sharp[note_name]
    
    return note_name, octave


def note_to_semitone(note_name: str, octave: int) -> int:
    """Convert note name and octave to absolute semitone number (C0 = 0)."""
    if note_name not in NOTE_TO_SEMITONE:
        raise ValueError(f"Unknown note: {note_name}")
    return NOTE_TO_SEMITONE[note_name] + (octave * 12)


def semitone_to_note(semitone: int, prefer_sharp: bool = True) -> Tuple[str, int]:
    """Convert absolute semitone number to (note_name, octave)."""
    octave = semitone // 12
    note_idx = semitone % 12
    
    if prefer_sharp:
        note_name = SEMITONE_TO_NOTE_SHARP[note_idx]
    else:
        note_name = SEMITONE_TO_NOTE_FLAT[note_idx]
    
    return note_name, octave


def transpose_note(note_str: str, semitones: int) -> str:
    """Transpose a note by a given number of semitones."""
    note_name, octave = parse_note(note_str)
    current_semitone = note_to_semitone(note_name, octave)
    new_semitone = current_semitone + semitones
    
    if new_semitone < 0:
        raise ValueError(f"Transposition would result in negative semitone: {new_semitone}")
    
    new_note_name, new_octave = semitone_to_note(new_semitone, prefer_sharp=True)
    return f"{new_note_name}{new_octave}"


def scan_dataset(data_dir: Path) -> Dict[str, List[Path]]:
    """Scan the dataset directory recursively for audio files."""
    note_to_files = defaultdict(list)
    audio_extensions = {'.wav', '.mp3', '.ogg', '.flac', '.m4a'}
    
    for audio_file in data_dir.rglob('*'):
        if audio_file.suffix.lower() in audio_extensions:
            parent_dir = audio_file.parent.name
            filename_stem = audio_file.stem
            candidates = [parent_dir, filename_stem]
            
            for candidate in candidates:
                try:
                    note_match = re.match(r'^([A-G](?:sharp|flat|[#b])?\d+)', candidate, re.IGNORECASE)
                    if note_match:
                        note_str = note_match.group(1)
                        note_name, octave = parse_note(note_str)
                        normalized_note = f"{note_name}{octave}"
                        note_to_files[normalized_note].append(audio_file)
                        break
                    
                    try:
                        note_name, octave = parse_note(candidate)
                        normalized_note = f"{note_name}{octave}"
                        note_to_files[normalized_note].append(audio_file)
                        break
                    except ValueError:
                        continue
                except Exception:
                    continue
    
    return dict(note_to_files)


def select_best_file(file_list: List[Path]) -> Path:
    """Select the 'best' file from a list."""
    if not file_list:
        raise ValueError("Empty file list")
    return sorted(file_list, key=lambda p: (len(p.name), p.name))[0]


def generate_tts_audio(text: str, output_path: Optional[Path] = None):
    """Generate TTS audio from text."""
    if not PYDUB_AVAILABLE:
        return None
    
    if TTS_ENGINE == 'pyttsx3':
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)
            
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                output_path = Path(temp_file.name)
                temp_file.close()
            else:
                output_path = Path(output_path)
            
            engine.save_to_file(text, str(output_path))
            engine.runAndWait()
            
            audio = AudioSegment.from_wav(str(output_path))
            
            if output_path.exists() and 'tmp' in str(output_path):
                try:
                    output_path.unlink()
                except:
                    pass
            
            return audio
        except Exception as e:
            print(f"Error with pyttsx3: {e}")
            return None
    
    elif TTS_ENGINE == 'edge-tts':
        try:
            async def _generate():
                if output_path is None:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                    output_path_async = Path(temp_file.name)
                    temp_file.close()
                else:
                    output_path_async = Path(output_path)
                
                voices = await edge_tts.list_voices()
                voice = None
                for v in voices:
                    if 'en' in v['Locale'].lower() and 'female' in v['Gender'].lower():
                        voice = v['ShortName']
                        break
                if not voice:
                    voice = 'en-US-AriaNeural'
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path_async))
                return output_path_async
            
            output_path_result = asyncio.run(_generate())
            audio = AudioSegment.from_mp3(str(output_path_result))
            
            if 'tmp' in str(output_path_result):
                try:
                    output_path_result.unlink()
                except:
                    pass
            
            return audio
        except Exception as e:
            print(f"Error with edge-tts: {e}")
            return None
    
    else:
        if PYDUB_AVAILABLE:
            duration_ms = len(text.split()) * 200
            return AudioSegment.silent(duration=duration_ms)
        return None


def load_and_prepare_audio(file_path: Path, target_sample_rate: int = 44100):
    """Load audio file and prepare it."""
    if not PYDUB_AVAILABLE:
        raise RuntimeError("pydub not available")
    
    audio = AudioSegment.from_file(str(file_path))
    
    if audio.frame_rate != target_sample_rate:
        audio = audio.set_frame_rate(target_sample_rate)
    
    if audio.channels > 1:
        audio = audio.set_channels(1)
    
    fade_duration = 10
    if len(audio) > fade_duration * 2:
        audio = audio.fade_in(fade_duration).fade_out(fade_duration)
    
    return audio


def create_note_pair_audio(
    root_file: Path,
    second_file: Path,
    gap_ms: int = 150,
    target_sample_rate: int = 44100
):
    """Create audio for a note pair: root + gap + second note."""
    root_audio = load_and_prepare_audio(root_file, target_sample_rate)
    second_audio = load_and_prepare_audio(second_file, target_sample_rate)
    
    root_audio = normalize(root_audio)
    second_audio = normalize(second_audio)
    
    gap = AudioSegment.silent(duration=gap_ms)
    pair_audio = root_audio + gap + second_audio
    
    return pair_audio


def generate_exercise_audio(
    root_note: str,
    semitone_range: Tuple[int, int],
    num_rounds: int,
    num_repetitions: int,
    note_to_files_map: Dict[str, List[Path]],
    note_gap_ms: int = 150,
    between_repetitions_wait_s: float = 2.0,
    between_rounds_wait_s: float = 1.0,
    sample_rate: int = 44100,
    random_seed: Optional[int] = None
):
    """Generate the complete exercise audio."""
    if not PYDUB_AVAILABLE:
        raise RuntimeError("pydub not available")
    
    if random_seed is not None:
        random.seed(random_seed)
    
    root_note_name, root_octave = parse_note(root_note)
    root_note_normalized = f"{root_note_name}{root_octave}"
    
    if root_note_normalized not in note_to_files_map:
        raise ValueError(f"Root note {root_note_normalized} not found in dataset")
    
    root_file = select_best_file(note_to_files_map[root_note_normalized])
    
    min_offset, max_offset = semitone_range
    intro_text = (
        f"Here is an ear training test. "
        f"There will be {num_rounds} rounds. "
        f"Each round repeats a pair of notes {num_repetitions} times. "
        f"The root note is {root_note}. "
        f"The second note is within {min_offset} to {max_offset} semitones from the root."
    )
    
    script_texts = [intro_text]
    
    intro_audio = generate_tts_audio(intro_text)
    if not intro_audio:
        intro_audio = AudioSegment.silent(duration=2000)
    
    complete_audio = intro_audio
    complete_audio += AudioSegment.silent(duration=500)
    
    answer_sheet_data = []
    
    for round_num in range(1, num_rounds + 1):
        max_retries = 50
        offset = None
        second_note_str = None
        second_file = None
        
        for attempt in range(max_retries):
            offset = random.randint(min_offset, max_offset)
            try:
                second_note_str = transpose_note(root_note, offset)
                if second_note_str in note_to_files_map:
                    second_file = select_best_file(note_to_files_map[second_note_str])
                    break
            except Exception:
                continue
        
        if second_file is None:
            raise ValueError(
                f"Could not find a valid second note for round {round_num} "
                f"after {max_retries} attempts."
            )
        
        answer_sheet_data.append({
            'round': round_num,
            'offset': offset,
            'second_note': second_note_str
        })
        
        pair_audio = create_note_pair_audio(root_file, second_file, note_gap_ms, sample_rate)
        
        for rep_num in range(1, num_repetitions + 1):
            if rep_num == 1:
                prompt_text = f"Here is question number {round_num}, the first time."
            elif rep_num == num_repetitions:
                prompt_text = "The last time."
            else:
                ordinals = {2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth'}
                ordinal = ordinals.get(rep_num, f"{rep_num}th")
                prompt_text = f"The {ordinal} time."
            
            script_texts.append(prompt_text)
            
            prompt_audio = generate_tts_audio(prompt_text)
            if not prompt_audio:
                prompt_audio = AudioSegment.silent(duration=500)
            
            complete_audio += prompt_audio
            complete_audio += AudioSegment.silent(duration=200)
            complete_audio += pair_audio
            
            if rep_num < num_repetitions:
                complete_audio += AudioSegment.silent(duration=int(between_repetitions_wait_s * 1000))
        
        if round_num < num_rounds:
            complete_audio += AudioSegment.silent(duration=int(between_rounds_wait_s * 1000))
    
    return complete_audio, answer_sheet_data, script_texts


@app.route('/')
def index():
    """Main page with form."""
    return render_template('index.html', 
                         pydub_available=PYDUB_AVAILABLE,
                         tts_engine=TTS_ENGINE)


@app.route('/api/status')
def status():
    """API endpoint to check system status."""
    data_dir = Path('./data')
    note_to_files_map = scan_dataset(data_dir) if data_dir.exists() else {}
    
    return jsonify({
        'pydub_available': PYDUB_AVAILABLE,
        'tts_engine': TTS_ENGINE,
        'notes_found': len(note_to_files_map),
        'sample_notes': sorted(list(note_to_files_map.keys()))[:10] if note_to_files_map else []
    })


@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate exercise audio."""
    try:
        data = request.get_json()
        
        # Parse parameters
        root_note = data.get('root_note', 'C4')
        semitone_min = int(data.get('semitone_min', -12))
        semitone_max = int(data.get('semitone_max', 12))
        num_rounds = int(data.get('num_rounds', 10))
        num_repetitions = int(data.get('num_repetitions', 3))
        note_gap_ms = int(data.get('note_gap_ms', 150))
        between_repetitions_wait_s = float(data.get('between_repetitions_wait_s', 2.0))
        between_rounds_wait_s = float(data.get('between_rounds_wait_s', 1.0))
        sample_rate = int(data.get('sample_rate', 44100))
        random_seed = data.get('random_seed')
        if random_seed:
            random_seed = int(random_seed)
        
        # Validate
        if not PYDUB_AVAILABLE:
            return jsonify({'error': 'pydub is not available. Please install it.'}), 400
        
        if semitone_min >= semitone_max:
            return jsonify({'error': 'Semitone min must be less than max'}), 400
        
        if num_rounds < 1 or num_rounds > 100:
            return jsonify({'error': 'Number of rounds must be between 1 and 100'}), 400
        
        # Scan dataset
        data_dir = Path('./data')
        if not data_dir.exists():
            return jsonify({'error': 'Data directory not found'}), 400
        
        note_to_files_map = scan_dataset(data_dir)
        if not note_to_files_map:
            return jsonify({'error': 'No audio files found in dataset'}), 400
        
        # Generate exercise
        exercise_audio, answer_data, script_texts = generate_exercise_audio(
            root_note=root_note,
            semitone_range=(semitone_min, semitone_max),
            num_rounds=num_rounds,
            num_repetitions=num_repetitions,
            note_to_files_map=note_to_files_map,
            note_gap_ms=note_gap_ms,
            between_repetitions_wait_s=between_repetitions_wait_s,
            between_rounds_wait_s=between_rounds_wait_s,
            sample_rate=sample_rate,
            random_seed=random_seed
        )
        
        # Create unique output directory for this generation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = app.config['OUTPUT_FOLDER'] / timestamp
        output_dir.mkdir(exist_ok=True)
        
        # Export audio
        mp3_path = output_dir / "exercise.mp3"
        wav_path = output_dir / "exercise.wav"
        
        try:
            exercise_audio.export(str(mp3_path), format="mp3", bitrate="192k")
            audio_file = mp3_path
            audio_format = 'mp3'
        except Exception:
            exercise_audio.export(str(wav_path), format="wav")
            audio_file = wav_path
            audio_format = 'wav'
        
        # Generate answer sheet
        answer_sheet_path = output_dir / "answer_sheet.txt"
        with open(answer_sheet_path, 'w') as f:
            f.write("EAR TRAINING EXERCISE - ANSWER SHEET\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Random seed: {random_seed}\n")
            f.write(f"\nConfiguration:\n")
            f.write(f"  Root note: {root_note}\n")
            f.write(f"  Semitone range: [{semitone_min}, {semitone_max}]\n")
            f.write(f"  Number of rounds: {num_rounds}\n")
            f.write(f"  Repetitions per round: {num_repetitions}\n")
            f.write(f"  Sample rate: {sample_rate}\n")
            f.write(f"  Note gap: {note_gap_ms}ms\n")
            f.write(f"  Between repetitions wait: {between_repetitions_wait_s}s\n")
            f.write(f"  Between rounds wait: {between_rounds_wait_s}s\n")
            f.write(f"\nAnswers:\n")
            f.write(f"Round\tOffset (semitones)\tSecond Note\n")
            f.write("-" * 60 + "\n")
            
            for entry in answer_data:
                f.write(f"{entry['round']}\t{entry['offset']}\t{entry['second_note']}\n")
        
        # Generate script file
        script_path = output_dir / "script.txt"
        with open(script_path, 'w') as f:
            f.write("EAR TRAINING EXERCISE - SPOKEN PROMPTS SCRIPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nThis file contains all the spoken prompts in the exercise.\n")
            f.write("\n" + "-" * 60 + "\n\n")
            
            for i, text in enumerate(script_texts, 1):
                f.write(f"{i}. {text}\n\n")
        
        # Save answer data as JSON for test-taking
        answer_json_path = output_dir / "answers.json"
        with open(answer_json_path, 'w') as f:
            json.dump({
                'root_note': root_note,
                'semitone_range': [semitone_min, semitone_max],
                'num_rounds': num_rounds,
                'answers': answer_data
            }, f, indent=2)
        
        return jsonify({
            'success': True,
            'output_dir': timestamp,
            'test_id': timestamp,  # Use timestamp as test ID
            'audio_file': f"{timestamp}/exercise.{audio_format}",
            'answer_sheet': f"{timestamp}/answer_sheet.txt",
            'script': f"{timestamp}/script.txt",
            'answers_json': f"{timestamp}/answers.json",
            'duration_seconds': len(exercise_audio) / 1000,
            'audio_format': audio_format
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test/<test_id>')
def take_test(test_id):
    """Test-taking interface."""
    # Security check
    test_id = secure_filename(test_id)
    test_dir = app.config['OUTPUT_FOLDER'] / test_id
    
    if not test_dir.exists():
        return render_template('error.html', message='Test not found'), 404
    
    # Check if answers.json exists
    answers_json_path = test_dir / "answers.json"
    if not answers_json_path.exists():
        return render_template('error.html', message='Test data not found'), 404
    
    # Load test data
    with open(answers_json_path, 'r') as f:
        test_data = json.load(f)
    
    # Find audio file
    audio_file = None
    audio_format = None
    for ext in ['mp3', 'wav']:
        audio_path = test_dir / f"exercise.{ext}"
        if audio_path.exists():
            audio_file = f"{test_id}/exercise.{ext}"
            audio_format = ext
            break
    
    if not audio_file:
        return render_template('error.html', message='Audio file not found'), 404
    
    return render_template('test.html', 
                         test_id=test_id,
                         test_data=test_data,
                         audio_file=audio_file,
                         audio_format=audio_format)


@app.route('/api/test/<test_id>/answers', methods=['GET'])
def get_test_answers(test_id):
    """Get correct answers for a test."""
    test_id = secure_filename(test_id)
    test_dir = app.config['OUTPUT_FOLDER'] / test_id
    answers_json_path = test_dir / "answers.json"
    
    if not answers_json_path.exists():
        return jsonify({'error': 'Test not found'}), 404
    
    with open(answers_json_path, 'r') as f:
        test_data = json.load(f)
    
    return jsonify({
        'root_note': test_data['root_note'],
        'answers': test_data['answers']
    })


@app.route('/api/test/<test_id>/submit', methods=['POST'])
def submit_test(test_id):
    """Submit test answers and get results."""
    test_id = secure_filename(test_id)
    test_dir = app.config['OUTPUT_FOLDER'] / test_id
    answers_json_path = test_dir / "answers.json"
    
    if not answers_json_path.exists():
        return jsonify({'error': 'Test not found'}), 404
    
    # Load correct answers
    with open(answers_json_path, 'r') as f:
        test_data = json.load(f)
    
    # Get user answers
    user_answers = request.get_json().get('answers', [])
    correct_answers = test_data['answers']
    
    # Compare answers
    results = []
    correct_count = 0
    
    for i, correct in enumerate(correct_answers):
        user_answer = user_answers[i] if i < len(user_answers) else None
        round_num = correct['round']
        
        # User can submit either offset or note name
        is_correct = False
        user_offset = None
        user_note = None
        
        if user_answer is not None:
            if isinstance(user_answer, dict):
                user_offset = user_answer.get('offset')
                user_note = user_answer.get('note')
            elif isinstance(user_answer, (int, str)):
                # Try to parse as offset or note
                try:
                    user_offset = int(user_answer)
                except (ValueError, TypeError):
                    user_note = str(user_answer)
        
        # Check correctness
        if user_offset is not None:
            is_correct = (user_offset == correct['offset'])
        elif user_note is not None:
            try:
                # Normalize note names for comparison
                user_note_parsed, _ = parse_note(user_note)
                correct_note_parsed, _ = parse_note(correct['second_note'])
                is_correct = (user_note_parsed == correct_note_parsed)
            except:
                is_correct = False
        
        if is_correct:
            correct_count += 1
        
        results.append({
            'round': round_num,
            'user_answer': {
                'offset': user_offset,
                'note': user_note
            },
            'correct_answer': {
                'offset': correct['offset'],
                'note': correct['second_note']
            },
            'is_correct': is_correct
        })
    
    total_rounds = len(correct_answers)
    score_percentage = (correct_count / total_rounds * 100) if total_rounds > 0 else 0
    
    return jsonify({
        'success': True,
        'results': results,
        'score': {
            'correct': correct_count,
            'total': total_rounds,
            'percentage': round(score_percentage, 2)
        }
    })


@app.route('/download/<path:filepath>')
def download(filepath):
    """Download or serve generated files."""
    file_path = app.config['OUTPUT_FOLDER'] / filepath
    
    if not file_path.exists() or not file_path.is_file():
        return jsonify({'error': 'File not found'}), 404
    
    # Security check - ensure file is within output folder
    try:
        file_path.resolve().relative_to(app.config['OUTPUT_FOLDER'].resolve())
    except ValueError:
        return jsonify({'error': 'Invalid file path'}), 403
    
    # For audio files, serve for playback (not as attachment)
    # For other files, download as attachment
    as_attachment = not file_path.suffix.lower() in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
    
    return send_file(str(file_path), as_attachment=as_attachment)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

