import yt_dlp
import sys
print("Preuzimanje uskoro pocinje...")

sampling_rate = "128" if len(sys.argv) < 2 else sys.argv[1]
if sampling_rate == "128":
    print("* Upozorenje: Odabran je podrazumijevana ucestanost odabiranja (128 kbps).")
    print("              Primjer odabira druge ucestanosti (kroz CMD): yt2mp3 64")
playlist = []
with open('input.txt', 'r') as f:
    for i in f.readlines():
        playlist.append(i.replace("\n", ""))
        
def get_video_title(url):
    # Kreiranje opcija za yt-dlp
    ydl_opts = {
        'quiet': True,
        'skip_download': True,  # Ne preuzimaj video
        'force_generic_extractor': True,  # Koristi generički ekstraktor
    }

    # Koristi yt-dlp za preuzimanje informacija o videu
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    return info.get('title', 'Nepoznat naziv')

item_names = {}
for i in playlist:
    item_names[i] = get_video_title(i)
     
            
for video_url in playlist:
    ydl_opts = {
        'format': 'bestaudio/best',
        'force_generic_extractor': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': f'{sampling_rate}',
        }],
        'outtmpl': f'{item_names[video_url]}.%(ext)s',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    
    