export interface VideoMetadata {
    id?: string;
    title: string;
    link: string;
    thumbnail: string;
    channel: string;
    duration: string;
}

export interface CognitiveGap {
    concept: string;
    reason: string;
    youtube_query: string;
    video?: VideoMetadata;
}

export interface AnalysisResponse {
    summary: string[];
    cognitive_gaps: CognitiveGap[];
    error?: string;
    details?: string;
    is_extensive?: boolean;
    pdf_notice?: string;
}

export const analyzeContent = async (text: string, file: File | null, youtubeUrl?: string): Promise<AnalysisResponse> => {
    const formData = new FormData();

    if (youtubeUrl) {
        formData.append('youtube_url', youtubeUrl);
    } else if (file) {
        formData.append('file', file);
    } else if (text) {
        formData.append('text', text);
    } else {
        throw new Error("Please provide text, a file, or a YouTube URL.");
    }

    const response = await fetch('http://127.0.0.1:5000/api/summarize', {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.details || 'Failed to analyze content');
    }

    return data;
};
