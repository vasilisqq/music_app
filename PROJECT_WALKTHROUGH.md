# music_app — подробная инструкция по коду

Этот проект берёт аудиофайл (mp3/wav), разделяет его на стемы (Demucs), транскрибирует один или несколько стемов в MIDI (Basic Pitch), затем (частично) квантует MIDI по битам и делает «пианистичную» редукцию (упрощение/ограничение плотности нот) в один выходной MIDI.

Ниже — максимально подробное описание того, **какие файлы за что отвечают**, в каком порядке всё запускается, что именно происходит с данными на каждом шаге и где настраиваются параметры.

---

## 1) Быстрый старт

### Как запустить

Основная точка запуска — `main.py` (он обычно вызывает функции из `pipeline.py`).

Типичный сценарий локального запуска (по коду `pipeline.run_from_local_file()`):

1. Положить рядом с кодом `input.mp3` (или `input.wav`).
2. Запустить `python main.py` (или напрямую вызвать `pipeline.run_from_local_file()`).
3. На выходе будет папка `separated/...` со стемами и папка `midi_out/` с MIDI.

Что появляется в `midi_out/` (на практике):
- `vocals.mid`, `bass.mid`, `other.mid` — сырые транскрипты стемов.
- `vocals_q.mid`, `bass_q.mid` (и иногда `other_q.mid`, `drums_q.mid`) — квантизованные версии.
- `piano_reduction_playable.mid` — итоговый «играбельный» MIDI.

Фактические имена файлов и логика их появления управляются кодом в `pipeline.py`. 

---

## 2) Общая архитектура пайплайна

Весь процесс можно мысленно разделить на 5 стадий:

1) **Подготовка входа** (mp3 → wav) — `audio_utils.py` + `pipeline.py`.
2) **Разделение на стемы** (Demucs) — `separation.py`.
3) **Транскрипция стемов в MIDI** (Basic Pitch) — `transcription_basic_pitch.py` + `pipeline.py`.
4) **Детект битов** по аудио (madmom) — `beats_madmom.py` + `pipeline.py`.
5) **Квантизация (частичная) + редукция в пиано** — `midi_quantize.py` + `midi_reduce.py` + `pipeline.py`.

Ключевая мысль: на стадии (5) у тебя **две разные операции**:
- *Quantize* — “подогнать события MIDI к сетке битов”.
- *Reduce* — “ограничить плотность/полифонию и собрать удобную для пиано фактуру”.

---

## 3) `pipeline.py` — главный оркестратор

Это центральный файл, который связывает все модули.

### 3.1 `run_from_local_file()`

`run_from_local_file(input_name="input.mp3", always_reseparate=False)` делает полный прогон «с файла на диске»:

1. Вызывает `_materialize_input_as_output_wav()`:
   - Если вход mp3 → конвертирует в `output.wav`.
   - Если вход wav → копирует/использует как `output.wav`.

2. Вычисляет папку стемов `separated/htdemucs/<stem>`.
   - Если `always_reseparate=True` или папки нет — вызывает `separate_stems()`.

3. Запускает `stems_to_midi(...)`:
   - На этом шаге **Basic Pitch** создаёт `vocals.mid/bass.mid/other.mid` (или пустые MIDI, если стем молчит).

4. Запускает `quantize_and_reduce_pipeline(...)`:
   - На этом шаге находится детект битов + квантизация + пиано-редукция.

### 3.2 `stems_to_midi()`

`stems_to_midi(stems_dir, midi_dir, transcribe_drums=False)`:

- Создаёт набор параметров Basic Pitch (`BasicPitchParams`) для каждого стема (vocals/bass/other) из `config.py`.
- Для каждого стема вызывает `transcribe_or_empty(...)`:
  - Если файла стема нет → пишет пустой MIDI.
  - Если стем «тихий» (по `audio_utils.is_wav_silent`) → пишет пустой MIDI.
  - Иначе вызывает `stem_to_midi(stem_wav, out_mid, params)`.

