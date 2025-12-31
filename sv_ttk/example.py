import tkinter as tk, sys
from tkinter import ttk, messagebox as msg, filedialog as fd

try: import __init__ as sv_ttk
except: import sv_ttk

window = tk.Tk()
window.title("Sun Valley Demo")
window.minsize(width = 799, height = 456)
sv_ttk.set_theme("light")

icon = tk.PhotoImage(data = "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")
window.iconphoto(True, icon)

checked = tk.BooleanVar(value = True)
unchecked = tk.BooleanVar(value = False)
disabled = tk.BooleanVar(value = False)
radio = tk.StringVar(value = "1")
radio_enabled = tk.StringVar(value = "1")
option = tk.StringVar(value = "Python")
progress = tk.IntVar(value = 0)
menubar = tk.StringVar(value = "none")
disable_widgets = tk.BooleanVar(value = False)

test_menu = tk.Menu()
for i in range(5):
    test_menu.add_command(label = f"Option {str(i + 1)}")

fruits = ["Apple", "Banana", "Orange", "Strawberry", "Pear"]
vegetables = ["Tomato", "Potato", "Cabbage", "Onion", "Garlic"]
programming_langs = ["Python", "Java", "C++", "C#", "Javascript"]

menu = tk.Menu()
menu.add_cascade(label = "File", menu = test_menu)
menu.add_cascade(label = "Edit", menu = test_menu)
menu.add_cascade(label = "View", menu = test_menu)
menu.add_cascade(label = "Help", menu = test_menu)

# Custom menu bar
menu_bar = ttk.Frame(window)
menu_bar_frame = ttk.Frame(menu_bar, padding = (4, 0, 4, 4))
menu_bar_frame.pack(fill = "x")

if not sys.platform == "win32": menu_bar_frame.configure(padding = 4)

ttk.Separator(menu_bar, orient = "horizontal").pack(fill = "x")
ttk.Menubutton(menu_bar_frame, text = "File", menu = test_menu, style = "Toolbutton", padding = (8, 1, 8, 1)).pack(side = "left")
ttk.Menubutton(menu_bar_frame, text = "Edit", menu = test_menu, style = "Toolbutton", padding = (8, 1, 8, 1)).pack(side = "left")
ttk.Menubutton(menu_bar_frame, text = "View", menu = test_menu, style = "Toolbutton", padding = (8, 1, 8, 1)).pack(side = "left")
ttk.Menubutton(menu_bar_frame, text = "Help", menu = test_menu, style = "Toolbutton", padding = (8, 1, 8, 1)).pack(side = "left")

title = ttk.Label(window, text = "Sun Valley Theme Demo", font = ("Segoe UI Semibold", 20))
title.pack(padx = 16, pady = (8, 0), side = "top", anchor = "w")

notebook = ttk.Notebook(window)
notebook.pack(pady = 16, padx = 16, fill = "both", expand = True, side = "bottom")

frame = ttk.Frame(notebook, padding = 16)
frame.pack(fill = "both", expand = True)

options = ttk.Frame(notebook, padding = 16)
options.pack(fill = "x")

scrollbar_example = ttk.Frame(notebook, width = 751)
scrollbar_example.pack(fill = "x")

color_constants = ttk.Frame(notebook, padding = 16)
color_constants.pack(fill = "x")

notebook.add(text = "Widgets", child = frame)
notebook.add(text = "Scrollbar", child = scrollbar_example)
notebook.add(text = "Color constants", child = color_constants)
notebook.add(text = "Options", child = options)

try: sv_ttk.bg
except: notebook.forget(2)

frame1 = ttk.Frame(frame)

main = ttk.Frame(frame1)
main.pack(side = "left")

row1 = ttk.Frame(main)
row1.pack()


checkboxes = ttk.Labelframe(row1, text = "Checkbuttons", padding = 4)
checkboxes.pack(side = "left", fill = "y")

ttk.Checkbutton(checkboxes, text = "Checked", variable = checked, width = 15).pack(anchor = "w", padx = 4, pady = (8, 4))
ttk.Checkbutton(checkboxes, text = "Unhecked", variable = unchecked, width = 15).pack(anchor = "w", padx = 4, pady = 4)
ttk.Checkbutton(checkboxes, text = "Disabled", variable = disabled, state = "disabled", width = 15).pack(anchor = "w", padx = 4, pady = 4)


