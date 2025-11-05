# ui_theme.py
"""
构建美观主题窗口，优先使用 ttkbootstrap；
如果未安装则回退到标准 Tkinter。
"""

def build_root(app_title="EE6008 Multimodal Login", size="460x280", themename="flatly"):
    """
    返回 (root, tb)
    - root: Tk 或 ttkbootstrap.Window
    - tb: ttkbootstrap 模块对象（可用于 bootstyle），若未安装则为 None
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
