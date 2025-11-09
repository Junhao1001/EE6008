# ui_theme.py
"""
Build an aesthetically pleasing themed window, prioritize using ttkbootstrap;
fall back to standard Tkinter if ttkbootstrap is not installed.
"""

def build_root(app_title="EE6008 Multimodal Login", size="460x280", themename="flatly"):
    """
    Return (root, tb)
    - root: Tk or ttkbootstrap.Window
    - tb: ttkbootstrap module object (usable for bootstyle), None if not installed
    """
    try:
        import ttkbootstrap as tb
        root = tb.Window(themename=themename)
        root.title(app_title)
        root.geometry(size)
        root.resizable(False, False)

        style = tb.Style()
        style.configure(".", font=("Segoe UI", 10))
        style.configure("Card.TLabelframe", padding=12)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI Semibold", 10))
        return root, tb

    except Exception:
        import tkinter as tk
        root = tk.Tk()
        root.title(app_title)
        root.geometry(size)
        root.resizable(False, False)
        return root, None