Важно про `config.USE_ONLY_OTHER`:
- Если `USE_ONLY_OTHER=True`, то `vocals.mid` и `bass.mid` принудительно пишутся пустыми, а транскрибируется только `other.wav → other.mid`.

### 3.3 `quantize_and_reduce_pipeline()`

`quantize_and_reduce_pipeline(stems_dir, midi_dir, subdivisions_quant=4, include_drums=False)`:

1. Выбирает аудио для бит-трекинга: ищет по очереди `mixture.wav`, `drums.wav`, `other.wav`.
2. Получает `beat_times = detect_beats_madmom(beat_audio)`.
3. Гарантирует существование `vocals.mid` и `bass.mid` (если их нет — пишет пустые).
4. Квантует вокал и бас:
   - `vocals.mid → vocals_q.mid` через `quantize_midi_file(..., subdivisions=subdivisions_quant)`.
   - `bass.mid → bass_q.mid` аналогично.

5. Выбирает, какой `other.mid` использовать:
   - Если `config.OTHER_USE_QUANTIZATION=True`, делает `other_q.mid` и использует его.
   - Иначе использует исходный `other.mid` как есть.

6. (опционально) квантует барабаны, если включено.
7. Вызывает `complete_midi(...)` из `midi_reduce.py`, который собирает финальный `piano_reduction_playable.mid`.

---

## 4) `config.py` — все настройки

`config.py` — это твоя «панель управления». Почти все числа, которые влияют на результат, живут тут.

### 4.1 Переключатели

- `USE_ONLY_OTHER`: если True — используешь только стем OTHER.
- `OTHER_USE_QUANTIZATION`: если True — создаётся `other_q.mid` и он используется дальше.
- `OTHER_DENSE_MODE`: если True — включается твоя плотная «играбельная текстура» из OTHER (см. `midi_reduce.complete_midi`).

### 4.2 Basic Pitch

Параметры вида:
- `BP_*_ONSET_THRESHOLD`
- `BP_*_FRAME_THRESHOLD`
- `BP_*_MIN_NOTE_LENGTH`

влияют на то, какие ноты Basic Pitch вообще создаст.

Важно: если `BP_OTHER_MIN_NOTE_LENGTH` слишком большой, короткие ноты могут **не появиться уже на этапе транскрипции**, и дальнейшая обработка их не вернёт.

### 4.3 Dense OTHER

Параметры dense-ветки (используются в `midi_reduce.py`):
- `OTHER_DENSE_GRID_SUBDIV`: насколько мелко режется сетка внутри бита.
- `OTHER_DENSE_MAX_NOTES`: сколько максимум нот брать в одном временном срезе.
- `OTHER_DENSE_HAND_SPAN`: ограничение «растяжки руки» (если слишком широко — оставляется верхняя нота).
- `OTHER_DENSE_HOLD_SEC`: искусственно продлевает все ноты перед нарезкой (уменьшает выпадения).
- `OTHER_DENSE_MIN_VEL`: минимальная velocity, ниже которой ноты выкидываются.
- `OTHER_DENSE_MIN_DUR_SEC`: минимальная длительность ноты ("пыль" режется).
- `OTHER_DENSE_PROBE_EPS_SEC`: на сколько секунд смещать точку проверки активности внутри слайса.

---

## 5) `audio_utils.py` — конвертация и тишина

Обычно тут две важные вещи:

1) `convert_to_wav(...)` — используется, когда вход mp3.
2) `is_wav_silent(...)` — применяется перед транскрипцией, чтобы не гонять Basic Pitch на пустом/тихом аудио.

Порог тишины настраивается в `config.py` через:
- `STEM_SILENCE_RMS_DBFS`
- `STEM_SILENCE_PEAK_DBFS`

---

## 6) `separation.py` — Demucs

`separate_stems(wav_path)` просто прокидывает `wav_path` в `demucs.separate.main(...)`.

Demucs создаёт структуру `separated/htdemucs/<track>/` со стемами (`vocals.wav`, `bass.wav`, `drums.wav`, `other.wav`, `mixture.wav` — в зависимости от модели).

---

