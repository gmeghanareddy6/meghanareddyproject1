import os
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, WhisperProcessor, WhisperForConditionalGeneration
from keybert import KeyBERT
import torchaudio

class LocalMLPipeline:
    def __init__(self):
        print("Initializing Local ML Pipeline... This may take a moment to load models.")
        
        # Determine the best device (CPU or GPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading models on: {self.device.upper()}")

        # 1. Summarization Model (DistilBART)
        # We use a smaller BART model suitable for 8-16GB RAM laptops
        self.summarizer_model_id = "sshleifer/distilbart-cnn-12-6"
        print(f"Loading Summarizer: {self.summarizer_model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.summarizer_model_id)
        self.summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(self.summarizer_model_id).to(self.device)

        # 2. Transcription Model (Whisper Tiny) for fast local processing
        self.whisper_model_id = "openai/whisper-tiny"
        print(f"Loading Whisper: {self.whisper_model_id}")
        self.whisper_processor = WhisperProcessor.from_pretrained(self.whisper_model_id)
        self.whisper_model = WhisperForConditionalGeneration.from_pretrained(self.whisper_model_id).to(self.device)

        # 3. Keyword Extraction (KeyBERT)
        # Using a small embedding model for fast local keyword generation
        print("Loading KeyBERT (all-MiniLM-L6-v2)")
        self.kw_model = KeyBERT(model="all-MiniLM-L6-v2")

        print("Local ML Pipeline Initialization Complete!")

    def summarize_text(self, text, max_length=150, min_length=50):
        """
        Summarizes the provided text using DistilBART.
        Supports dynamic chunking for text longer than 3500 chars to produce proportional summaries.
        """
        try:
            if len(text) > 3500:
                # Split into chunks of around 3000 characters respecting paragraphs
                paragraphs = text.split('\n')
                chunks = []
                current_chunk = ""
                for p in paragraphs:
                    if len(current_chunk) + len(p) < 3000:
                        current_chunk += p + "\n"
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = p + "\n"
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                if len(chunks) <= 1:
                    chunks = [text[i:i+3000] for i in range(0, min(len(text), 15000), 3000)]
                
                summaries = []
                # Summarize up to 6 chunks for deep coverage
                for chunk in chunks[:6]:
                    inputs = self.tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True).to(self.device)
                    summary_ids = self.summarizer_model.generate(
                        inputs["input_ids"],
                        max_length=max_length,
                        min_length=min_length,
                        no_repeat_ngram_size=3,
                        early_stopping=True
                    )
                    summaries.append(self.tokenizer.decode(summary_ids[0], skip_special_tokens=True))
                
                return " ".join(summaries)
            else:
                inputs = self.tokenizer(text, return_tensors="pt", max_length=1024, truncation=True).to(self.device)
                summary_ids = self.summarizer_model.generate(
                    inputs["input_ids"],
                    max_length=max_length,
                    min_length=min_length,
                    no_repeat_ngram_size=3,
                    early_stopping=True
                )
                return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        except Exception as e:
            print(f"Summarization Error: {e}")
            return "Failed to generate summary locally."

    def extract_keywords(self, text, top_n=5):
        """
        Extracts key educational topics/keywords using KeyBERT.
        """
        try:
            # Extract keywords with diversity (Max Sum Similarity)
            keywords = self.kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 3), stop_words='english', 
                                                      use_maxsum=True, nr_candidates=20, top_n=top_n)
            
            # Format nicely
            results = []
            for kw, score in keywords:
                results.append({
                    "concept": kw.title(),
                    "reason": f"Extracted automatically (Confidence: {score:.2f})",
                    "youtube_query": f"{kw} educational tutorial"
                })
            return results
        except Exception as e:
            print(f"Keyword Extraction Error: {e}")
            return []

    def transcribe_audio(self, audio_path):
        """
        Transcribes a local audio file using Whisper.
        """
        try:
            # Load audio using torchaudio
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Whisper expects 16kHz audio. Resample if necessary.
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
                waveform = resampler(waveform)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                
            input_features = self.whisper_processor(waveform.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_features.to(self.device)
            
            # Generate token ids
            predicted_ids = self.whisper_model.generate(input_features)
            
            # Decode token ids to text
            transcription = self.whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            return transcription.strip()
            
        except Exception as e:
            print(f"Transcription Error: {e}")
            return None

# Singleton instance for the Flask app to use
ml_pipe = None

def get_pipeline():
    global ml_pipe
    if ml_pipe is None:
        ml_pipe = LocalMLPipeline()
    return ml_pipe

if __name__ == "__main__":
    # Test script directly
    pipe = get_pipeline()
    test_text = "Machine learning (ML) is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without explicit instructions. Recently, generative artificial neural networks have surpassed many previous approaches in performance."
    
    print("\n--- TEST SUMMARIZATION ---")
    print(pipe.summarize_text(test_text))
    
    print("\n--- TEST KEYWORDS ---")
    print(pipe.extract_keywords(test_text))
