import tkinter as tk
from controller import AudioSchedulerController


def main() -> None:
    root = tk.Tk()
    AudioSchedulerController(root)
    root.mainloop()


if __name__ == "__main__":
    main()