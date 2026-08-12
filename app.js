"use strict";

// ---------- DOM ----------
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const resetBtn = document.getElementById("resetBtn");
const downloadBtn = document.getElementById("downloadBtn");
const timerEl = document.getElementById("timer");
const liveNoteEl = document.getElementById("liveNote");
const liveFreqEl = document.getElementById("liveFreq");
const meterFill = document.getElementById("meterFill");
const statusEl = document.getElementById("status");
const noteCountEl = document.getElementById("noteCount");
const canvas = document.getElementById("pianoRoll");
const ctx = canvas.getContext("2d");
const playbackPanel = document.getElementById("playbackPanel");
const playbackAudio = document.getElementById("playbackAudio");
const silenceThresholdInput = document.getElementById("silenceThreshold");
const minDurationInput = document.getElementById("minDuration");
const minFreqInput = document.getElementById("minFreq");
const maxFreqInput = document.getElementById("maxFreq");
const noteStabilityInput = document.getElementById("noteStability");

// ---------- Constants ----------
const ANALYSIS_BUFFER_SIZE = 2048;
const CONFIDENCE_THRESHOLD = 0.85;
const TICKS_PER_QUARTER = 480;
const MICROSECONDS_PER_QUARTER = 500000; // 120 BPM
const TICKS_PER_SECOND = TICKS_PER_QUARTER / (MICROSECONDS_PER_QUARTER / 1e6);
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const SILENCE_HOLD_MS = 130; // brief gaps that don't end a note
const PITCH_MEDIAN_WINDOW = 5; // frames of median smoothing applied to the raw pitch estimate
const NOTE_DEAD_ZONE_SEMITONES = 0.55; // pitch can wander this far from the held note without triggering a change

// ---------- State ----------
let audioContext = null;
let mediaStream = null;
let sourceNode = null;
let processorNode = null;
let mediaRecorder = null;
let recordedChunks = [];

let isRecording = false;
let recordStartTime = 0;
let timerHandle = null;

let noteEvents = []; // finalized notes: {note, start, end, velocity}
let currentNote = null; // in-progress note: {note, start, lastVoiced, velocitySamples}
let candidateNote = null;
let candidateStart = null;
let pitchHistory = []; // recent raw MIDI pitch estimates, for median smoothing

