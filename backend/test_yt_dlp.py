
import yt_dlp

TRUSTED_CHANNELS = [
    "Neso Academy", "Abdul Bari", "Jenny's Lectures CS IT", "freeCodeCamp.org", "CS Dojo",
    "Traversy Media", "Fireship", "Programming with Mosh", "Khan Academy", "mitocw",
    "StatQuest with Josh Starmer", "3Blue1Brown", "The Coding Train", "Sentdex", "Corey Schafer",
    "Tech With Tim", "Web Dev Simplified", "Amigoscode", "Kevin Powell", "Net Ninja", "Academind",
    "Harvard University", "Stanford Online", "CrashCourse", "Kurzgesagt – In a Nutshell",
    "Veritasium", "Vsauce", "Computerphile", "Numberphile"
]

def search_yt_dlp(query):
    print(f"Searching via yt-dlp: {query}")
    ydl_opts = {
        'default_search': 'ytsearch5',
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                for video in info['entries']:
                    title = video.get('title')
                    channel = video.get('uploader', 'Unknown')
                    duration = video.get('duration') # in seconds
                    view_count = video.get('view_count')
                    
                    print(f"Found: {title} by {channel} ({duration}s)")
                    
                    # Logic to score would go here
        except Exception as e:
            print(f"Error: {e}")

search_yt_dlp("Backpropagation neural networks tutorial")
