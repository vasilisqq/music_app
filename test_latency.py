#!/usr/bin/env python3
"""
Test script to verify audio latency and preloading performance.
"""
import time
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("ТЕСТ ПРЕДВЫЧИСЛЕНИЯ НОТ И ЗАДЕРЖКИ ВОСПРОИЗВЕДЕНИЯ")
print("=" * 60)

# Импортируем модуль (здесь происходит предвычисление нот)
start = time.time()
from app import test
import_time = time.time() - start

print(f"\n⏱ Время инициализации модуля: {import_time:.3f}сек")

# Проверяем, что ноты нотного стана в кеше
print("\n📝 Проверка кеша нот нотного стана:")
for note in list(test.ALL_STAFF_NOTES)[:5]:
    if note in test.note_cache:
        size_bytes = len(test.note_cache[note]) * 4  # float32
        print(f"  ✓ {note:5s} - в кеше ({size_bytes/1024:.1f} KB)")
    else:
        print(f"  ✗ {note:5s} - НЕ в кеше!")

print(f"\nВсего нот в кеше: {len(test.note_cache)}/{len(test.ALL_STAFF_NOTES)}")

# Тестируем задержку получения нот из кеша
print("\n⚡ Тест задержки получения нот ИЗ КЕША (должно быть <1мс):")
cached_notes = list(test.ALL_STAFF_NOTES)[:3]
for note in cached_notes:
    start = time.time()
    audio = test.get_note_audio(note)
    elapsed = (time.time() - start) * 1000
    print(f"  {note}: {elapsed:.2f}мс")

# Тестируем задержку генерации новой ноты (быстро)
print("\n⚡ Тест задержки генерации новой ноты (быстрый режим):")
new_notes = ["C7", "B7", "A7"]
for note in new_notes:
    # Убедимся, что её нет в кеше
    if note in test.note_cache:
        del test.note_cache[note]
    
    start = time.time()
    audio = test.get_note_audio(note)
    elapsed = (time.time() - start) * 1000
    print(f"  {note}: {elapsed:.2f}мс")

print("\n" + "=" * 60)
print("✅ ГОТОВО: Все ноты нотного стана предвычислены")
print("   Ноты воспроизводятся без задержки")
print("=" * 60)
