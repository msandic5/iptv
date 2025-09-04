import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import END, Listbox, PhotoImage, Scrollbar, filedialog, messagebox, ttk

import requests
import vlc

os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")


def check_stream_vlc(url, options=None):
    try:
        instance = vlc.Instance()
        player = instance.media_player_new()
        if options:
            media = instance.media_new(url, *options)
        else:
            media = instance.media_new(url)
        player.set_media(media)
        player.play()
        time.sleep(5)
        state = player.get_state()
        player.stop()
        return state in [vlc.State.Playing, vlc.State.Paused]
    except Exception as e:
        return False


def check_stream_ffmpeg(url, options=None):
    try:
        headers = []
        if options:
            for opt in options:
                if opt.startswith(":http-user-agent="):
                    headers.append(f"User-Agent: {opt.split('=', 1)[1]}")
                elif opt.startswith(":http-referrer="):
                    headers.append(f"Referer: {opt.split('=', 1)[1]}")
        header_str = "\\r\\n".join(headers) if headers else ""
        ffmpeg_cmd = ["ffmpeg", "-i", url, "-t", "5", "-f", "null", "-"]
        if header_str:
            ffmpeg_cmd = [
                "ffmpeg",
                "-headers",
                header_str,
                "-i",
                url,
                "-t",
                "5",
                "-f",
                "null",
                "-",
            ]
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return result.returncode == 0  # samo kod 0 znači da radi
    except Exception as e:
        return False


channels = []
selected_channels = []


def load_channels():
    url = entry_url.get().strip()
    if not url:
        messagebox.showinfo("Info", "Unesi URL do M3U liste!")
        return
    try:
        response = requests.get(url)
        response.encoding = "utf-8"
        lines = response.text.splitlines()
    except Exception as e:
        messagebox.showerror("Greška", f"Ne mogu učitati listu!\n{e}")
        return

    channels.clear()
    listbox_left.delete(0, END)
    block_lines = []
    vlc_options = []
    channel_name = ""
    for line in lines:
        if line.startswith("#EXTINF"):
            block_lines = [line]
            vlc_options = []
            channel_name = line.split(",", 1)[-1].strip()
        elif line.startswith("#EXTVLCOPT:"):
            block_lines.append(line)
            opt = ":" + line.strip().split(":", 1)[1]
            vlc_options.append(opt)
        elif line.startswith("http"):
            block_lines.append(line)
            url = line.strip()
            channels.append(
                {
                    "name": channel_name,
                    "url": url,
                    "options": vlc_options.copy(),
                    "block": block_lines.copy(),
                }
            )
            listbox_left.insert(END, channel_name)
            block_lines = []
            vlc_options = []
            channel_name = ""
        else:
            block_lines.append(line)


# Globalna varijabla za zaustavljanje testiranja
stop_testing = False


def test_selected_thread():
    global stop_testing
    selected = listbox_left.curselection()
    if not selected:
        messagebox.showinfo("Info", "Odaberi barem jedan kanal!")
        return
    results = []
    progress_bar["maximum"] = len(selected)
    progress_var.set(0)
    root.update_idletasks()
    stop_testing = False
    for i, idx in enumerate(selected):
        if stop_testing:
            break
        ch = channels[idx]
        if radio_var.get() == "vlc":
            result = check_stream_vlc(ch["url"], ch["options"])
        else:
            result = check_stream_ffmpeg(ch["url"], ch["options"])
        status = "✅ Radi" if result else "❌ Ne radi"
        results.append(f"{ch['name']}: {status}")
        color = "green" if result else "red"
        listbox_left.itemconfig(idx, {"bg": color, "fg": "white"})
        progress_var.set(i + 1)
        root.update_idletasks()
    progress_var.set(0)
    root.update_idletasks()
    if stop_testing:
        messagebox.showinfo("Info", "Testiranje je zaustavljeno!")
    else:
        messagebox.showinfo("Rezultat", "\n".join(results))


def test_selected():
    # Pokreni testiranje u posebnoj niti
    threading.Thread(target=test_selected_thread, daemon=True).start()


def stop_test():
    global stop_testing
    stop_testing = True


def add_selected():
    selected = listbox_left.curselection()
    if not selected:
        messagebox.showinfo("Info", "Odaberi barem jedan kanal za dodavanje!")
        return
    for idx in selected:
        ch = channels[idx]
        # Provjeri da li je već dodan
        if ch not in selected_channels:
            selected_channels.append(ch)
            listbox_right.insert(END, ch["name"])


