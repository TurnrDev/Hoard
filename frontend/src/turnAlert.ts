type AudioContextWindow = Window & {
  webkitAudioContext?: typeof AudioContext;
};

export function alertCurrentTurn(): void {
  try {
    navigator.vibrate?.([140, 70, 140]);
  } catch {
    // Vibration is optional; continue to the audio cue regardless.
  }

  const AudioContextClass =
    window.AudioContext ?? (window as AudioContextWindow).webkitAudioContext;
  if (!AudioContextClass) {
    return;
  }

  try {
    const audioContext = new AudioContextClass();
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    const startTime = audioContext.currentTime;

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(660, startTime);
    gain.gain.setValueAtTime(0.0001, startTime);
    gain.gain.exponentialRampToValueAtTime(0.12, startTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.16);
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start(startTime);
    oscillator.stop(startTime + 0.17);
    oscillator.addEventListener("ended", () => {
      void audioContext.close();
    });
    void audioContext.resume().catch(() => audioContext.close());
  } catch {
    // Browser media policies can reject unsolicited sound; the rail still highlights.
  }
}