## 7) `beats_madmom.py` — биты

`detect_beats_madmom(...)` возвращает список `beat_times: list[float]` — моменты времени битов (в секундах).

Это критично важно, потому что:
- по этим битам строится сетка квантизации (в `midi_quantize.py`);
- по этим же битам строится сетка нарезки dense-режима (в `midi_reduce.py`).

Если бит-трекер ошибается (сдвиг, пропуски, двойные биты), то вся дальнейшая сетка будет «косая».

---

## 8) `midi_quantize.py` — квантизация MIDI по битам

Файл делает “музыкальную сетку” из `beat_times` и подгоняет `note.start/end` к ней.

### 8.1 `_build_subbeat_grid(beat_times, subdivisions)`

- Берёт `beat_times`, сортирует.
- Считает разницы между битами, берёт медианный период.
- **Важно:** если первый бит начинается не с 0.0, функция расширяет биты назад до 0.0 (чтобы ноты в интро не «прилипали» к первому найденному биту и не делали тишину в начале).
- Строит сетку между каждым соседним битом, деля интервал на `subdivisions` частей.

Итог: `grid: list[float]` — возрастающий список времён.

### 8.2 `quantize_pretty_midi_to_beats(...)`

Для каждого инструмента и каждой ноты:
- Берёт исходные `s0/e0`.
- Квантует `start` в `s` по режиму (`nearest/floor/ceil`).
- Оценивает длительность в шагах сетки.
- Ставит `end` в `e = s + steps*min_step_sec`.
- Потом делает чистку:
  - `_merge_adjacent_same_pitch(...)` — склеивает соседние ноты одного pitch.
  - `_remove_same_pitch_overlaps(...)` — убирает самоперекрытия.

Это квантизация именно времени/длительности, а не выбор нот.

---

## 9) `midi_reduce.py` — редукция в пиано

Это второй «тяжёлый» модуль: он пытается сделать MIDI удобным для пианино.

### 9.1 Общая идея `complete_midi()`

`complete_midi(vocals_mid, bass_mid, other_mid, drums_mid, out_mid, beat_times, ...)`:

1. Загружает входные MIDI через `pretty_midi.PrettyMIDI(...)`.
2. Собирает ноты из инструментов (`_iter_notes`) и чистит их (`_clean_notes`):
   - отбрасывает по диапазону, длительности, velocity.

3. Делает левую руку (bass) как «текстуру» на сетке `MELODY_GRID_SUBDIV`:
   - `_limit_polyphony_on_grid(...)` выбирает несколько активных нот на каждом шаге.

4. Делает правую руку из OTHER в dense-режиме (если включено):
   - Строит более плотную сетку `OTHER_DENSE_GRID_SUBDIV`.
   - Опционально продлевает исходные ноты `OTHER_DENSE_HOLD_SEC`.
   - Фильтрует мусор по `OTHER_DENSE_MIN_VEL` и `OTHER_DENSE_MIN_DUR_SEC`.
   - На каждом срезе выбирает `OTHER_DENSE_MAX_NOTES` самых громких.
   - Ограничивает растяжку руки `OTHER_DENSE_HAND_SPAN`.

5. Финальная чистка:
   - `_merge_adjacent_same_pitch` и `_remove_same_pitch_overlaps` отдельно для RH/LH.

6. Пишет `out_mid`.

### 9.2 `_limit_polyphony_on_grid()` — главный “слайсер”

Эта функция берёт **все ноты** (например, raw OTHER) и для каждого временного интервала `[a, b]`:

1. Выбирает момент проверки `probe_t = a + probe_eps_sec`.
2. Находит активные ноты в этот момент (`_active_notes_at`).
3. Сортирует активные ноты:
   - либо по velocity,
   - либо по pitch.
4. Берёт только первые `max_notes_per_slice`.
5. Применяет ограничение руки (`hand_span_limit`), при необходимости оставляет только верхнюю ноту.
6. Создаёт выходные ноты.