def add_tested():
    # Dodaj sve zelene (testirane i rade) iz lijeve liste u desnu listu
    for idx in range(listbox_left.size()):
        # Provjeri boju pozadine
        item_bg = listbox_left.itemcget(idx, "bg")
        if item_bg == "green":
            ch = channels[idx]
            if ch not in selected_channels:
                selected_channels.append(ch)
                listbox_right.insert(END, ch["name"])


def save_playlist():
    if not selected_channels:
        messagebox.showinfo("Info", "Nema kanala za spremanje!")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".m3u",
        filetypes=[("M3U Playlist", "*.m3u"), ("All Files", "*.*")],
        title="Sačuvaj playlistu",
    )
    if not file_path:
        return
    with open(file_path, "w", encoding="utf-8") as f:
        for ch in selected_channels:
            for line in ch["block"]:
                f.write(line if line.endswith("\n") else line + "\n")
    messagebox.showinfo("Info", f"Playlista je sačuvana na:\n{file_path}")


root = tk.Tk()
root.title("IPTV Stream Tester")

# Top frame za URL i LOAD
frame_top = tk.Frame(root)
frame_top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

entry_url = tk.Entry(frame_top, width=70)
entry_url.pack(side=tk.LEFT, padx=(0, 10))
entry_url.insert(
    0,
    "UNESI OVDJE URL DO M3U LISTE",
)


def clear_entry_on_click(event):
    if entry_url.get() == "UNESI OVDJE URL DO M3U LISTE":
        entry_url.delete(0, END)


entry_url.bind("<Button-1>", clear_entry_on_click)

btn_load = tk.Button(frame_top, text="LOAD", command=load_channels, width=10)
btn_load.pack(side=tk.LEFT)

# ProgressBar ispod URL EditBox-a
progress_frame = tk.Frame(root)
progress_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
progress_bar.pack(fill=tk.X, expand=True)

# Frame za radio button s labelom
frame_radio = tk.LabelFrame(root, text="Metod testiranja", padx=10, pady=5)
frame_radio.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

radio_var = tk.StringVar(value="vlc")
radio_vlc = tk.Radiobutton(
    frame_radio, text="python-vlc", variable=radio_var, value="vlc"
)
radio_ffmpeg = tk.Radiobutton(
    frame_radio, text="ffmpeg", variable=radio_var, value="ffmpeg"
)
radio_vlc.pack(side=tk.LEFT, padx=5)
radio_ffmpeg.pack(side=tk.LEFT, padx=5)

frame_main = tk.Frame(root)
frame_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

frame_left = tk.Frame(frame_main)
frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

frame_right = tk.Frame(frame_main)
frame_right.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0))

scrollbar_left = Scrollbar(frame_left)
scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)

listbox_left = Listbox(
    frame_left,
    selectmode=tk.EXTENDED,
    yscrollcommand=scrollbar_left.set,
    width=40,
    exportselection=0,
)
listbox_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_left.config(command=listbox_left.yview)

frame_buttons = tk.Frame(frame_right)
frame_buttons.pack(side=tk.TOP, fill=tk.X)

btn_test = tk.Button(
    frame_buttons, text="TEST", command=test_selected, width=15, height=2
)
btn_test.pack(side=tk.LEFT, padx=(0, 5), pady=(0, 10))

btn_stop = tk.Button(frame_buttons, text="STOP", command=stop_test, width=7, height=2)
btn_stop.pack(side=tk.LEFT, padx=(0, 10), pady=(0, 10))

btn_add = tk.Button(
    frame_buttons, text="DODAJ", command=add_selected, width=20, height=2
)
btn_add.pack(pady=(0, 10))

btn_add_tested = tk.Button(
    frame_buttons, text="DODAJ TESTIRANE", command=add_tested, width=20, height=2
)
btn_add_tested.pack(pady=(0, 10))

btn_save = tk.Button(
    frame_buttons, text="SACUVAJ", command=save_playlist, width=20, height=2
)
btn_save.pack(pady=(0, 10))

frame_right_list = tk.Frame(frame_right)
frame_right_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(10, 0))

scrollbar_right = Scrollbar(frame_right_list)
scrollbar_right.pack(side=tk.RIGHT, fill=tk.Y)

listbox_right = Listbox(
    frame_right_list,
    selectmode=tk.EXTENDED,
    yscrollcommand=scrollbar_right.set,
    width=40,
    exportselection=0,
)
listbox_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_right.config(command=listbox_right.yview)

root.mainloop()
