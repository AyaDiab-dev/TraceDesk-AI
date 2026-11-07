
  import { useCallback, useEffect, useRef, useState } from 'react'


async function classifyVoiceWake(text) {
  const utterance = text.trim().replace(/[.!?،؟]+$/g, '').trim()

  if (!utterance) return false

  // Fast path: only an isolated, explicit wake phrase.
  // Longer sentences go through semantic classification
  // to distinguish direct address from quoted speech.
  const exactWakePhrases = new Set([
    'hey tracedesk',
    'hi tracedesk',
    'hello tracedesk',
    'tracedesk',
    'hey trace desk',
    'hi trace desk',
    'hello trace desk',
    'trace desk',
    'يا تريس ديسك',
    'مرحبا تريس ديسك',
    'היי טרייס דסק',
  ])

  if (exactWakePhrases.has(utterance.toLowerCase())) {
    return true
  }

  // No assistant-name candidate: avoid unnecessary LLM calls.
  const possibleName =
    /\btrace\s*desk\b/i.test(utterance) ||
    /تريس\s*ديسك/.test(utterance) ||
    /טרייס\s*דסק/.test(utterance)

  if (!possibleName) return false

  // Semantic fallback for ambiguous sentences.
  try {
    const response = await fetch('/api/voice/wake-intent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: utterance }),
    })

    if (!response.ok) return false

    const decision = await response.json()

    return (
      decision.intent === 'WAKE' &&
      decision.should_wake === true
    )
  } catch {
    return false
  }
}


function normalizeVoiceErrorCodes(text) {
  return text.replace(
    /\b(?:an\s+x|n\s*x|nx)\s*[- ]?\s*(112|403|503|781)\b/gi,
    (_, code) => `NX-${code}`
  )
}

