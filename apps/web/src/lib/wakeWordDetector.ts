/**
 * Wake word detector using the browser SpeechRecognition API.
 * Listens continuously in passive mode for "Amin" / "Hey Amin" / "OK Amin"
 * and fires a callback when detected.
 */

type SpeechRecognitionEvent = Event & {
  results: SpeechRecognitionResultList;
  resultIndex: number;
};

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event & { error: string }) => void) | null;
  onend: (() => void) | null;
}

const KEYWORDS = ['amin', 'hey amin', 'okay amin', 'ok amin'];

export class WakeWordDetector {
  private recognition: BrowserSpeechRecognition | null = null;
  private _onWake: () => void;
  private _running = false;
  private _intentionallyStopped = false;
  private _restartTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(onWake: () => void) {
    this._onWake = onWake;
  }

  static isSupported(): boolean {
    return !!(
      (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition
    );
  }

  start(): void {
    if (this._running) return;
    if (!WakeWordDetector.isSupported()) {
      return;
    }

    const SRConstructor = ((window as unknown as Record<string, unknown>)
      .SpeechRecognition ||
      (window as unknown as Record<string, unknown>)
        .webkitSpeechRecognition) as new () => BrowserSpeechRecognition;

    this.recognition = new SRConstructor();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';
    this.recognition.maxAlternatives = 1;

    this._intentionallyStopped = false;
    this._running = true;

    this.recognition.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript.toLowerCase().trim();
        if (KEYWORDS.some(kw => transcript.includes(kw))) {
          this.stop();
          this._onWake();
          return;
        }
      }
    };

    this.recognition.onerror = event => {
      const err = event.error;
      if (err === 'aborted' || err === 'no-speech') return;
    };

    this.recognition.onend = () => {
      if (!this._intentionallyStopped && this._running) {
        this._restartTimer = setTimeout(() => {
          if (this._running && !this._intentionallyStopped) {
            try {
              this.recognition?.start();
            } catch {
              /* ignore */
            }
          }
        }, 300);
      }
    };

    try {
      this.recognition.start();
    } catch (e) {
      this._running = false;
    }
  }

  stop(): void {
    this._intentionallyStopped = true;
    this._running = false;
    if (this._restartTimer) {
      clearTimeout(this._restartTimer);
      this._restartTimer = null;
    }
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        /* ignore */
      }
      this.recognition = null;
    }
  }

  get running(): boolean {
    return this._running;
  }
}
