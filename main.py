import subprocess
import re
from tqdm import tqdm
import os


directory = "video/"


files = os.listdir(directory)
mp4_files = [f for f in files if f.endswith('.mp4')]
mp3_files = [f for f in files if f.endswith('.mp3')]


if len(mp4_files) != 1 or len(mp3_files) != 1:
    raise Exception("В директории должно быть ровно один файл .mp4 и один файл .mp3")

video_path = os.path.join(directory, mp4_files[0])
audio_path = os.path.join(directory, mp3_files[0])
output_path = os.path.join(f"codec {mp4_files[0]}")


def get_duration(filename):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8"
    )
    return float(result.stdout)


duration = get_duration(video_path)

command = [
    "ffmpeg",
    "-i",
    video_path,
    "-i",
    audio_path,
    "-c:v",
    "copy",
    "-c:a",
    "aac",
    "-strict",
    "experimental",
    output_path,
]

progress_pattern = re.compile(r"time=(\d+:\d+:\d+\.\d+)")


def time_to_seconds(column_time):
    h, m, s = map(float, column_time.split(":"))
    return h * 3600 + m * 60 + s


process = subprocess.Popen(
    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", universal_newlines=True
)

with tqdm(total=duration, unit="s", unit_scale=True, desc="Сшивание аудио и видео",
          bar_format="{l_bar}{bar}{n:.1f}/{total_fmt} ({percentage:.1f}%) [{elapsed}<{remaining}]") as pbar:
    for line in process.stdout:
        match = progress_pattern.search(line)
        if match:
            time_str = match.group(1)
            seconds = time_to_seconds(time_str)
            pbar.update(seconds - pbar.n)

process.wait()

if process.returncode == 0:
    # Вычисление размера выходного файла
    file_size_bytes = os.path.getsize(output_path)
    if file_size_bytes < 1024 ** 2:
        file_size = f"{file_size_bytes / 1024:.2f} КБ"
    elif file_size_bytes < 1024 ** 3:
        file_size = f"{file_size_bytes / (1024 ** 2):.2f} МБ"
    else:
        file_size = f"{file_size_bytes / (1024 ** 3):.2f} ГБ"

    print("\nВидео и аудио успешно объединены.")
    print(f"Размер выходного файла: {file_size}")
else:
    print("\nПроизошла ошибка.")