buttons = ttk.Labelframe(row1, text = "Buttons", padding = 4)
buttons.pack(side = "left", padx = (16, 0))

ttk.Button(buttons, text = "Button", width = 27).pack(anchor = "w", padx = 8, pady = 4)
ttk.Button(buttons, text = "Accent Button", width = 27, style = "Accent.TButton").pack(anchor = "w", padx = 8, pady = 4)
ttk.Button(buttons, text = "Toolbutton", width = 27, style = "Toolbutton").pack(anchor = "w", padx = 8, pady = 4)


row2 = ttk.Frame(main)
row2.pack(pady = (16, 0))


radiobuttons = ttk.Labelframe(row2, text = "Radiobuttons", padding = 4)
radiobuttons.pack(side = "left", fill = "y")

ttk.Radiobutton(radiobuttons, text = "Selected", width = 15, variable = radio, value = "1").pack(anchor = "w", padx = 4, pady = (8, 4))
ttk.Radiobutton(radiobuttons, text = "Unselected", width = 15, variable = radio, value = "2").pack(anchor = "w", padx = 4, pady = 4)
ttk.Radiobutton(radiobuttons, text = "Disabled", width = 15, state = "disabled").pack(anchor = "w", padx = 4, pady = 4)


input = ttk.Labelframe(row2, text = "Input", padding = 4)
input.pack(side = "left", padx = (16, 0))

entry = ttk.Entry(input)
entry.pack(padx = 8, pady = 4, fill = "x")
entry.insert(0, "Type here...")

combo = ttk.Combobox(input, values = fruits)
combo.pack(padx = 8, pady = 4, fill = "x")
combo.insert(0, "Apple")

spinbox = ttk.Spinbox(input, from_ = 0, to = 100)
spinbox.pack(padx = 8, pady = 4, fill = "x")
spinbox.insert(0, 40)


other = ttk.LabelFrame(frame1, text = "Other widgets", padding = 4)
other.pack(side = "left", padx = (16, 0))

ttk.Menubutton(other, menu = test_menu, text = "Menubutton", width = 25).pack(padx = 8, pady = 4)
ttk.OptionMenu(other, option, programming_langs[0], *programming_langs).pack(padx = 8, pady = 4, fill = "x")

readonlycombo = ttk.Combobox(other, state = "readonly", values = vegetables)
readonlycombo.pack(padx = 8, pady = 4, fill = "x")
readonlycombo.current(0)

ttk.Separator(other, orient = "horizontal").pack(padx = 4, pady = 8, fill = "x")

scale = ttk.Scale(other, orient = "horizontal", from_ = 0, to = 100, command = lambda e: progress.set(scale.get()))
scale.pack(padx = 8, pady = 4, fill = "x")

progressbar = ttk.Progressbar(other, maximum = 100, orient = "horizontal", variable = progress)
progressbar.pack(padx = 8, pady = 4, fill = "x")

ttk.Separator(other, orient = "horizontal").pack(padx = 4, pady = 8, fill = "x")

ttk.Checkbutton(other, text = "Switch", style = "Switch.TCheckbutton").pack(padx = 8, pady = 6, fill = "x")
ttk.Checkbutton(other, text = "Toggle Button", style = "Toggle.TButton").pack(padx = 8, pady = 4, fill = "x")


