import os
import re
import subprocess
from typing import List

from tqdm import tqdm

directory =  eo/"
files = os.listdir(directory)

mp4_files: List[str] = [f for f in files if f.endswith(".mp4")]
mp3_files: List[str] = [f for f in files if f.endswith(".mp3")]

if len(mp4_files) != 1 or len(mp3_files) != 1:
    raise Exception("В директории должно быть ровно один файл .mp4 и один файл .mp3")

video_path: str = os.path.join(directory, mp4_files[0])
audio_path: str = os.path.join(directory, mp3_files[0])
output_path: str = os.path.join(f"codec_{mp4_files[0]}")


def get_duration(filename: str) -> float:
    """
    Получает длительность файла с помощью ffprobe.

    :param filename: Путь к файлу.
    :return: Длительность файла в секундах.
    """
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
        encoding="utf-8",
    )
    return float(result.stdout)


def time_to_seconds(time_column: str) -> float:
    """
    Преобразует время из формата hh:mm:ss в секунды.

    :param time_column: Время в формате hh:mm:ss.
    :return: Время в секундах.
    """
    h, m, s = map(float, time_column.split(":"))
    return h * 3600 + m * 60 + s


def get_video_duration(file_path: str) -> float:
    """
    Получает длительность видео файла с помощью ffmpeg.

    :param file_path: Путь к видео файлу.
    :return: Длительность видео в секундах.
    """
    result = subprocess.run(
        ["ffmpeg", "-i", file_path],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # Поиск строки с длительностью
    for lines in result.stderr.split("\n"):
        if "Duration" in lines:
            duration_str = lines.split(",")[0].split("Duration:")[1].strip()
            h, m, s = duration_str.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0


def split_video(file_path: str, part_size_gb: float = 1.9) -> None:
    """
    Разбивает видео на части по 1.9 ГБ или другой заданной размерности.

    :param file_path: Путь к видео файлу.
    :param part_size_gb: Размер одной части в гигабайтах (по умолчанию 1.9 ГБ).
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл '{file_path}' не найден.")

        video_duration = get_video_duration(file_path)
        if video_duration == 0:
            raise ValueError(f"Не удалось получить длительность видео '{file_path}'.")

        part_size_bytes = int(part_size_gb * 1024 * 1024 * 1024)
        size = os.path.getsize(file_path)
        part_duration = video_duration * (part_size_bytes / size)

        print(f"Размер файла: {size / (1024 * 1024 * 1024):.2f} ГБ")
        print(f"Разбиение на части по ~{part_duration / 60:.2f} минут...")

        part_num = 1
        start_time = 0.0
        while start_time < video_duration:
            output_file = f"{file_path}_part{part_num}.mp4"
            arguments_codec = [
                "ffmpeg",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-strict", "experimental",
                output_path,
            ]
            subprocess.run(
                arguments_codec, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            print(
                f"Часть {part_num} завершена ({(start_time / video_duration) * 100:.2f}%)"
            )
            start_time += part_duration
            part_num += 1

        print("Разбиение завершено успешно.")

    except Exception as e:
        print(f"Ошибка: {e}")


duration: float = get_duration(video_path)

command: List[str] = [
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

process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    encoding="utf-8",
    universal_newlines=True,
)

with tqdm(
    total=duration,
    unit="s",
    unit_scale=True,
    desc="Сшивание аудио и видео",
    bar_format="{l_bar}{bar}{n:.1f}/{total_fmt} ({percentage:.1f}%) [{elapsed}<{remaining}]",
) as pbar:
    for line in process.stdout:
        match = progress_pattern.search(line)
        if match:
            column_time = match.group(1)
            seconds = time_to_seconds(column_time)
            pbar.update(seconds - pbar.n)

process.wait()

if process.returncode == 0:
    file_size_bytes: int = os.path.getsize(output_path)

    if file_size_bytes < 1024**2:
        file_size = f"{file_size_bytes / 1024:.2f} КБ"
    elif file_size_bytes < 1024**3:
        file_size = f"{file_size_bytes / (1024 ** 2):.2f} МБ"
    else:
        file_size = f"{file_size_bytes / (1024 ** 3):.2f} ГБ"

    print("\nВидео и аудио успешно объединены.")
    print(f"Размер выходного файла: {file_size}")

    # Если размер файла больше 2 ГБ, разбиваем его на части
    if file_size_bytes > 2 * 1024**3:
        print("Файл превышает 2 ГБ. Начинаем разбиение...")
        split_video(output_path)

else:
    print("\nПроизошла ошибка.")
