from allpairspy import AllPairs
import time
from app.test import player

params = [
    ["C4", "C2", "C7"],
    [0.25, 1.0, 2.0],
    [0.3, 1.0]
]
tests = list(AllPairs(params))
print("TC | НОТА | ДЛИНА | VOL | ЗВУК | ПИТЧ | ДЛИНА | ГРОМК | ✅/4")
print("-" * 60)
results = []
for i, (note, duration, volume) in enumerate(tests, 1):
    print(f"\nTC-{i:02d}: ИГРАЕМ {note} {duration}s vol={volume}")
    player.play_note(note, duration, volume)
    time.sleep(duration + 0.5)
    sound = input("  1. Звук слышен? (да/нет): ")
    pitch = input("  2. Питч правильный? (да/нет): ")
    length = input("  3. Длина соответствует? (да/нет): ")
    loudness = input("  4. Громкость соответствует? (да/нет): ")
    passed = sum([1 if x == "да" else 0 for x in [sound, pitch, length, loudness]])
    status = "✅" if passed == 4 else f"{passed}/4"
    print(f"  → RESULT: {status}")
    results.append({
        "tc": i, 
        "note": note, 
        "duration": duration, 
        "volume": volume,
        "sound": sound, 
        "pitch": pitch, 
        "length": length, 
        "loudness": loudness,
        "status": status
    })
print("\n" + "="*80)
print("📊 ФИНАЛЬНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
print("="*80)
print(f"{'TC':>2} | {'НОТА':>2} | {'ДЛИНА':>4} | {'VOL':>3} | {'ЗВУК':>3} | {'ПИТЧ':>3} | {'ДЛИНА':>4} | {'ГРОМК':>5} | {'СТАТУС':>5}")
print("-" * 80)
total_passed = 0
for result in results:
    status_icon = "✅" if result["status"] == "✅" else "❌"
    print(f"{result['tc']:>2} | {result['note']:<2} | {result['duration']:>4.2f} | {result['volume']:>3.1f} | {result['sound']:<3} | {result['pitch']:<3} | {result['length']:<4} | {result['loudness']:<5} | {status_icon}")
    if result["status"] == "✅":
        total_passed += 1
print("-" * 80)
print(f"📈 ИТОГО: {total_passed}/9 тестов ПРОЙДЕНЫ ✅")
print(f"📉 НЕ ПРОЙДЕНО: {9-total_passed}/9 тестов ❌")