text = tk.Text(scrollbar_example, padx = 10, pady = 10, height = 5, wrap = "word", bd = 0, highlightthickness = 0, font = ("Segoe UI", 10))
text.pack(side = "left", fill = "both", expand = True)
text.insert("1.0", '''Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed laoreet eu libero at imperdiet. Curabitur a pretium lorem. Pellentesque sed augue ultricies, vestibulum nunc eget, gravida mauris. Vivamus venenatis arcu non fringilla laoreet. Duis vulputate id odio sit amet sodales. In velit nunc, vulputate quis sollicitudin sit amet, fermentum eget purus. Etiam sed felis ut nisi pulvinar ultricies sed id risus. Vestibulum mauris libero, consectetur quis lobortis ut, maximus ac ante. Donec molestie sit amet lorem ut porta. In odio ante, faucibus non elit eget, vehicula scelerisque mi. Proin aliquam neque nunc, quis rutrum erat ultricies euismod. Suspendisse lectus lacus, fringilla sit amet mollis quis, maximus vitae orci. Duis sodales eros nec sagittis molestie. Donec tristique pharetra ex, nec dictum est sodales vel. Proin maximus mattis sapien, id viverra nulla auctor sed.

Donec ante nulla, dignissim id bibendum eget, rutrum nec erat. Suspendisse sodales arcu quis erat consequat tincidunt. Nunc nisl massa, maximus vehicula nulla sed, interdum molestie justo. Suspendisse convallis sem ac massa auctor pulvinar. Nulla turpis ex, tempor sit amet imperdiet eu, commodo at elit. Nullam eu auctor tortor, in vehicula velit. Aenean eu mi pharetra turpis semper pellentesque. Mauris mollis eget sapien quis rhoncus. Vivamus neque mauris, porttitor scelerisque neque eu, faucibus placerat mauris. In cursus sagittis dapibus. Praesent lacinia, arcu a suscipit laoreet, quam turpis consequat ipsum, nec aliquet ipsum orci eget lacus. Quisque justo odio, scelerisque tincidunt est ac, tempor ultricies erat.

Etiam consequat, eros nec maximus vulputate, tellus urna feugiat purus, ut scelerisque enim felis nec nulla. Morbi viverra, magna quis interdum dapibus, urna lacus sollicitudin nulla, ac mattis ante dolor eu ligula. Vivamus nec laoreet lorem, ut lacinia lorem. Donec accumsan ligula felis, et tincidunt lorem pharetra in. Sed et facilisis ipsum. Vivamus et magna elementum, hendrerit felis in, dapibus purus. Nullam eleifend mattis ex, ac sagittis enim finibus nec. Praesent ut mauris lobortis, semper urna ultrices, imperdiet ligula. Pellentesque a diam rutrum mi venenatis dapibus. Curabitur eu tempus lacus. Phasellus convallis diam at fermentum sagittis.

Aliquam erat volutpat. Maecenas eros eros, ultrices sit amet luctus vitae, lobortis id augue. Donec pulvinar ante sem, sed condimentum justo condimentum et. Pellentesque congue lectus lectus, at vehicula est feugiat vel. Proin cursus mi eget ultrices rutrum. Morbi in sodales mauris. Suspendisse convallis, lacus vitae dignissim mollis, nisi ligula egestas tellus, eu consectetur ligula lorem vitae purus. Aliquam iaculis massa vel ligula porttitor fermentum. Mauris imperdiet sed mauris vel semper. Cras eu ex justo. Mauris eu sollicitudin elit, vel maximus dolor.

Sed a ex dictum, sagittis nulla ac, varius lacus. Maecenas sed commodo nunc. Ut eu convallis neque, et fringilla tellus. Nam facilisis nisl a lacus molestie rhoncus. Vestibulum eu turpis viverra, tempus tellus quis, imperdiet lectus. Aenean posuere lacus et aliquam accumsan. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec tortor diam, volutpat id consequat sit amet, vestibulum quis tellus. Vivamus pellentesque commodo rutrum. Nulla varius semper commodo. Fusce laoreet neque vitae eros consectetur, semper pellentesque quam laoreet. Proin ultrices eget turpis sit amet faucibus. Etiam sit amet laoreet erat. Proin vitae auctor erat, non hendrerit metus.

Fusce semper vitae est et ultricies. Nunc ut luctus arcu. Donec quis sapien viverra, malesuada lorem eget, pulvinar tortor. Nam tempus, elit id gravida rhoncus, ipsum diam tincidunt risus, ac scelerisque eros urna sit amet dui. Phasellus vel accumsan diam, eu auctor ipsum. Etiam nunc justo, rhoncus eu egestas consectetur, ornare a justo. Phasellus dapibus ligula vitae mauris gravida dictum. Quisque vel sem eros. Pellentesque malesuada pharetra lectus eu convallis. Nullam ullamcorper euismod nibh, sit amet placerat diam varius sit amet. Nulla at rutrum tellus. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum nec risus libero.

Sed ac pellentesque lorem. Morbi at elementum odio. Maecenas commodo pulvinar orci, sed sagittis odio ornare eget. Morbi et justo nec ipsum molestie imperdiet ullamcorper sed nibh. Praesent dignissim elementum metus eu convallis. Nam non tortor bibendum, feugiat augue interdum, faucibus mi. Nulla ipsum ex, elementum vitae odio quis, ullamcorper consectetur diam. Nam erat felis, sagittis quis feugiat nec, molestie vitae neque. Vivamus ullamcorper placerat augue sit amet euismod. In et pretium arcu, sit amet vestibulum risus. Nullam id tempus mauris, sollicitudin varius tortor. Donec ultricies, risus quis pellentesque volutpat, tellus velit tristique neque, id condimentum leo tellus eget risus. Fusce laoreet, arcu id lobortis porta, nunc orci tincidunt elit, non bibendum enim libero eu tortor. Vivamus nec ligula gravida, iaculis ante ut, varius tortor.

Sed sit amet lectus quis elit faucibus rutrum. Aenean arcu diam, laoreet et elit eget, malesuada euismod nulla. Aenean quam eros, dapibus ut suscipit a, posuere vel justo. Nunc sed metus diam. Aliquam efficitur varius pellentesque. Praesent viverra odio eu nisi tincidunt tempor. Aliquam erat volutpat. Vestibulum sapien lorem, molestie id erat eget, accumsan ultrices magna. Vivamus convallis ex augue, sit amet finibus ante cursus convallis. Duis ornare nisi in lacinia venenatis. Duis id semper mi.

In a odio gravida, mollis purus ut, dignissim nisl. Donec in tellus convallis felis sodales tincidunt non a mauris. Aliquam ac lorem nisl. Pellentesque vehicula neque quis sapien facilisis semper. Proin vel blandit velit. Integer elementum nisi lorem, quis gravida sapien placerat et. Morbi vitae diam enim. Pellentesque eget malesuada lorem. Nullam quis leo sit amet leo egestas luctus. Suspendisse ut posuere metus. Nunc interdum mattis elit vitae pellentesque. Cras placerat convallis posuere. Suspendisse elementum diam eget arcu commodo feugiat. Etiam porttitor ante sed mi vulputate, vitae sodales felis sagittis. Nam egestas augue neque, a dictum libero fringilla at. Nam auctor lorem lacus, quis sagittis risus vulputate at.

Praesent odio sapien, auctor efficitur suscipit sed, dictum et elit. Vivamus quis diam eu lectus laoreet pulvinar. Nunc malesuada posuere augue. Suspendisse potenti. Nam blandit mi eget suscipit egestas. Nulla arcu felis, faucibus vel justo ac, iaculis finibus lacus. Curabitur ut justo et arcu gravida condimentum. Nam malesuada orci turpis. Proin eu massa at dolor rhoncus vehicula. In quis lorem orci. Mauris laoreet diam varius est porttitor, sit amet facilisis purus rhoncus. Pellentesque rhoncus egestas lorem, nec mattis sem faucibus vel. Nam vitae dolor tincidunt, congue nibh ac, iaculis lorem. Vivamus quam mauris, molestie nec dui sit amet, egestas ultrices leo. Quisque congue justo id nulla semper pretium. Sed molestie eget ex sed malesuada.''')
text.configure(state = "disabled")