// ---------- Helpers ----------
function freqToMidi(freq) {
  return 69 + 12 * Math.log2(freq / 440);
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function midiToNoteName(midi) {
  const rounded = Math.round(midi);
  const name = NOTE_NAMES[((rounded % 12) + 12) % 12];
  const octave = Math.floor(rounded / 12) - 1;
  return `${name}${octave}`;
}

function formatTimer(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toFixed(1).padStart(4, "0");
  return `${m}:${s}`;
}

function rmsToVelocity(rms) {
  // rough log mapping of rms (~0.005 - 0.3) to MIDI velocity 1-127
  const db = 20 * Math.log10(Math.max(rms, 1e-6));
  const normalized = Math.min(1, Math.max(0, (db + 45) / 40));
  return Math.max(1, Math.min(127, Math.round(normalized * 126) + 1));
}

// ---------- Pitch detection (bounded autocorrelation) ----------
function detectPitch(buf, sampleRate, minFreq, maxFreq, silenceThreshold) {
  const size = buf.length;
  let sumSquares = 0;
  for (let i = 0; i < size; i++) sumSquares += buf[i] * buf[i];
  const rms = Math.sqrt(sumSquares / size);

  if (rms < silenceThreshold) {
    return { frequency: -1, rms };
  }

  const minLag = Math.max(2, Math.floor(sampleRate / maxFreq));
  const maxLag = Math.min(size - 2, Math.ceil(sampleRate / minFreq));
  if (minLag >= maxLag) return { frequency: -1, rms };

  let bestLag = -1;
  let bestCorr = -Infinity;
  const corr = new Float32Array(maxLag + 2);

  for (let lag = minLag; lag <= maxLag; lag++) {
    let sum = 0;
    const limit = size - lag;
    for (let i = 0; i < limit; i++) {
      sum += buf[i] * buf[i + lag];
    }
    corr[lag] = sum;
    if (sum > bestCorr) {
      bestCorr = sum;
      bestLag = lag;
    }
  }

  if (bestLag <= minLag || bestLag >= maxLag) {
    return { frequency: -1, rms };
  }

  // parabolic interpolation for sub-sample precision
  const x1 = corr[bestLag - 1];
  const x2 = corr[bestLag];
  const x3 = corr[bestLag + 1];
  const a = (x1 + x3 - 2 * x2) / 2;
  const b = (x3 - x1) / 2;
  let trueLag = bestLag;
  if (a !== 0) trueLag = bestLag - b / (2 * a);
  if (trueLag <= 0) return { frequency: -1, rms };

  // normalized confidence to reject noisy/non-periodic signal
  let energy = 0;
  const limit = size - bestLag;
  for (let i = 0; i < limit; i++) {
    energy += buf[i] * buf[i] + buf[i + bestLag] * buf[i + bestLag];
  }
  const confidence = energy > 0 ? (2 * bestCorr) / energy : 0;
  if (confidence < CONFIDENCE_THRESHOLD) return { frequency: -1, rms };

  return { frequency: sampleRate / trueLag, rms, confidence };
}

// ---------- Note segmentation ----------
// Raw pitch estimates are noisy from frame to frame (vibrato, breath, octave slips).
// To avoid chopping a sung note into many spurious fragments we: (1) median-smooth the
// pitch over a short rolling window, (2) keep a dead zone around the currently held note
// so small wobbles don't count as a change, and (3) require a pitch drift outside that
// dead zone to persist for a configurable duration before actually switching notes.
function processFrame(freq, rms, nowSeconds) {
  const silenceThreshold = parseFloat(silenceThresholdInput.value);
  const voiced = freq > 0 && rms >= silenceThreshold;

  if (!voiced) {
    liveNoteEl.textContent = "—";
    liveFreqEl.textContent = "— Hz";
    pitchHistory.length = 0;
    candidateNote = null;
    candidateStart = null;
    if (currentNote && (nowSeconds - currentNote.lastVoiced) * 1000 > SILENCE_HOLD_MS) {
      finalizeCurrentNote(currentNote.lastVoiced);
    }
    return;
  }

  pitchHistory.push(freqToMidi(freq));
  if (pitchHistory.length > PITCH_MEDIAN_WINDOW) pitchHistory.shift();
  const smoothedMidi = median(pitchHistory);
  const roundedNote = Math.round(smoothedMidi);

  liveNoteEl.textContent = midiToNoteName(roundedNote);
  liveFreqEl.textContent = `${freq.toFixed(1)} Hz`;

  if (!currentNote) {
    currentNote = { note: roundedNote, start: nowSeconds, lastVoiced: nowSeconds, velocitySamples: [rms] };
    candidateNote = null;
    candidateStart = null;
    return;
  }

  currentNote.lastVoiced = nowSeconds;

  const deviation = Math.abs(smoothedMidi - currentNote.note);
  if (deviation < NOTE_DEAD_ZONE_SEMITONES) {
    currentNote.velocitySamples.push(rms);
    candidateNote = null;
    candidateStart = null;
    return;
  }

  // pitch has drifted outside the held note's dead zone - require it to hold steady
  // for noteStability ms before treating it as a genuine note change
  if (candidateNote !== roundedNote) {
    candidateNote = roundedNote;
    candidateStart = nowSeconds;
  }

  const stabilityMs = parseFloat(noteStabilityInput.value);
  if ((nowSeconds - candidateStart) * 1000 >= stabilityMs) {
    // backdate the transition to when the pitch actually started drifting, rather than
    // the later moment it was confirmed, so note timing isn't skewed by the debounce delay
    finalizeCurrentNote(candidateStart);
    currentNote = { note: roundedNote, start: candidateStart, lastVoiced: nowSeconds, velocitySamples: [rms] };
    candidateNote = null;
    candidateStart = null;
  }
}

function finalizeCurrentNote(endSeconds) {
  if (!currentNote) return;
  const minDurationSeconds = parseFloat(minDurationInput.value) / 1000;
  const duration = endSeconds - currentNote.start;
  if (duration >= minDurationSeconds) {
    const avgRms = currentNote.velocitySamples.reduce((a, b) => a + b, 0) / currentNote.velocitySamples.length;
    noteEvents.push({
      note: currentNote.note,
      start: currentNote.start,
      end: endSeconds,
      velocity: rmsToVelocity(avgRms),
    });
    drawPianoRoll();
    updateNoteCount();
  }
  currentNote = null;
}

// ---------- Recording ----------
async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        channelCount: 1,
      },
    });
  } catch (err) {
    statusEl.textContent = `Impossible d'accéder au microphone : ${err.message}`;
    return;
  }

  resetState();

  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  sourceNode = audioContext.createMediaStreamSource(mediaStream);
  processorNode = audioContext.createScriptProcessor(ANALYSIS_BUFFER_SIZE, 1, 1);

  processorNode.onaudioprocess = (event) => {
    const input = event.inputBuffer.getChannelData(0);
    const buf = new Float32Array(input); // copy, buffer is reused internally
    const minFreq = parseFloat(minFreqInput.value);
    const maxFreq = parseFloat(maxFreqInput.value);
    const silenceThreshold = parseFloat(silenceThresholdInput.value);
    const result = detectPitch(buf, audioContext.sampleRate, minFreq, maxFreq, silenceThreshold);
    const nowSeconds = audioContext.currentTime - recordStartTime;

    meterFill.style.width = `${Math.min(100, (result.rms / 0.2) * 100)}%`;
    processFrame(result.frequency, result.rms, nowSeconds);
  };

  sourceNode.connect(processorNode);
  processorNode.connect(createSilentSink(audioContext));

  recordStartTime = audioContext.currentTime;
  isRecording = true;

  // parallel MediaRecorder for audio playback reference
  recordedChunks = [];
  try {
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };
    mediaRecorder.start();
  } catch (err) {
    mediaRecorder = null; // playback reference is optional
  }

  recordBtn.classList.add("recording");
  recordBtn.disabled = true;
  stopBtn.disabled = false;
  resetBtn.disabled = true;
  downloadBtn.disabled = true;
  playbackPanel.hidden = true;
  statusEl.textContent = "Enregistrement en cours… chantez, sifflez ou fredonnez.";

  timerHandle = setInterval(() => {
    timerEl.textContent = formatTimer(audioContext.currentTime - recordStartTime);
  }, 100);
}

