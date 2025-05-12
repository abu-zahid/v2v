// const BASE_URL = "http://localhost:8000";
const BASE_URL = "http://localhost:8000";

class AudioChat {
    constructor() {
        // Configuration elements
        this.baseUrlInput = document.getElementById('baseUrl');
        this.baseUrlInput.value = BASE_URL;
        this.recipientIdInput = document.getElementById('recipientId');
        this.accessTokenInput = document.getElementById('accessToken');

        // Control elements
        this.startButton = document.getElementById('startButton');
        this.stopButton = document.getElementById('stopButton');
        this.status = document.getElementById('status');
        this.speakerIndicator = document.getElementById('speakerIndicator');

        // Audio state
        this.ws = null;
        this.audioContext = null;
        this.mediaStreamSource = null;
        this.scriptProcessor = null;
        this.isRecording = false;
        this.audioQueue = [];
        this.isPlaying = false;
        this.nextPlayTime = 0;
        this.currentAudioSource = null;
        this.isInterrupted = false;

        // Audio configuration
        this.sampleRate = 44100;  // Match Dia's sample rate (44.1kHz)
        this.bufferSize = 4096;

        // Bind event listeners
        this.startButton.addEventListener('click', () => this.startConversation());
        this.stopButton.addEventListener('click', () => this.stopConversation());
    }

    updateStatus(message) {
        this.status.textContent = message;
    }

    updateSpeakerIndicator(speaker) {
        if (speaker === 'user') {
            this.speakerIndicator.textContent = '👤 You are speaking';
            this.speakerIndicator.className = 'speaker-indicator user-speaking';
        } else if (speaker === 'ai') {
            this.speakerIndicator.textContent = '🤖 AI is speaking';
            this.speakerIndicator.className = 'speaker-indicator ai-speaking';
        } else if (this.isRecording) {
            this.speakerIndicator.textContent = '👂 Ready for conversation';
            this.speakerIndicator.className = 'speaker-indicator';
        } else {
            this.speakerIndicator.textContent = '⚪ Not connected';
            this.speakerIndicator.className = 'speaker-indicator';
        }
    }

    async startConversation() {
        try {
            // Clear any previous status
            this.updateSpeakerIndicator(null);
            
            // Validate inputs
            if (!this.baseUrlInput.value.trim()) {
                this.updateStatus('Please fill in the Base URL field');
                return;
            }

            // Validate base URL format
            try {
                new URL(this.baseUrlInput.value);
            } catch (e) {
                this.updateStatus('Please enter a valid Base URL');
                return;
            }

            // Connect to WebSocket server
            const wsUrl = `${this.baseUrlInput.value.replace('http', 'ws')}/ai-voice-chat`;
            this.ws = new WebSocket(wsUrl);
            this.ws.binaryType = 'arraybuffer';
            
            this.ws.onopen = async () => {
                this.updateStatus('Connected');
                this.startButton.disabled = true;
                this.stopButton.disabled = false;
                await this.startRecording();
            };

            this.ws.onmessage = async (event) => {
                const data = JSON.parse(event.data);
                
                if (data.event === 'output_audio_buffer.append') {
                    try {
                        const decodedData = Uint8Array.from(atob(data.data), c => c.charCodeAt(0));
                        const audioBlob = new Blob([decodedData], { type: 'audio/wav' }); // Changed to WAV to match Dia's output
                        this.audioQueue.push(audioBlob);
                        
                        if (!this.isPlaying) {
                            this.isInterrupted = false;
                            await this.playNextChunk();
                        }
                    } catch (error) {
                        console.error('Error processing audio:', error);
                    }
                }
                else if (data.event === 'user.speech_started') {
                    this.interruptAudio();
                    this.updateSpeakerIndicator('user');
                }
                else if (data.event === 'user.speech_stopped') {
                    this.updateSpeakerIndicator(null);
                }
            };

            this.ws.onclose = () => {
                this.updateStatus('Disconnected');
                this.stopRecording();
                this.startButton.disabled = false;
                this.stopButton.disabled = true;
                this.updateSpeakerIndicator(null);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('Connection error');
                this.updateSpeakerIndicator(null);
            };

        } catch (error) {
            console.error('Error:', error);
            this.updateStatus('Failed to start conversation');
            this.updateSpeakerIndicator(null);
        }
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    channelCount: 1,
                    sampleRate: this.sampleRate
                } 
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            this.mediaStreamSource = this.audioContext.createMediaStreamSource(stream);
            this.scriptProcessor = this.audioContext.createScriptProcessor(
                this.bufferSize, 1, 1
            );