scrollbar = ttk.Scrollbar(scrollbar_example, orient = "vertical", command = text.yview)
scrollbar.pack(side = "left", fill = "y", pady = 8)

text.configure(yscrollcommand = scrollbar.set)


def hide_menu():
    window.configure(menu = "")
    menu_bar.forget()
    title.pack(padx = 16, pady = (8, 0), side = "top", anchor = "w")
    update_colors()

def show_native_menu():
    window.configure(menu = menu)
    title.forget()
    menu_bar.forget()
    update_colors()

def show_custom_menu():
    window.configure(menu = "")
    menu_bar.pack(side = "top", fill = "x")
    title.forget()
    update_colors()
        
def update_colors():
    if menubar.get() == "custom":
        if sv_ttk.get_theme() == "dark": window.configure(bg = "#1f1f1f")
        else: window.configure(bg = "#ffffff")
    else:
        if sv_ttk.get_theme() == "dark": window.configure(bg = "#1c1c1c")
        else: window.configure(bg = "#fafafa")

def toggle_theme(): sv_ttk.toggle_theme(); update_colors(); update_color_constants()

def change_state_for_all_widgets(parent, state):
    for widget in parent.winfo_children():
        if isinstance(widget, (ttk.Frame, tk.Frame, ttk.Labelframe)):
            change_state_for_all_widgets(widget, state)
        else:
            if isinstance(widget, (ttk.Checkbutton, ttk.Radiobutton)) and widget["text"] == "Disabled": return

            try: widget["state"] = state
            except: pass

            if state == "enabled": readonlycombo["state"] = "readonly"