Ключевой момент (важно для понимания поведения длительностей):
- Если включён `keep_original_ends=True`, то выходная нота имеет `end = max(b, n.end)`.
- Если `keep_original_ends=False`, то выходная нота ограничивается `end=b`.

То есть функция одновременно:
- “сэмплирует” фактуру во времени,
- и решает, какой конец ставить каждой выбранной ноте.

### 9.3 Почему ноты могут “пропадать”

Нота может не попасть в результат, если:
- Она не активна в момент `probe_t` (слишком короткая или начинается/заканчивается на границе слайса).
- Её выкинул `_clean_notes` по `min_dur/min_vel/диапазону`.
- Она проиграла конкуренцию по velocity (в слайсе было больше нот, чем `max_notes_per_slice`).
- Её убрали ограничения руки (`hand_span_limit`) — оставили только верхнюю.

---

## 10) `transcription_basic_pitch.py` — транскрипция

`stem_to_midi(stem_wav, out_mid, params)` — обёртка над моделью Basic Pitch.

`BasicPitchParams` задаёт пороги и минимальную длину ноты (в миллисекундах/фреймах — зависит от реализации внутри third_party), которые сильно влияют на:
- количество нот,
- точность onsets,
- наличие/отсутствие очень коротких событий.

Если тебя интересуют пропажи **до** редукции, первым делом смотри `BP_*` параметры.

---

## 11) Где что дебажить

Если «ноты пропадают» — важно понять, на каком шаге:

1) Проверка `midi_out/other.mid` (сырое):
- Если уже здесь нет нот — причина в Basic Pitch / silence detection.

2) Если используешь квантизацию OTHER: проверить `midi_out/other_q.mid`:
- Если ноты появились/исчезли тут — причина в `midi_quantize.py` настройках (`subdivisions`, `start_mode`, `merge_gap`, `keep_repeated_notes`).

3) Проверка финального `piano_reduction_playable.mid`:
- Если в `other.mid` ноты есть, а в финале нет — причина в `midi_reduce.py` (фильтры, polyphony, hand_span, probe).

---

## 12) Типичные ручки (что крутить)

### Больше нот (гуще)
- Увеличить `OTHER_DENSE_MAX_NOTES`.
- Уменьшить `OTHER_DENSE_MIN_VEL`.
- Уменьшить `OTHER_DENSE_MIN_DUR_SEC`.

### Меньше выпадений коротких нот
- Увеличить `OTHER_DENSE_HOLD_SEC`.
- Уменьшить `OTHER_DENSE_PROBE_EPS_SEC` (часто 0.0–1e-5 лучше).

### Более “пианистично” (не широко)
- Уменьшить `OTHER_DENSE_HAND_SPAN`.

### Меньше «дробилки» по времени
- Уменьшить `OTHER_DENSE_GRID_SUBDIV`.

---

## 13) Что важно помнить про текущую логику

- У тебя **две сетки**:
  - сетка квантизации (для vocals/bass и опционально other/drums),
  - сетка dense-редукции (для playable OTHER).

- Dense-редукция — это не “оставить MIDI как есть”, а реконструкция фактуры: она всегда выбирает подмножество нот в каждый момент времени.

- Поведение длительностей в dense-режиме определяется параметром `keep_original_ends` в `_limit_polyphony_on_grid()` и тем, делал ли ты `_add_hold()`.

---

## 14) Файлы проекта (кто за что)

- `main.py` — точка запуска.
- `pipeline.py` — оркестратор всего процесса.
- `config.py` — все настройки.
- `audio_utils.py` — конвертация mp3→wav и детект тишины.
- `separation.py` — Demucs separation.
- `beats_madmom.py` — beat tracking.
- `transcription_basic_pitch.py` — Basic Pitch transcription.
- `midi_quantize.py` — квантизация MIDI по `beat_times`.
- `midi_reduce.py` — редукция/ограничение плотности и сборка финального пиано MIDI.

---

Если нужно, можно добавить в этот документ отдельный раздел «как подобрать параметры под конкретный трек» (например под `beth.mp3` vs `kor.mp3`) и чеклист “если слышны паузы/если каша/если слишком много нот”.
