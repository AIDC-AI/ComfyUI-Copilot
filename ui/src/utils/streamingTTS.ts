/**
 * StreamingTTS — reads aloud AI responses in real-time as text streams in.
 *
 * Usage:
 *   const tts = new StreamingTTS({ onAllDone: () => console.log('done') });
 *   // In the SSE loop:
 *   tts.feed(response.text);          // full accumulated text each iteration
 *   // When response.finished:
 *   tts.flush();
 *   // To cancel:
 *   tts.stop();
 */

import { WorkflowChatAPI } from '../apis/workflowChatApi';

export interface StreamingTTSOptions {
  /** Called when all audio has finished playing after flush(). */
  onAllDone?: () => void;
  /** Called on the first TTS error (e.g., terms acceptance required). */
  onError?: (errorMessage: string) => void;
  /** Minimum characters before we consider sending a chunk (default 40). */
  minChunk?: number;
}

export class StreamingTTS {
  private claimedOffset = 0;
  private buffer = '';
  private playQueue: Blob[] = [];
  private isPlaying = false;
  private currentAudio: HTMLAudioElement | null = null;
  private stopped = false;
  private streamFinished = false;
  private pendingFetches = 0;
  private minChunk: number;
  private onAllDone?: () => void;
  private onError?: (errorMessage: string) => void;
  private errorFired = false;

  constructor(opts?: StreamingTTSOptions) {
    this.onAllDone = opts?.onAllDone;
    this.onError = opts?.onError;
    this.minChunk = opts?.minChunk ?? 40;
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /** Feed the full accumulated text from the SSE stream (called per SSE event). */
  feed(fullText: string | undefined | null) {
    if (this.stopped || !fullText) return;

    const newText = fullText.substring(this.claimedOffset);
    if (!newText) return;

    this.buffer += newText;
    this.claimedOffset = fullText.length;
    this.extractAndQueue();
  }

  /** Call when the stream is finished to flush any remaining buffer. */
  flush() {
    this.streamFinished = true;
    if (this.buffer.trim()) {
      this.sendChunk(this.buffer.trim());
      this.buffer = '';
    }
    this.checkAllDone();
  }

  /** Immediately stop all playback and discard queued audio. */
  stop() {
    this.stopped = true;
    if (this.currentAudio) {
      this.currentAudio.pause();
      try { URL.revokeObjectURL(this.currentAudio.src); } catch { /* ignore */ }
      this.currentAudio = null;
    }
    this.playQueue = [];
    this.isPlaying = false;
  }

  /** Whether the TTS has been stopped. */
  get isStopped() {
    return this.stopped;
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  /**
   * Scan the buffer for sentence boundaries and extract speakable chunks.
   * Sentence boundary = `.` `!` `?` or `\n` followed by whitespace or end of next char.
   */
  private extractAndQueue() {
    while (true) {
      let bestBreak = -1;

      for (let i = this.minChunk; i < this.buffer.length; i++) {
        const ch = this.buffer[i];
        if (ch === '.' || ch === '!' || ch === '?' || ch === '\n') {
          // Accept if next char is whitespace, newline, or we're near end of buffer
          const next = this.buffer[i + 1];
          if (!next || next === ' ' || next === '\n' || next === '\r') {
            bestBreak = i + 1;
            break;
          }
        }
      }

      if (bestBreak < 0) break; // no sentence boundary found yet

      const chunk = this.buffer.substring(0, bestBreak).trim();
      this.buffer = this.buffer.substring(bestBreak).trimStart();

      if (chunk) {
        this.sendChunk(chunk);
      }
    }
  }

  /** Send a text chunk to the TTS API and enqueue the resulting audio blob. */
  private async sendChunk(text: string) {
    if (this.stopped || !text) return;
    this.pendingFetches++;

    try {
      const blob = await WorkflowChatAPI.textToSpeech(text);
      if (this.stopped) return;
      this.playQueue.push(blob);
      this.playNext();
    } catch (err: any) {
      const msg = err?.message || String(err);
      console.error('[StreamingTTS] chunk error:', msg);
      // Fire onError once (e.g., for terms acceptance)
      if (!this.errorFired && this.onError) {
        this.errorFired = true;
        this.onError(msg);
      }
      // Stop further attempts on fatal errors like terms acceptance
      if (msg.includes('terms') || msg.includes('model_terms_required')) {
        this.stop();
      }
    } finally {
      this.pendingFetches--;
      this.checkAllDone();
    }
  }

  /** Play the next blob in the queue. */
  private playNext() {
    if (this.isPlaying || this.stopped || this.playQueue.length === 0) return;

    const blob = this.playQueue.shift()!;
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    this.currentAudio = audio;
    this.isPlaying = true;

    const done = () => {
      try { URL.revokeObjectURL(url); } catch { /* ignore */ }
      this.currentAudio = null;
      this.isPlaying = false;
      this.playNext();
      this.checkAllDone();
    };

    audio.onended = done;
    audio.onerror = done;
    audio.play().catch(done);
  }

  /** Check if everything is truly done (stream finished + all audio played). */
  private checkAllDone() {
    if (
      this.streamFinished &&
      !this.isPlaying &&
      this.playQueue.length === 0 &&
      this.pendingFetches === 0 &&
      !this.buffer.trim()
    ) {
      this.onAllDone?.();
    }
  }
}