def change_widgets_state():
    if disable_widgets.get(): change_state_for_all_widgets(frame, "disabled")
    else: change_state_for_all_widgets(frame, "enabled")

ttk.Label(options, text = "Options", font = ("Segoe UI Semibold", 18)).pack(anchor = "w", pady = (0, 18))

ttk.Checkbutton(options, text = "Dark Mode", command = toggle_theme, style = "Switch.TCheckbutton").pack(anchor = "w")
ttk.Checkbutton(options, text = "Disable all widgets", variable = disable_widgets, command = change_widgets_state).pack(anchor = "w", pady = (10, 0))

ttk.Label(options, text = "Menu bar", font = ("Segoe UI Semibold", 13)).pack(anchor = "w", pady = (16, 8))
ttk.Radiobutton(options, text = "None", variable = menubar, command = hide_menu, value = "none").pack(anchor = "w", pady = (4, 0))
ttk.Radiobutton(options, text = "Native", variable = menubar, command = show_native_menu, value = "native").pack(anchor = "w", pady = (4, 0))
ttk.Radiobutton(options, text = "Custom", variable = menubar, command = show_custom_menu, value = "custom").pack(anchor = "w", pady = (4, 6))

other_options = ttk.Frame(options)
other_options.pack(anchor = "w")

ttk.Button(other_options, text = "Open Toplevel", command = tk.Toplevel).pack(side = "left", anchor = "w", pady = (10, 0))
ttk.Button(other_options, text = "Show message box", command = lambda: msg.showinfo("Test message box", "This is a test message box.")).pack(side = "left", padx = (8, 0), anchor = "w", pady = (10, 0))
ttk.Button(other_options, text = "Show file dialog", command = lambda: fd.askdirectory()).pack(side = "left", padx = (8, 0), anchor = "w", pady = (10, 0))


def add_color_constant_preview(title, color):
    global constants_list

    item = ttk.Frame(constants_list)
    item.pack(fill = "x", pady = (0, 8))

    ttk.Label(item, text = title, width = 70).pack(side = "left")
    tk.Frame(item, width = 30, height = 30, background = color, highlightbackground = sv_ttk.fg, highlightthickness = 1).pack(side = "right")
    ttk.Label(item, text = color, font = "Consolas").pack(padx = 10, side = "right")

def update_color_constants():
    global constants_list

    try: constants_list.forget()
    except: pass

    window.update()
    constants_list = ttk.Frame(color_constants)
    
    try:
        add_color_constant_preview("Background (background/bg): ", sv_ttk.bg)
        add_color_constant_preview("Foreground (foreground/fg): ", sv_ttk.fg)
        add_color_constant_preview("Foreground (disabled) (foreground_disabled/fg_dis): ", sv_ttk.fg_dis)
        add_color_constant_preview("Selection background (selection_background/sel_bg): ", sv_ttk.sel_bg)
        add_color_constant_preview("Selection foreground (selection_foreground/sel_fg): ", sv_ttk.sel_fg)
        add_color_constant_preview("Accent (accent): ", sv_ttk.accent)
    except: pass

    constants_list.place(relx = .5, rely = .55, anchor = "center")

window.update()

ttk.Label(color_constants, text = "Color constants", font = ("Segoe UI Semibold", 18)).pack(anchor = "w", pady = (0, 18))
update_color_constants()

geometry = window.geometry().split("+")[0].split("x")
window.minsize(width = geometry[0], height = geometry[1])

frame1.place(relx = .5, rely = .5, anchor = "center")

window.mainloop()