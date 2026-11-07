
"""Live evaluation; calls OpenRouter once per example and reports false activations.
Run only after deterministic tests pass. Uses actual model, so costs may apply.
"""
from agent.voice_intent import WakeIntent, classify_wake_intent

CASES = [
    ("Hey TraceDesk, I need help with VPN", WakeIntent.WAKE),
    ("TraceDesk, are you there?", WakeIntent.WAKE),
    ("Excuse me, could you help me reset my password?", WakeIntent.WAKE),
    ("يا تريس ديسك، ممكن تساعدني؟", WakeIntent.WAKE),
    ("لو سمحت ساعدني أصلح مشكلة الـVPN", WakeIntent.WAKE),
    ("היי טרייס דסק, אני צריכה עזרה", WakeIntent.WAKE),
    ("אפשר לעזור לי עם ה-VPN?", WakeIntent.WAKE),
    ("Hey John, can you help with the printer?", WakeIntent.IGNORE),
    ("مرحبا أحمد، كيف حالك؟", WakeIntent.IGNORE),
    ("שלום דני, מה נשמע?", WakeIntent.IGNORE),
    ("I was talking to my colleague about the VPN", WakeIntent.IGNORE),
    ("She said 'Hey TraceDesk' during the demo", WakeIntent.IGNORE),
    ("We should ask TraceDesk tomorrow", WakeIntent.IGNORE),
    ("مرحبا", WakeIntent.UNCERTAIN),
    ("Hello", WakeIntent.UNCERTAIN),
    ("שלום", WakeIntent.UNCERTAIN),
    ("My VPN", WakeIntent.UNCERTAIN),
]


def main():
    errors = 0
    false_wakes = 0

    for text, expected in CASES:
        result = classify_wake_intent(text)

        ok = result.intent is expected
        errors += not ok
        false_wakes += (
            result.should_wake
            and expected is not WakeIntent.WAKE
        )

        print(
            f"{'PASS' if ok else 'FAIL'} "
            f"expected={expected.value:9} "
            f"got={result.intent.value:9} | {text}"
        )

    print(
        f"\nTotal: {len(CASES)} "
        f"| Correct: {len(CASES)-errors} "
        f"| Errors: {errors} "
        f"| False wakes: {false_wakes}"
    )

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
