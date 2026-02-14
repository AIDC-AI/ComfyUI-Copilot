/**
 * VADRecorder — Voice Activity Detection recorder that auto-stops on silence.
 *
 * Uses Web Audio API AnalyserNode to monitor volume levels. When RMS drops
 * below the threshold for `silenceMs` milliseconds, recording automatically
 * stops and the `onSilenceStop` callback fires with the audio Blob.
 *
 * Usage:
 *   const vad = new VADRecorder({
 *     silenceMs: 1500,
 *     onSilenceStop: (blob) => { ... },
 *     onVolumeChange: (rms) => { ... },  // optional: for visual feedback
 *   });
 *   await vad.start();
 *   // ... user speaks, auto-stops on silence
 *   // or manually: vad.stop()
 */

export interface VADRecorderOptions {
  /** Silence duration (ms) before auto-stop. Default 1500. */
  silenceMs?: number;
  /** RMS threshold below which we consider silence. Default 0.015. */
  silenceThreshold?: number;
  /** Called when recording auto-stops due to silence. */
  onSilenceStop?: (audioBlob: Blob) => void;
  /** Called each animation frame with the current RMS level (0-1). */
  onVolumeChange?: (rms: number) => void;
  /** Called when recording starts successfully. */
  onStart?: () => void;
  /** Called on error (e.g., mic denied). */
  onError?: (err: Error) => void;
}

export class VADRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private stream: MediaStream | null = null;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private chunks: Blob[] = [];
  private animFrameId: number | null = null;
  private active = false;
  private manualStop = false;

  private silenceMs: number;
  private silenceThreshold: number;
  private onSilenceStop?: (blob: Blob) => void;
  private onVolumeChange?: (rms: number) => void;
  private onStart?: () => void;
  private onError?: (err: Error) => void;

  constructor(opts?: VADRecorderOptions) {
    this.silenceMs = opts?.silenceMs ?? 1500;
    this.silenceThreshold = opts?.silenceThreshold ?? 0.015;
    this.onSilenceStop = opts?.onSilenceStop;
    this.onVolumeChange = opts?.onVolumeChange;
    this.onStart = opts?.onStart;
    this.onError = opts?.onError;
  }

  get isActive() {
    return this.active;
  }

  async start() {
    if (this.active) return;
    this.manualStop = false;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioContext = new AudioContext();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      source.connect(this.analyser);

      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: 'audio/webm' });
      this.chunks = [];

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.chunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: 'audio/webm' });
        this.cleanup();
        if (!this.manualStop && blob.size > 0) {
          this.onSilenceStop?.(blob);
        }
      };

      this.mediaRecorder.start();
      this.active = true;
      this.onStart?.();
      this.monitorVolume();
    } catch (err) {
      this.cleanup();
      this.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  /** Manually stop recording. Does NOT trigger onSilenceStop — returns the blob directly. */
  async stop(): Promise<Blob | null> {
    if (!this.active) return null;
    this.manualStop = true;

    return new Promise<Blob | null>((resolve) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        const blob = this.chunks.length > 0 ? new Blob(this.chunks, { type: 'audio/webm' }) : null;
        this.cleanup();
        resolve(blob);
        return;
      }

      this.mediaRecorder.onstop = () => {
        const blob = this.chunks.length > 0 ? new Blob(this.chunks, { type: 'audio/webm' }) : null;
        this.cleanup();
        resolve(blob);
      };

      this.mediaRecorder.stop();
    });
  }

  // ---------------------------------------------------------------------------
  // Volume monitoring with VAD
  // ---------------------------------------------------------------------------

  private monitorVolume() {
    if (!this.analyser) return;

    const data = new Float32Array(this.analyser.frequencyBinCount);

    const check = () => {
      if (!this.analyser || !this.active) return;

      this.analyser.getFloatTimeDomainData(data);

      // Compute RMS
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
      const rms = Math.sqrt(sum / data.length);

      this.onVolumeChange?.(rms);

      if (rms < this.silenceThreshold) {
        // Silence detected — start timer if not already running
        if (!this.silenceTimer) {
          this.silenceTimer = setTimeout(() => {
            // Auto-stop after sustained silence
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
              this.active = false;
              this.mediaRecorder.stop();
            }
          }, this.silenceMs);
        }
      } else {
        // Voice detected — reset timer
        if (this.silenceTimer) {
          clearTimeout(this.silenceTimer);
          this.silenceTimer = null;
        }
      }

      if (this.active) {
        this.animFrameId = requestAnimationFrame(check);
      }
    };

    this.animFrameId = requestAnimationFrame(check);
  }

  // ---------------------------------------------------------------------------
  // Cleanup
  // ---------------------------------------------------------------------------

  private cleanup() {
    this.active = false;
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    this.analyser = null;
    this.mediaRecorder = null;
  }
}