// ScriptProcessorNode requires a connected destination to fire in some browsers;
// route through a muted gain node instead of the real output to avoid feedback/echo.
function createSilentSink(ctx) {
  const gain = ctx.createGain();
  gain.gain.value = 0;
  gain.connect(ctx.destination);
  return gain;
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  const endSeconds = audioContext.currentTime - recordStartTime;
  finalizeCurrentNote(endSeconds);

  clearInterval(timerHandle);
  timerEl.textContent = formatTimer(endSeconds);

  processorNode.disconnect();
  sourceNode.disconnect();
  mediaStream.getTracks().forEach((t) => t.stop());
  audioContext.close();

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.addEventListener(
      "stop",
      () => {
        if (recordedChunks.length) {
          const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
          playbackAudio.src = URL.createObjectURL(blob);
          playbackPanel.hidden = false;
        }
      },
      { once: true }
    );
    mediaRecorder.stop();
  }

  recordBtn.classList.remove("recording");
  recordBtn.disabled = false;
  stopBtn.disabled = true;
  resetBtn.disabled = false;
  downloadBtn.disabled = noteEvents.length === 0;
  liveNoteEl.textContent = "—";
  liveFreqEl.textContent = "— Hz";
  meterFill.style.width = "0%";

  statusEl.textContent = noteEvents.length
    ? `Terminé : ${noteEvents.length} note(s) détectée(s). Vous pouvez télécharger le MIDI.`
    : "Aucune note claire n'a été détectée. Essayez de chanter plus fort ou plus près du micro.";
}

function resetState() {
  noteEvents = [];
  currentNote = null;
  candidateNote = null;
  candidateStart = null;
  pitchHistory = [];
  updateNoteCount();
  drawPianoRoll();
  playbackPanel.hidden = true;
  playbackAudio.removeAttribute("src");
  downloadBtn.disabled = true;
  timerEl.textContent = "00:00.0";
}

