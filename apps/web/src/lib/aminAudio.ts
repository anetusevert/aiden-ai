let audioContext: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let sourceNode: MediaElementAudioSourceNode | null = null;
let connectedElement: HTMLAudioElement | null = null;

function getOrCreateContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  return audioContext;
}

export function connectAminAudioSource(
  audioElement: HTMLAudioElement
): AnalyserNode {
  const ctx = getOrCreateContext();

  if (connectedElement === audioElement && analyser) {
    return analyser;
  }

  disconnectAminAudio();

  analyser = ctx.createAnalyser();
  analyser.fftSize = 64;
  analyser.smoothingTimeConstant = 0.8;

  sourceNode = ctx.createMediaElementSource(audioElement);
  sourceNode.connect(analyser);
  analyser.connect(ctx.destination);
  connectedElement = audioElement;

  return analyser;
}

export function getAminAnalyser(): AnalyserNode | null {
  return analyser;
}

export function disconnectAminAudio(): void {
  if (sourceNode) {
    try {
      sourceNode.disconnect();
    } catch {
      /* already disconnected */
    }
    sourceNode = null;
  }
  if (analyser) {
    try {
      analyser.disconnect();
    } catch {
      /* already disconnected */
    }
    analyser = null;
  }
  connectedElement = null;
}