            this.mediaStreamSource.connect(this.scriptProcessor);
            this.scriptProcessor.connect(this.audioContext.destination);

            this.scriptProcessor.onaudioprocess = async (e) => {
                if (this.ws?.readyState === WebSocket.OPEN) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcm16 = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        const s = Math.max(-1, Math.min(1, inputData[i]));
                        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }
                    
                    await this.ws.send(JSON.stringify({
                        "event": "input_audio_buffer.append",
                        "data": btoa(String.fromCharCode.apply(null, new Uint8Array(pcm16.buffer)))
                    }));
                }
            };

            this.isRecording = true;
            this.updateStatus('Recording');
            this.updateSpeakerIndicator(null);

        } catch (error) {
            console.error('Error starting recording:', error);
            this.updateStatus('Failed to start recording');
        }
    }

    async stopConversation() {
        if (this.ws) {
            this.ws.close();
        }
        this.stopRecording();
    }

    stopRecording() {
        if (this.isRecording) {
            if (this.mediaStreamSource) {
                this.mediaStreamSource.disconnect();
            }
            if (this.scriptProcessor) {
                this.scriptProcessor.disconnect();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            
            this.isRecording = false;
            this.updateStatus('Stopped');
            this.updateSpeakerIndicator(null);
        }
    }

    async playNextChunk() {
        if (this.audioQueue.length === 0 || this.isPlaying) {
            return;
        }

        this.isPlaying = true;
        this.updateSpeakerIndicator('ai');
        const chunk = this.audioQueue.shift();
        
        try {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                this.nextPlayTime = this.audioContext.currentTime;
            }

            const arrayBuffer = await chunk.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            if (this.currentAudioSource) {
                this.currentAudioSource.stop();
                this.currentAudioSource.disconnect();
            }

            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            
            this.currentAudioSource = source;
            
            source.start(this.nextPlayTime);
            this.nextPlayTime += audioBuffer.duration;
            
            // Tell the server we're now in AI speaking mode
            if (this.ws?.readyState === WebSocket.OPEN) {
                await this.ws.send(JSON.stringify({
                    "event": "current_speaker.switch",
                    "data": "ai"
                }));
            }
            
            source.onended = async () => {
                this.isPlaying = false;
                this.currentAudioSource = null;
                
                if (this.audioQueue.length === 0) {
                    this.updateSpeakerIndicator(null);
                    
                    // Tell the server we're no longer in AI speaking mode
                    if (this.ws?.readyState === WebSocket.OPEN) {
                        await this.ws.send(JSON.stringify({
                            "event": "current_speaker.switch",
                            "data": "none"
                        }));
                    }
                }
                
                if (!this.isInterrupted) {
                    await this.playNextChunk();
                }
            };
        } catch (error) {
            console.error('Error playing audio:', error);
            this.isPlaying = false;
            this.currentAudioSource = null;
            this.updateSpeakerIndicator(null);
            if (!this.isInterrupted) {
                await this.playNextChunk();
            }
        }
    }

    interruptAudio() {
        this.isInterrupted = true;
        if (this.currentAudioSource) {
            this.currentAudioSource.stop();
            this.currentAudioSource.disconnect();
            this.currentAudioSource = null;
        }
        
        // Tell the server the user is speaking
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                "event": "current_speaker.switch",
                "data": "user"
            }));
        }
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    new AudioChat();
});