// ---------- Piano roll ----------
function drawPianoRoll() {
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#10131a";
  ctx.fillRect(0, 0, w, h);

  if (noteEvents.length === 0 && !currentNote) {
    return;
  }

  const allNotes = noteEvents.map((n) => n.note).concat(currentNote ? [currentNote.note] : []);
  let minNote = Math.min(...allNotes) - 2;
  let maxNote = Math.max(...allNotes) + 2;
  if (maxNote - minNote < 12) {
    const mid = (maxNote + minNote) / 2;
    minNote = Math.floor(mid - 6);
    maxNote = Math.ceil(mid + 6);
  }
  const noteRange = maxNote - minNote;
  const rowHeight = h / noteRange;

  const maxTime = Math.max(
    1,
    ...noteEvents.map((n) => n.end),
    currentNote ? currentNote.lastVoiced - currentNote.start + (audioContext ? audioContext.currentTime - recordStartTime - currentNote.start : 0) : 0
  );
  const pxPerSecond = Math.max(40, w / Math.max(maxTime, 4));

  // horizontal guide lines per octave (C notes)
  ctx.strokeStyle = "#20242f";
  ctx.lineWidth = 1;
  for (let n = Math.ceil(minNote); n <= maxNote; n++) {
    if (n % 12 === 0) {
      const y = h - (n - minNote) * rowHeight;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
      ctx.fillStyle = "#4a5062";
      ctx.font = "10px monospace";
      ctx.fillText(midiToNoteName(n), 4, y - 2);
    }
  }

  function drawNoteRect(note, start, end, active) {
    const x = start * pxPerSecond;
    const width = Math.max(2, (end - start) * pxPerSecond);
    const y = h - (note - minNote) * rowHeight - rowHeight;
    ctx.fillStyle = active ? "#ff9f6b" : "#7aa2ff";
    ctx.strokeStyle = "#0f1115";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, y, width, rowHeight - 2, 3) : ctx.rect(x, y, width, rowHeight - 2);
    ctx.fill();
    ctx.stroke();
  }

  for (const n of noteEvents) drawNoteRect(n.note, n.start, n.end, false);
  if (currentNote && audioContext) {
    const now = audioContext.currentTime - recordStartTime;
    drawNoteRect(currentNote.note, currentNote.start, now, true);
  }

  // resize canvas width to fit content if recording ran long
  const neededWidth = Math.ceil(maxTime * pxPerSecond) + 40;
  if (neededWidth > canvas.width) {
    canvas.width = neededWidth;
  }
}

function updateNoteCount() {
  noteCountEl.textContent = `${noteEvents.length} note${noteEvents.length === 1 ? "" : "s"}`;
}

// ---------- MIDI file generation ----------
function writeVariableLengthQuantity(value) {
  let buffer = value & 0x7f;
  const bytes = [];
  while ((value >>= 7) > 0) {
    buffer <<= 8;
    buffer |= (value & 0x7f) | 0x80;
  }
  while (true) {
    bytes.push(buffer & 0xff);
    if (buffer & 0x80) buffer >>= 8;
    else break;
  }
  return bytes;
}

function buildMidiFile(notes) {
  const trackEvents = [];

  // tempo meta event (120 BPM)
  trackEvents.push({ tick: 0, bytes: [0xff, 0x51, 0x03, 0x07, 0xa1, 0x20] });

  for (const n of notes) {
    const startTick = Math.round(n.start * TICKS_PER_SECOND);
    const endTick = Math.max(startTick + 1, Math.round(n.end * TICKS_PER_SECOND));
    trackEvents.push({ tick: startTick, priority: 1, bytes: [0x90, n.note, n.velocity] });
    trackEvents.push({ tick: endTick, priority: 0, bytes: [0x80, n.note, 0] });
  }

  // sort by tick; at equal tick, note-offs (priority 0) before note-ons (priority 1)
  trackEvents.sort((a, b) => a.tick - b.tick || (a.priority || 0) - (b.priority || 0));

  const data = [];
  let prevTick = 0;
  for (const ev of trackEvents) {
    const delta = Math.max(0, ev.tick - prevTick);
    data.push(...writeVariableLengthQuantity(delta));
    data.push(...ev.bytes);
    prevTick = ev.tick;
  }
  data.push(...writeVariableLengthQuantity(0), 0xff, 0x2f, 0x00); // end of track

  const header = [
    0x4d, 0x54, 0x68, 0x64, // "MThd"
    0x00, 0x00, 0x00, 0x06, // header length
    0x00, 0x00, // format 0
    0x00, 0x01, // 1 track
    (TICKS_PER_QUARTER >> 8) & 0xff, TICKS_PER_QUARTER & 0xff,
  ];

  const trackLength = data.length;
  const trackHeader = [
    0x4d, 0x54, 0x72, 0x6b, // "MTrk"
    (trackLength >>> 24) & 0xff,
    (trackLength >>> 16) & 0xff,
    (trackLength >>> 8) & 0xff,
    trackLength & 0xff,
  ];

  return new Uint8Array([...header, ...trackHeader, ...data]);
}

function downloadMidi() {
  if (noteEvents.length === 0) return;
  const bytes = buildMidiFile(noteEvents);
  const blob = new Blob([bytes], { type: "audio/midi" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = url;
  a.download = `voix-vers-midi-${timestamp}.mid`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------- Wiring ----------
recordBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
resetBtn.addEventListener("click", resetState);
downloadBtn.addEventListener("click", downloadMidi);

if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
  statusEl.textContent = "Votre navigateur ne supporte pas l'accès au microphone (getUserMedia).";
  recordBtn.disabled = true;
}

drawPianoRoll();
