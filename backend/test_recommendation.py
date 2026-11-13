
from youtubesearchpython import VideosSearch

TRUSTED_CHANNELS = [
    "Neso Academy", "Abdul Bari", "Jenny's Lectures CS IT", "freeCodeCamp.org", "CS Dojo",
    "Traversy Media", "Fireship", "Programming with Mosh", "Khan Academy", "mitocw",
    "StatQuest with Josh Starmer", "3Blue1Brown", "The Coding Train", "Sentdex", "Corey Schafer",
    "Tech With Tim", "Web Dev Simplified", "Amigoscode", "Kevin Powell", "Net Ninja", "Academind",
    "Harvard University", "Stanford Online", "CrashCourse", "Kurzgesagt – In a Nutshell",
    "Veritasium", "Vsauce", "Computerphile", "Numberphile"
]

def get_youtube_video(query):
    print(f"Searching for: {query}")
    try:
        videos_search = VideosSearch(query, limit=5)
        results = videos_search.result()
        
        best_video = None
        highest_score = -1

        if results['result']:
            for video in results['result']:
                score = 0
                channel_name = video['channel']['name']
                title = video['title'].lower()
                duration = video.get('duration')

                # 1. Preferred Channel Bonus
                if any(trusted.lower() in channel_name.lower() for trusted in TRUSTED_CHANNELS):
                    score += 10
                
                # 2. Educational Keywords Bonus
                if any(keyword in title for keyword in ["tutorial", "course", "lecture", "explained", "crash course", "introduction", "learn"]):
                    score += 5
                
                # 3. Duration Check
                if duration:
                    parts = duration.split(':')
                    if len(parts) >= 2:
                        try:
                            minutes = int(parts[-2])
                            if len(parts) == 3:
                                minutes += int(parts[-3]) * 60
                            
                            if minutes >= 3 and minutes <= 60:
                                score += 3
                            elif minutes < 2:
                                score -= 5
                        except:
                            pass
                
                print(f"Scored Video '{video['title']}' ({channel_name}) [{duration}]: {score}")

                if score > highest_score:
                    highest_score = score
                    best_video = video
            
            if best_video:
                print(f"WINNER: {best_video['title']} by {best_video['channel']['name']}")
                return best_video

    except Exception as e:
        print(f"Error: {e}")

# Test Cases
get_youtube_video("Backpropagation neural networks tutorial")
get_youtube_video("History of Rome Crash Course")
get_youtube_video("Python for beginners")