function extractWakeRequest(text) {
  const wakePrefix =
    /^(?:(?:hey|hi|hello)\s+)?trace\s*desk\b[\s,.:!?-]*/i

  const arabicPrefix =
    /^(?:(?:يا|مرحبا)\s+)?تريس\s*ديسك[\s،.!؟:-]*/

  const hebrewPrefix =
    /^(?:היי\s+)?טרייס\s*דסק[\s,.!?׃:-]*/

  for (const pattern of [wakePrefix, arabicPrefix, hebrewPrefix]) {
    if (pattern.test(text.trim())) {
      return text.trim().replace(pattern, '').trim()
    }
  }

  return text.trim()
}

  function detectTextLanguage(text, fallback = 'en-US') {
    const arabic = (text.match(/[\u0600-\u06FF]/g) || []).length
    const hebrew = (text.match(/[\u0590-\u05FF]/g) || []).length

    if (arabic > hebrew && arabic > 0) return 'ar-SA'
    if (hebrew > 0) return 'he-IL'
    return fallback
  }

  function splitSpeechSegments(text, fallback = 'en-US') {
    const parts = text.match(
      /[\u0600-\u06FF][\u0600-\u06FF\s،؟.!:؛-]*|[\u0590-\u05FF][\u0590-\u05FF\s,.!?-]*|[A-Za-z][A-Za-z0-9\s,.!?'-]*/g
    )

    if (!parts?.length) {
      return [{ text, lang: detectTextLanguage(text, fallback) }]
    }

    return parts
      .map((part) => ({
        text: part.trim(),
        lang: detectTextLanguage(part, 'en-US'),
      }))
      .filter((part) => part.text)
  }

  function findVoice(voices, language) {
    const normalized = language.toLowerCase()
    const prefix = normalized.split('-')[0]

    return (
      voices.find((voice) => voice.lang.toLowerCase() === normalized) ||
      voices.find((voice) =>
        voice.lang.toLowerCase().startsWith(`${prefix}-`)
      ) ||
      voices.find((voice) => voice.lang.toLowerCase() === prefix) ||
      null
    )
  }

  export function useVoiceAssistant({
    onTranscript,
    language = 'en-US',
  }) {
    const [voiceStatus, setVoiceStatus] = useState('idle')
    const [voiceError, setVoiceError] = useState('')

    const speakRef = useRef(null)
    const recognitionRef = useRef(null)
    const utteranceRef = useRef(null)
    const activeRef = useRef(false)
    const busyRef = useRef(false)
    const sendRef = useRef(onTranscript)
    const languageRef = useRef(language)
    const generationRef = useRef(0)
    const listenRef = useRef(null)
    const conversationRef = useRef(false)
    const directModeRef = useRef(false)
    const lastInteractionRef = useRef(0)
    const restartTimerRef = useRef(null)
    const conversationTimerRef = useRef(null)
    const CONVERSATION_TIMEOUT_MS = 30000

    useEffect(() => {
      sendRef.current = onTranscript
      languageRef.current = language
    }, [onTranscript, language])

    const stop = useCallback(() => {
      activeRef.current = false
      generationRef.current += 1

      conversationRef.current = false
      directModeRef.current = false
      lastInteractionRef.current = 0

      clearTimeout(restartTimerRef.current)
      restartTimerRef.current = null

      clearTimeout(conversationTimerRef.current)
      conversationTimerRef.current = null

      const recognition = recognitionRef.current
      recognitionRef.current = null
      recognition?.abort()

      utteranceRef.current = null

      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }

      busyRef.current = false
      setVoiceStatus('idle')
    }, [])

    const listen = useCallback(() => {
      if (!activeRef.current || busyRef.current || recognitionRef.current) {
        return
      }

      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition

      if (!SpeechRecognition) {
        setVoiceError('Speech recognition is unavailable in this browser.')
        stop()
        return
      }

      const generation = generationRef.current
      const recognition = new SpeechRecognition()

      recognitionRef.current = recognition
      recognition.lang = languageRef.current
      recognition.continuous = false
      recognition.interimResults = true

      let transcript = ''
      let failed = false
      let failureReason = ''

      recognition.onstart = () => {
        if (activeRef.current && generation === generationRef.current) {
          setVoiceStatus(
            conversationRef.current ? 'listening' : 'standby'
          )
        }
      }

      recognition.onresult = (event) => {
        transcript = Array.from(event.results)
          .filter((result) => result.isFinal)
          .map((result) => result[0].transcript)
          .join(' ')
          .trim()
      }

      recognition.onerror = (event) => {
        failureReason = event.error
        failed = true

        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          setVoiceError(`Speech recognition error: ${event.error}`)
        }
      }


  recognition.onend = async () => {
    if (recognitionRef.current === recognition) {
      recognitionRef.current = null
    }

    if (!activeRef.current || generation !== generationRef.current) {
      return
    }

    const restartListening = () => {
      if (!activeRef.current || generation !== generationRef.current) {
        return
      }

      clearTimeout(restartTimerRef.current)

      restartTimerRef.current = setTimeout(() => {
        restartTimerRef.current = null
        listenRef.current?.()
      }, 350)
    }

    if (failed) {
      // Silence is normal while waiting for a wake phrase.
      if (failureReason === 'no-speech') {
        restartListening()
        return
      }

      stop()
      return
    }

    if (!transcript) {
      restartListening()
      return
    }

    const now = Date.now()

    if (
      conversationRef.current &&
      now - lastInteractionRef.current > CONVERSATION_TIMEOUT_MS
    ) {
      conversationRef.current = false
      directModeRef.current = false
      lastInteractionRef.current = 0
    }

    let message = transcript

    if (!conversationRef.current) {
    setVoiceStatus('thinking')

    const shouldWake =
      directModeRef.current ||
      (await classifyVoiceWake(transcript))
      if (!activeRef.current || generation !== generationRef.current) {
        return
      }

      if (!shouldWake) {
        setVoiceStatus('standby')
        restartListening()
        return
      }


conversationRef.current = true

// Remove the wake phrase before sending the actual request.
message = extractWakeRequest(transcript)

// Wake-only utterance: greet locally and wait for the question.
if (!message) {
  lastInteractionRef.current = Date.now()
  busyRef.current = true

  const greeting =
    languageRef.current.startsWith('ar')
      ? 'مرحبًا! كيف يمكنني مساعدتك؟'
      : languageRef.current.startsWith('he')
        ? 'שלום! איך אפשר לעזור?'
        : 'Hi! How can I help you?'

  speakRef.current?.(greeting)
  return
}

    }

    lastInteractionRef.current = now
    busyRef.current = true
    setVoiceStatus('thinking')
    clearTimeout(conversationTimerRef.current)
    conversationTimerRef.current = null

    try {
      const normalizedMessage = normalizeVoiceErrorCodes(message)
    await sendRef.current(normalizedMessage)
    }
    catch (error) {
      setVoiceError(error.message || 'Unable to send voice message.')
      stop()
    }
  }


      try {
        recognition.start()
      } catch (error) {
        setVoiceError(error.message || 'Unable to start recognition.')
        stop()
      }
    }, [stop])

    useEffect(() => {
      listenRef.current = listen
    }, [listen])

    const speak = useCallback((text) => {
      if (!activeRef.current || !text) return

      if (!('speechSynthesis' in window)) {
        setVoiceError('Speech synthesis is unavailable in this browser.')
        stop()
        return
      }

      const generation = generationRef.current
      const synthesis = window.speechSynthesis
      const segments = splitSpeechSegments(text, languageRef.current)
      const voices = synthesis.getVoices()

      const missingLanguages = [
        ...new Set(
          segments
            .filter((segment) => !findVoice(voices, segment.lang))
            .map((segment) => segment.lang)
        ),
      ]

      if (missingLanguages.length > 0) {
        setVoiceError(
          `No installed voice for: ${missingLanguages.join(', ')}`
        )
        stop()
        return
      }

      synthesis.cancel()
      setVoiceStatus('speaking')

      let index = 0

      const speakNext = () => {
        if (!activeRef.current || generation !== generationRef.current) {
          return
        }

       if (index >= segments.length) {
        utteranceRef.current = null

        lastInteractionRef.current = Date.now()
        busyRef.current = false

        clearTimeout(conversationTimerRef.current)

        conversationTimerRef.current = setTimeout(() => {
          conversationTimerRef.current = null

          if (!activeRef.current || generation !== generationRef.current) {
            return
          }

          conversationRef.current = false
          directModeRef.current = false
          lastInteractionRef.current = 0
          setVoiceStatus('standby')
        }, CONVERSATION_TIMEOUT_MS)

        setVoiceStatus('listening')
        listenRef.current?.()
        return
      }

        const segment = segments[index]
        index += 1

        const utterance = new SpeechSynthesisUtterance(segment.text)

        utteranceRef.current = utterance
        utterance.lang = segment.lang
        utterance.voice = findVoice(voices, segment.lang)
        utterance.rate = 0.95
        utterance.pitch = 1

        utterance.onend = () => {
          if (generation !== generationRef.current) return
          speakNext()
        }

        utterance.onerror = (event) => {
          if (!activeRef.current || generation !== generationRef.current) {
            return
          }

          setVoiceError(`Speech playback failed: ${event.error}`)
          stop()
        }

        synthesis.speak(utterance)
      }

      speakNext()
    }, [stop])
    speakRef.current = speak
    const start = useCallback(() => {
  if (activeRef.current) return

  setVoiceError('')
  activeRef.current = true
  busyRef.current = false
  generationRef.current += 1
  setVoiceStatus('standby')

  listen()
}, [listen])

// Start a direct voice conversation without requiring "Hey TraceDesk".
const startDirect = useCallback(() => {
  if (busyRef.current) return

  clearTimeout(conversationTimerRef.current)
  conversationTimerRef.current = null

  clearTimeout(restartTimerRef.current)
  restartTimerRef.current = null

  directModeRef.current = true
  conversationRef.current = true
  lastInteractionRef.current = Date.now()

  setVoiceError('')
  activeRef.current = true

  const recognition = recognitionRef.current

  if (recognition) {
    // Reuse the current recognition session instead of
    // starting a second one while the first is active.
    setVoiceStatus('listening')
    return
  }

  generationRef.current += 1
  setVoiceStatus('listening')
  listenRef.current?.()
}, [])

useEffect(() => {
  return () => {
    activeRef.current = false
    generationRef.current += 1
    recognitionRef.current?.abort()
    recognitionRef.current = null
    utteranceRef.current = null
    window.speechSynthesis?.cancel()
  }
}, [])

    return {
      voiceStatus,
      voiceError,
      start,
      startDirect,
      stop,
      speak,
      isVoiceActive: voiceStatus !== 'idle',
    }
  }
