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
        return result.returncode == 0  # only returncode 0 means success
    except Exception as e:
        return False


channels = []
selected_channels = []


def load_channels():
    url = entry_url.get().strip()
    if not url:
        messagebox.showinfo("Info", "Enter M3U playlist URL here!")
        return
    try:
        response = requests.get(url)
        response.encoding = "utf-8"
        lines = response.text.splitlines()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot load playlist!\n{e}")
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


# Global variable to stop testing
stop_testing = False


def test_selected_thread():
    global stop_testing
    selected = listbox_left.curselection()
    if not selected:
        messagebox.showinfo("Info", "Odaberi barem jedan kanal!")
        return
    num_ok = 0
    num_fail = 0
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
        color = "green" if result else "red"
        listbox_left.itemconfig(idx, {"bg": color, "fg": "white"})
        if result:
            num_ok += 1
        else:
            num_fail += 1
        progress_var.set(i + 1)
        root.update_idletasks()
    progress_var.set(0)
    root.update_idletasks()
    if stop_testing:
        messagebox.showinfo("Info", "Testing stopped!")
    else:
        messagebox.showinfo(
            "Result",
            f"Channels: {len(selected)}\nWorking: {num_ok}\nNot Working: {num_fail}",
        )


def test_selected():
    # Start testing in a separate thread
    threading.Thread(target=test_selected_thread, daemon=True).start()


def stop_test():
    global stop_testing
    stop_testing = True


def add_selected():
    selected = listbox_left.curselection()
    if not selected:
        messagebox.showinfo("Info", "Select at least one channel to add!")
        return
    for idx in selected:
        ch = channels[idx]
        # Check if already added
        if ch not in selected_channels:
            selected_channels.append(ch)
            listbox_right.insert(END, ch["name"])


def add_tested():
    # add all channels marked as green
    for idx in range(listbox_left.size()):
        # Check background color
        item_bg = listbox_left.itemcget(idx, "bg")
        if item_bg == "green":
            ch = channels[idx]
            if ch not in selected_channels:
                selected_channels.append(ch)
                listbox_right.insert(END, ch["name"])


def save_playlist():
    if not selected_channels:
        messagebox.showinfo("Info", "No channels to save!")
        return
    file_path = filedialog.asksaveasfilename(
        defaultextension=".m3u",
        filetypes=[("M3U Playlist", "*.m3u"), ("All Files", "*.*")],
        title="Save Playlist",
    )
    if not file_path:
        return
    with open(file_path, "w", encoding="utf-8") as f:
        for ch in selected_channels:
            for line in ch["block"]:
                f.write(line if line.endswith("\n") else line + "\n")
    messagebox.showinfo("Info", f"Playlist saved to:\n{file_path}")


root = tk.Tk()
root.title("IPTV M3U Checker")
style = ttk.Style(root)
style.theme_use("vista")  # or "clam", "alt", "default", "xpnative"

# Top frame for URL and LOAD
frame_top = ttk.Frame(root)
frame_top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

entry_url = ttk.Entry(frame_top, width=70)
entry_url.pack(side=tk.LEFT, padx=(0, 10))
entry_url.insert(
    0,
    "Enter M3U playlist URL here",
)


def clear_entry_on_click(event):
    if entry_url.get() == "Enter M3U playlist URL here":
        entry_url.delete(0, END)


def load_from_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("M3U Playlist", "*.m3u"), ("All Files", "*.*")],
        title="Open M3U Playlist",
    )
    if file_path:
        entry_url.delete(0, END)
        entry_url.insert(0, file_path)
        # Load channels from file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load playlist!\n{e}")
            return

        channels.clear()
        listbox_left.delete(0, END)
        block_lines = []
        vlc_options = []
        channel_name = ""
        for line in lines:
            line = line.rstrip("\n")
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


def move_up_right():
    selected = listbox_right.curselection()
    if not selected or selected[0] == 0:
        return
    for idx in selected:
        if idx == 0:
            continue
        # Swap in listbox
        name_selected = listbox_right.get(idx)
        name_above = listbox_right.get(idx - 1)
        listbox_right.delete(idx - 1)
        listbox_right.insert(idx - 1, name_selected)
        listbox_right.delete(idx)
        listbox_right.insert(idx, name_above)
        # Swap in selected_channels
        selected_channels[idx - 1], selected_channels[idx] = (
            selected_channels[idx],
            selected_channels[idx - 1],
        )
    # Select moved items
    listbox_right.selection_clear(0, END)
    for idx in [i - 1 for i in selected if i > 0]:
        listbox_right.selection_set(idx)


def move_down_right():
    selected = listbox_right.curselection()
    if not selected or selected[-1] == listbox_right.size() - 1:
        return
    for idx in reversed(selected):
        if idx == listbox_right.size() - 1:
            continue
        # Swap in listbox
        name_selected = listbox_right.get(idx)
        name_below = listbox_right.get(idx + 1)
        listbox_right.delete(idx)
        listbox_right.insert(idx, name_below)
        listbox_right.delete(idx + 1)
        listbox_right.insert(idx + 1, name_selected)
        # Swap in selected_channels
        selected_channels[idx], selected_channels[idx + 1] = (
            selected_channels[idx + 1],
            selected_channels[idx],
        )
    # Select moved items
    listbox_right.selection_clear(0, END)
    for idx in [i + 1 for i in selected if i < listbox_right.size() - 1]:
        listbox_right.selection_set(idx)


entry_url.bind("<Button-1>", clear_entry_on_click)

