/**
 * Amin Voice Client — WebSocket connection to the backend voice proxy
 * which relays audio to/from OpenAI Realtime API.
 *
 * Captures microphone via AudioWorklet, streams PCM16 base64 frames,
 * receives assistant audio and plays it back.
 */

import { getApiBaseUrl } from './api';

function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

const BACKPRESSURE_THRESHOLD = 64 * 1024;

const WORKLET_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const float32 = input[0];
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }
    return true;
  }
}
registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
`;

export type VoiceEventHandler = {
  onTranscript?: (text: string, role: 'user' | 'amin') => void;
  onSpeakingChange?: (speaking: boolean) => void;
  onListeningChange?: (listening: boolean) => void;
  onAssistantSpeakingChange?: (speaking: boolean) => void;
  onError?: (error: string) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onReconnecting?: () => void;
  onAutoIdle?: () => void;
  onStandbyRequested?: () => void;
};

let _singletonInstance: AminVoiceClient | null = null;
let _activeVoice = 'onyx';
let _activeLanguage = 'en';

const MALE_VOICES = new Set(['onyx', 'echo', 'fable']);
const SUPPORTED_LANGUAGES = new Set(['en', 'ar', 'fr', 'ur', 'tl']);

const LANGUAGE_INSTRUCTIONS: Record<string, string> = {
  en: 'CRITICAL INSTRUCTION: You MUST respond exclusively in English.',
  ar: 'CRITICAL INSTRUCTION: You MUST respond exclusively in Arabic. Every single word of your response must be in Arabic. Do not use English under any circumstances.',
  fr: 'CRITICAL INSTRUCTION: You MUST respond exclusively in French. Every single word of your response must be in French. Do not use English under any circumstances.',
  ur: 'CRITICAL INSTRUCTION: You MUST respond exclusively in Urdu. Every single word of your response must be in Urdu. Do not use English under any circumstances.',
  tl: 'CRITICAL INSTRUCTION: You MUST respond exclusively in Filipino (Tagalog). Every single word of your response must be in Filipino. Do not use English under any circumstances.',
};

function _buildSessionInstructions(): string {
  const langInstruction =
    LANGUAGE_INSTRUCTIONS[_activeLanguage] ?? LANGUAGE_INSTRUCTIONS.en;
  return `${langInstruction}\n\nYou are Amin, an AI legal assistant specialized in GCC and Saudi Arabian law. You are professional, concise, and helpful.`;
}

export function normalizeLanguage(language: string | null | undefined): string {
  const normalized = language?.trim().toLowerCase();
  return normalized && SUPPORTED_LANGUAGES.has(normalized) ? normalized : 'en';
}

const LANGUAGE_CONFIRMATIONS: Record<string, string> = {
  en: 'I have switched to English. How can I help you?',
  ar: '\u0644\u0642\u062F \u0627\u0646\u062A\u0642\u0644\u062A \u0625\u0644\u0649 \u0627\u0644\u0639\u0631\u0628\u064A\u0629. \u0643\u064A\u0641 \u064A\u0645\u0643\u0646\u0646\u064A \u0645\u0633\u0627\u0639\u062F\u062A\u0643\u061F',
  fr: 'Je suis pass\u00E9 au fran\u00E7ais. Comment puis-je vous aider ?',
  ur: '\u0645\u06CC\u06BA \u0627\u0631\u062F\u0648 \u0645\u06CC\u06BA \u0628\u0627\u062A \u06A9\u0631 \u0631\u06C1\u0627 \u06C1\u0648\u06BA\u06D4 \u0645\u06CC\u06BA \u0622\u067E \u06A9\u06CC \u06A9\u06CC\u0633\u06D2 \u0645\u062F\u062F \u06A9\u0631 \u0633\u06A9\u062A\u0627 \u06C1\u0648\u06BA\u061F',
  tl: 'Lumipat na ako sa Filipino. Paano kita matutulungan?',
};

/**
 * Update the active voice for Amin's realtime session.
 * Takes effect immediately if a session is connected; otherwise
 * applied on next connect. Triggers a spoken confirmation.
 */
export function setVoice(voice: string): void {
  const prev = _activeVoice;
  _activeVoice = MALE_VOICES.has(voice) ? voice : 'onyx';
  if (_singletonInstance?.connected && prev !== _activeVoice) {
    _singletonInstance.sendSessionUpdate({ voice: _activeVoice });
    _singletonInstance.requestSpokenConfirmation(
      'Your voice has been updated. This is how I sound now.'
    );
  }
}

export function getVoice(): string {
  return _activeVoice;
}

/**
 * Update the active language for Amin's realtime session.
 * Sends updated instructions and a spoken confirmation in the new language.
 */
export function setLanguage(language: string): void {
  const prev = _activeLanguage;
  _activeLanguage = normalizeLanguage(language);
  if (_singletonInstance?.connected && prev !== _activeLanguage) {
    _singletonInstance.sendSessionUpdate({
      instructions: _buildSessionInstructions(),
    });
    const confirmation =
      LANGUAGE_CONFIRMATIONS[_activeLanguage] ?? LANGUAGE_CONFIRMATIONS.en;
    _singletonInstance.requestSpokenConfirmation(confirmation);
  }
}

export function getLanguage(): string {
  return _activeLanguage;
}

export class AminVoiceClient {
  private ws: WebSocket | null = null;
  private handlers: VoiceEventHandler;
  private audioContext: AudioContext | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private _sourceNode: MediaStreamAudioSourceNode | null = null;
  private _mediaStream: MediaStream | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private keepaliveTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private maxReconnect = 5;
  private _disconnected = false;
  private _micPaused = false;
  private _userSpeaking = false;
  private lastContext = '';
  private _silenceTimeoutMs = 120_000;
  private _silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private _lastDisconnectTime = 0;
  private _playbackQueue: string[] = [];
  private _isPlaying = false;
  private _assistantSpeaking = false;
  private _sessionReady = false;

  constructor(handlers: VoiceEventHandler = {}) {
    if (_singletonInstance && _singletonInstance !== this) {
      _singletonInstance.disconnect();
    }
    _singletonInstance = this;
    this.handlers = handlers;
  }

  async connect(conversationId?: string): Promise<void> {
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      this._stopKeepalive();
      this._clearSilenceTimer();
      this.ws.onclose = null;
      this.ws.close(1000);
      this.ws = null;
      this.stopMicCapture();
    }
    this.reconnectAttempts = 0;
    this._disconnected = false;
    await this._connect(conversationId);
  }

  private async _connect(conversationId?: string): Promise<void> {
    if (this._disconnected) return;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    const base = getApiBaseUrl();
    const url = new URL(base, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${url.origin}/ws/voice${conversationId ? `/${conversationId}` : ''}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
      this.ws = ws;
    } catch (err) {
      this.handlers.onError?.(`Failed to create voice WebSocket: ${err}`);
      return;
    }

    const connectTimeout = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) ws.close();
    }, 10_000);

    ws.onopen = () => {
      clearTimeout(connectTimeout);
      if (this._disconnected || this.ws !== ws) return;
      this.reconnectAttempts = 0;
      this._sessionReady = false;
      this.handlers.onConnected?.();

      // Mic capture is deferred until we receive session.updated from OpenAI
      // to avoid streaming audio before the server-backed session is configured.
      this._startKeepalive();
      this._resetSilenceTimer();
    };

    ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data as string);
        this._handleServerEvent(data);
      } catch {
        /* ignore non-JSON */
      }
    };

    ws.onclose = ev => {
      clearTimeout(connectTimeout);
      this._stopKeepalive();
      this._clearSilenceTimer();

      if (
        ev.code !== 1000 &&
        this.reconnectAttempts < this.maxReconnect &&
        !this._disconnected
      ) {
        this._lastDisconnectTime = Date.now();
        this.reconnectAttempts++;
        this.handlers.onReconnecting?.();
        const base = Math.min(1000 * 2 ** (this.reconnectAttempts - 1), 30_000);
        const jitter = Math.floor(Math.random() * 1000);
        this.reconnectTimer = setTimeout(() => {
          if (!this._disconnected) void this._connect(conversationId);
        }, base + jitter);
        return;
      }
      this.handlers.onDisconnected?.();
    };

    ws.onerror = () => {
      clearTimeout(connectTimeout);
      this.handlers.onError?.('Voice connection failed.');
    };
  }

  disconnect(): void {
    this._disconnected = true;
    this.reconnectAttempts = this.maxReconnect;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this._stopKeepalive();
    this._clearSilenceTimer();
    this._micPaused = false;
    this._userSpeaking = false;
    this._setAssistantSpeaking(false);
    this.stopMicCapture();
    this._stopPlayback();
    if (this.ws) {
      this.ws.onclose = null;
      if (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ) {
        this.ws.close(1000);
      }
    }
    this.ws = null;
    this.handlers.onDisconnected?.();
  }

  async startMicCapture(): Promise<void> {
    try {
      if (!this.audioContext) {
        this.audioContext = new AudioContext({ sampleRate: 24000 });
      }
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      this._mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 24000,
        },
      });

      const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
      const workletUrl = URL.createObjectURL(blob);
      await this.audioContext.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);

      this._sourceNode = this.audioContext.createMediaStreamSource(
        this._mediaStream
      );
      this.workletNode = new AudioWorkletNode(
        this.audioContext,
        'pcm-capture-processor'
      );

      this.workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          if (this.ws.bufferedAmount > BACKPRESSURE_THRESHOLD) return;
          const base64 = arrayBufferToBase64(event.data);
          this.ws.send(
            JSON.stringify({ type: 'input_audio_buffer.append', audio: base64 })
          );
        }
      };

      this._sourceNode.connect(this.workletNode);
      this.handlers.onListeningChange?.(true);
    } catch (err) {
      this.handlers.onError?.(`Microphone access failed: ${err}`);
    }
  }

  stopMicCapture(): void {
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this._sourceNode) {
      this._sourceNode.disconnect();
      this._sourceNode = null;
    }
    if (this._mediaStream) {
      this._mediaStream.getTracks().forEach(t => t.stop());
      this._mediaStream = null;
    }
    this._micPaused = false;
    this.handlers.onListeningChange?.(false);
  }

  pauseMicCapture(): void {
    if (this._micPaused) return;
    this._micPaused = true;
    if (this.workletNode) this.workletNode.disconnect();
    if (this._sourceNode) this._sourceNode.disconnect();
  }

  resumeMicCapture(): void {
    if (!this._micPaused) return;
    this._micPaused = false;

    if (this._sourceNode && this.workletNode) {
      this._sourceNode.connect(this.workletNode);
      this.workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          if (this.ws.bufferedAmount > BACKPRESSURE_THRESHOLD) return;
          const base64 = arrayBufferToBase64(event.data);
          this.ws.send(
            JSON.stringify({ type: 'input_audio_buffer.append', audio: base64 })
          );
        }
      };
      this._resetSilenceTimer();
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      void this.startMicCapture();
    }
    this._resetSilenceTimer();
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get micPaused(): boolean {
    return this._micPaused;
  }

  sendSessionUpdate(params: { voice?: string; instructions?: string }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const session: Record<string, string> = {};
    if (params.voice) session.voice = params.voice;
    if (params.instructions) session.instructions = params.instructions;
    if (Object.keys(session).length === 0) return;
    this.ws.send(JSON.stringify({ type: 'session.update', session }));
  }

  requestSpokenConfirmation(text: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(
      JSON.stringify({
        type: 'response.create',
        response: {
          modalities: ['text', 'audio'],
          instructions: `Say exactly this and nothing else: "${text}"`,
        },
      })
    );
  }

  interrupt(): void {
    this._stopPlayback();
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ type: 'response.cancel' }));
  }

  private _handleServerEvent(data: Record<string, unknown>): void {
    const type = data.type as string;

    switch (type) {
      case 'session.created':
      case 'session.updated':
        if (!this._sessionReady) {
          this._sessionReady = true;
          if (!this._micPaused) {
            void this.startMicCapture();
          }
        }
        break;

      case 'input_audio_buffer.speech_started':
        this._userSpeaking = true;
        this.handlers.onSpeakingChange?.(true);
        if (this._assistantSpeaking) {
          this.interrupt();
        }
        this._resetSilenceTimer();
        break;

      case 'input_audio_buffer.speech_stopped':
        this._userSpeaking = false;
        this.handlers.onSpeakingChange?.(false);
        this._resetSilenceTimer();
        break;

      case 'response.audio.delta':
        if (typeof data.delta === 'string') {
          this._setAssistantSpeaking(true);
          this._playbackQueue.push(data.delta);
          this._processPlaybackQueue();
        }
        break;

      case 'response.audio_transcript.delta':
        if (typeof data.delta === 'string') {
          this.handlers.onTranscript?.(data.delta, 'amin');
        }
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (typeof data.transcript === 'string') {
          this.handlers.onTranscript?.(data.transcript, 'user');
        }
        this._resetSilenceTimer();
        break;

      case 'response.done':
        this._setAssistantSpeaking(false);
        this._resetSilenceTimer();
        break;

      case 'amin.voice.standby':
        this.handlers.onStandbyRequested?.();
        break;

      case 'error':
        this.handlers.onError?.(
          typeof data.error === 'object' && data.error !== null
            ? ((data.error as { message?: string }).message ??
                'Unknown voice error')
            : String(data.error ?? 'Unknown voice error')
        );
        break;

      default:
        break;
    }
  }

  private _resetSilenceTimer(): void {
    this._clearSilenceTimer();
    this._silenceTimer = setTimeout(() => {
      if (this._userSpeaking) {
        this._resetSilenceTimer();
        return;
      }
      this.handlers.onAutoIdle?.();
    }, this._silenceTimeoutMs);
  }

  private _clearSilenceTimer(): void {
    if (this._silenceTimer) {
      clearTimeout(this._silenceTimer);
      this._silenceTimer = null;
    }
  }

  private _startKeepalive(): void {
    this._stopKeepalive();
    this.keepaliveTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'amin.ping' }));
      }
    }, 25_000);
  }

  private _stopKeepalive(): void {
    if (this.keepaliveTimer) {
      clearInterval(this.keepaliveTimer);
      this.keepaliveTimer = null;
    }
  }

  private async _processPlaybackQueue(): Promise<void> {
    if (this._isPlaying || this._playbackQueue.length === 0) return;
    this._isPlaying = true;

    try {
      if (!this.audioContext) {
        this.audioContext = new AudioContext({ sampleRate: 24000 });
      }

      while (this._playbackQueue.length > 0) {
        const base64 = this._playbackQueue.shift()!;
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const int16 = new Int16Array(bytes.buffer);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
          float32[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7fff);
        }

        const buffer = this.audioContext.createBuffer(1, float32.length, 24000);
        buffer.getChannelData(0).set(float32);

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.audioContext.destination);
        source.start();

        await new Promise<void>(resolve => {
          source.onended = () => resolve();
        });
      }
    } catch {
      /* playback error, non-critical */
    }

    this._isPlaying = false;
  }

  private _stopPlayback(): void {
    this._playbackQueue = [];
    this._isPlaying = false;
    this._setAssistantSpeaking(false);
  }

  private _setAssistantSpeaking(speaking: boolean): void {
    if (this._assistantSpeaking === speaking) return;
    this._assistantSpeaking = speaking;
    this.handlers.onAssistantSpeakingChange?.(speaking);
  }
}
