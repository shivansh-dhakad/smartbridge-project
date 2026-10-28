
import React, { useEffect, useRef, useState } from "react";

const TARGET_RATE = 16000;

function resample(input, sourceRate, targetRate) {
  if (sourceRate === targetRate) return input;

  const outputLength = Math.floor(
    input.length * targetRate / sourceRate
  );
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const position = i * sourceRate / targetRate;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const fraction = position - left;

    output[i] =
      input[left] * (1 - fraction) + input[right] * fraction;
  }

  return output;
}

function toPCM16(samples) {
  const pcm = new Int16Array(samples.length);

  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    pcm[i] = sample < 0
      ? sample * 32768
      : sample * 32767;
  }

  return pcm;
}

export default function AudioCapture({ active, onMetrics }) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState("");

  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);

  useEffect(() => {
    if (!active) {
      stopCapture();
      return;
    }

    let cancelled = false;

    async function startCapture() {
      try {
        setError("");

        const stream =
          await navigator.mediaDevices.getUserMedia({
            audio: {
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true
            }
          });

        if (cancelled) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }

        streamRef.current = stream;

        const context = new AudioContext();
        audioContextRef.current = context;
        await context.resume();

        const ws = new WebSocket(
          "ws://localhost:8000/ws/audio"
        );

        ws.binaryType = "arraybuffer";
        wsRef.current = ws;

        ws.onmessage = event => {
          try {
            const data = JSON.parse(event.data);

            if (data.event === "audio_metrics") {
              onMetrics?.(data);
            }
          } catch (err) {
            console.error("Invalid audio metrics:", err);
          }
        };

        ws.onerror = () => {
          setError("Unable to connect to the audio server.");
        };

        ws.onclose = () => setIsRecording(false);

        await new Promise((resolve, reject) => {
          ws.onopen = resolve;
          ws.onerror = () =>
            reject(new Error("WebSocket connection failed"));
        });

        if (cancelled) {
          ws.close();
          return;
        }

        const source = context.createMediaStreamSource(stream);
        const processor = context.createScriptProcessor(
          4096, 1, 1
        );

        sourceRef.current = source;
        processorRef.current = processor;

        processor.onaudioprocess = event => {
          if (ws.readyState !== WebSocket.OPEN) return;

          const input = event.inputBuffer.getChannelData(0);
          const normalized = resample(
            input,
            context.sampleRate,
            TARGET_RATE
          );

          const pcm = toPCM16(normalized);
          ws.send(pcm.buffer);
        };

        source.connect(processor);

        // Keep the processing node active without audible microphone
        // feedback. The output is intentionally silent.
        const silentGain = context.createGain();
        silentGain.gain.value = 0;

        processor.connect(silentGain);
        silentGain.connect(context.destination);

        setIsRecording(true);
      } catch (err) {
        setError(err.message || "Microphone capture failed.");
        stopCapture();
      }
    }

    startCapture();

    return () => {
      cancelled = true;
      stopCapture();
    };
  }, [active]);

  function stopCapture() {
    if (processorRef.current) {
      processorRef.current.onaudioprocess = null;
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    sourceRef.current?.disconnect();
    sourceRef.current = null;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsRecording(false);
  }

  return (
    <div>
      <p>
        Audio status: {isRecording ? "Recording" : "Stopped"}
      </p>

      {error && <p role="alert">{error}</p>}
    </div>
  );
}