btn_load_url = ttk.Button(
    frame_top, text="Load from URL", command=load_channels, width=15
)
btn_load_url.pack(side=tk.LEFT)

btn_load_file = ttk.Button(
    frame_top, text="Load from File", command=load_from_file, width=15
)
btn_load_file.pack(side=tk.LEFT, padx=(10, 0))

# ProgressBar below top frame
progress_frame = ttk.Frame(root)
progress_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
progress_bar.pack(fill=tk.X, expand=True)

# Frame for radio buttons
frame_radio = ttk.LabelFrame(root, text="Testing Method", padding=(10, 5))
frame_radio.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

radio_var = tk.StringVar(value="vlc")
radio_vlc = ttk.Radiobutton(
    frame_radio, text="python-vlc", variable=radio_var, value="vlc"
)
radio_ffmpeg = ttk.Radiobutton(
    frame_radio, text="ffmpeg", variable=radio_var, value="ffmpeg"
)
radio_vlc.pack(side=tk.LEFT, padx=5)
radio_ffmpeg.pack(side=tk.LEFT, padx=5)

frame_main = ttk.Frame(root)
frame_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

frame_left = ttk.Frame(frame_main)
frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

frame_right = ttk.Frame(frame_main)
frame_right.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0))

frame_right_list = ttk.Frame(frame_right)
frame_right_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(10, 0))

scrollbar_right = ttk.Scrollbar(frame_right_list)
scrollbar_right.pack(side=tk.RIGHT, fill=tk.Y)

listbox_right = Listbox(
    frame_right_list,
    selectmode=tk.EXTENDED,
    yscrollcommand=scrollbar_right.set,
    width=50,  # povećaj širinu
    height=25,  # postavi visinu
    exportselection=0,
)
listbox_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_right.config(command=listbox_right.yview)

scrollbar_left = ttk.Scrollbar(frame_left)
scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)

listbox_left = Listbox(
    frame_left,
    selectmode=tk.EXTENDED,
    yscrollcommand=scrollbar_left.set,
    width=50,  # povećaj širinu
    height=25,  # postavi visinu
    exportselection=0,
)
listbox_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_left.config(command=listbox_left.yview)

# --- Testing LabelFrame ---
frame_testing = ttk.LabelFrame(frame_right, text="Testing", padding=(10, 5))
frame_testing.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

btn_test = ttk.Button(frame_testing, text="TEST", command=test_selected, width=15)
btn_test.pack(side=tk.LEFT, padx=(0, 5), pady=(0, 10))

btn_stop = ttk.Button(frame_testing, text="STOP", command=stop_test, width=7)
btn_stop.pack(side=tk.LEFT, padx=(0, 10), pady=(0, 10))

# --- Move LabelFrame ---
frame_move = ttk.LabelFrame(frame_right, text="Move", padding=(10, 5))
frame_move.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

btn_up = ttk.Button(frame_move, text="↑", command=move_up_right, width=5)
btn_up.pack(pady=(0, 5))

btn_down = ttk.Button(frame_move, text="↓", command=move_down_right, width=5)
btn_down.pack(pady=(0, 10))

# --- Creation LabelFrame ---
frame_creation = ttk.LabelFrame(frame_right, text="Creation", padding=(10, 5))
frame_creation.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

btn_add = ttk.Button(
    frame_creation, text="Add Selected", command=add_selected, width=20
)
btn_add.pack(pady=(0, 10))

btn_add_tested = ttk.Button(
    frame_creation, text="Add Tested", command=add_tested, width=20
)
btn_add_tested.pack(pady=(0, 10))

btn_save = ttk.Button(frame_creation, text="SAVE", command=save_playlist, width=20)
btn_save.pack(pady=(0, 10))


def clear_left_list():
    listbox_left.delete(0, END)
    channels.clear()


def clear_right_list():
    listbox_right.delete(0, END)
    selected_channels.clear()


def remove_selected_right():
    selected = listbox_right.curselection()
    # Remove from end to start to avoid index shifting
    for idx in reversed(selected):
        listbox_right.delete(idx)
        del selected_channels[idx]


def add_selected_left():
    add_selected()


def on_left_double_click(event):
    idx = listbox_left.curselection()
    if idx:
        add_selected()


def on_right_double_click(event):
    idx = listbox_right.curselection()
    if idx:
        remove_selected_right()


def show_left_menu(event):
    # Select item under cursor for context menu actions
    try:
        index = listbox_left.nearest(event.y)
        listbox_left.selection_clear(0, END)
        listbox_left.selection_set(index)
    except Exception:
        pass
    left_menu.tk_popup(event.x_root, event.y_root)


def show_right_menu(event):
    # Select item under cursor for context menu actions
    try:
        index = listbox_right.nearest(event.y)
        listbox_right.selection_clear(0, END)
        listbox_right.selection_set(index)
    except Exception:
        pass
    right_menu.tk_popup(event.x_root, event.y_root)


# Create context menu for left list
left_menu = tk.Menu(root, tearoff=0)
left_menu.add_command(label="Add", command=add_selected_left)
left_menu.add_command(label="Clear", command=clear_left_list)

# Create context menu for right list
right_menu = tk.Menu(root, tearoff=0)
right_menu.add_command(label="Remove", command=remove_selected_right)
right_menu.add_command(label="Clear", command=clear_right_list)

# Bind right-click and double-click events
listbox_left.bind("<Button-3>", show_left_menu)
listbox_right.bind("<Button-3>", show_right_menu)
listbox_left.bind("<Double-Button-1>", on_left_double_click)
listbox_right.bind("<Double-Button-1>", on_right_double_click)


root.mainloop()
